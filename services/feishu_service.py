"""
飞书多维表格服务模块
"""
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import (
    ListAppTableRecordRequest,
    ListAppTableRequest,
    UpdateAppTableRecordRequest
)
from lark_oapi.api.bitable.v1.model import AppTableRecord
from lark_oapi.api.wiki.v2.model.get_node_space_request import GetNodeSpaceRequest
from typing import List, Dict, Any, Optional
from models.record import ApplePackageRecord
from utils.logger import log_info, log_warning, log_success, log_error


class FeishuBitableService:
    """飞书多维表格服务类"""
    
    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书客户端
        
        Args:
            app_id: 飞书应用的 App ID
            app_secret: 飞书应用的 App Secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
    
    def get_app_token_from_wiki(self, wiki_node_token: str) -> Optional[str]:
        """
        从知识库（wiki）节点获取多维表格的 app_token
        
        Args:
            wiki_node_token: 知识库节点的 token（从 wiki URL 中提取）
        
        Returns:
            多维表格的 app_token（即 obj_token），如果失败返回 None
        """
        log_info(f"🔍 从知识库节点获取 app_token，节点 token: {wiki_node_token}")
        try:
            request = GetNodeSpaceRequest.builder() \
                .token(wiki_node_token) \
                .build()
            
            response = self.client.wiki.v2.space.get_node(request)
            
            if response.success():
                node = response.data.node
                obj_type = node.obj_type
                obj_token = node.obj_token
                
                log_success("成功获取节点信息")
                log_info(f"  - 节点类型: {obj_type}")
                log_info(f"  - obj_token (app_token): {obj_token}")
                
                if obj_type == "bitable":
                    log_success("确认是多维表格节点")
                    return obj_token
                else:
                    log_warning(f"节点类型不是多维表格 (bitable)，而是: {obj_type}")
                    return None
            else:
                log_error(f"获取节点信息失败: {response.code}, {response.msg}")
                log_info("\n可能的原因：")
                log_info("1. 应用没有访问知识库的权限")
                log_info("2. wiki_node_token 不正确")
                log_info("3. 节点不存在或已被删除")
                return None
        except Exception as e:
            log_error(f"获取节点信息异常: {str(e)}")
            return None
    
    def test_connection(self, app_token: str) -> bool:
        """
        测试连接，验证 app_token 是否正确
        
        Args:
            app_token: 多维表格的应用 Token
        
        Returns:
            连接是否成功
        """
        try:
            request = ListAppTableRequest.builder() \
                .app_token(app_token) \
                .build()
            
            response = self.client.bitable.v1.app_table.list(request)
            
            if response.success():
                tables = response.data.items
                log_success(f"连接成功！找到 {len(tables)} 个表格")
                log_info("可用的表格列表：")
                for table in tables:
                    log_info(f"  - 表格名称: {table.name}")
                    log_info(f"    表格 ID: {table.table_id}")
                return True
            else:
                log_error(f"连接失败: {response.code}, {response.msg}")
                return False
        except Exception as e:
            log_error(f"连接异常: {str(e)}")
            return False

    def get_all_records(
        self,
        app_token: str,
        table_id: str,
        view_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取所有记录（用于后续筛选）
        
        Args:
            app_token: 多维表格的应用 Token
            table_id: 表格 ID
            view_id: 视图 ID（可选）
        
        Returns:
            所有记录的列表（包含 record_id 和 fields）
        """
        all_records = []
        page_token = None
        
        while True:
            request_builder = ListAppTableRecordRequest.builder() \
                .app_token(app_token) \
                .table_id(table_id) \
                .page_size(500)
            
            if view_id:
                request_builder.view_id(view_id)
            
            if page_token:
                request_builder.page_token(page_token)
            
            request = request_builder.build()
            response = self.client.bitable.v1.app_table_record.list(request)
            
            if not response.success():
                log_error(f"请求失败: {response.code}, {response.msg}")
                break
            
            items = response.data.items
            if not items:
                break
            
            for record in items:
                if record.fields:
                    all_records.append({
                        'record_id': record.record_id,
                        'fields': record.fields
                    })
            
            if not response.data.has_more:
                break
            
            page_token = response.data.page_token
        
        return all_records

    def get_records_by_status(
        self, 
        app_token: str, 
        table_id: str, 
        status_field: str = "包状态",
        target_status: str = "提审中",
        view_id: Optional[str] = None,
        parent_field: str = "父记录"
    ) -> List[ApplePackageRecord]:
        """
        获取指定状态的主应用记录及其所有子记录（版本记录）
        
        查询逻辑：
        1. 查找所有父记录为空且包状态=提审中的记录（主应用）
        2. 查找这些主应用的所有子记录（版本记录），只包含状态为"提审中"或"已发布"的子记录
        
        Args:
            app_token: 多维表格的应用 Token
            table_id: 表格 ID
            status_field: 状态字段名称，默认为"包状态"
            target_status: 目标状态值，默认为"提审中"
            view_id: 视图 ID（可选），如果提供则只读取该视图下的数据
            parent_field: 父记录字段名称，默认为"父记录"
        
        Returns:
            主应用记录列表（每个记录包含其子记录）
        """
        log_info("开始读取多维表格，查询逻辑：")
        log_info(f"  步骤1: 查找父记录为空且{status_field} = {target_status}的记录（主应用）")
        log_info(f"  步骤2: 查找步骤1中所有主应用的子记录（版本记录）")
        log_info(f"  table_id: {table_id}")
        if view_id:
            log_info(f"  view_id: {view_id} (指定视图)")
        
        # 步骤1: 获取所有记录
        log_info("步骤1: 获取所有记录...")
        all_raw_records = self.get_all_records(app_token, table_id, view_id)
        log_info(f"  共获取 {len(all_raw_records)} 条记录")
        
        # 步骤2: 筛选父记录为空且包状态=提审中的主应用记录
        log_info("步骤2: 筛选主应用记录（父记录为空且包状态=提审中）...")
        main_apps: List[ApplePackageRecord] = []
        main_app_record_ids = set()
        
        for raw_record in all_raw_records:
            fields = raw_record['fields']
            if not fields:
                continue
            
            # 检查包状态
            status_match = False
            if status_field in fields:
                status_value = fields[status_field]
                if isinstance(status_value, list):
                    status_text = [str(item) for item in status_value]
                    status_match = target_status in status_text
                else:
                    status_match = str(status_value) == target_status
            
            if not status_match:
                continue
            
            # 检查父记录是否为空
            parent_empty = False
            if parent_field not in fields:
                parent_empty = True
            else:
                parent_value = fields[parent_field]
                if isinstance(parent_value, list):
                    if len(parent_value) == 0:
                        parent_empty = True
                    else:
                        is_empty = True
                        for item in parent_value:
                            if isinstance(item, dict):
                                if 'record_ids' in item and item.get('record_ids'):
                                    is_empty = False
                                    break
                                if 'text' in item and item.get('text'):
                                    is_empty = False
                                    break
                        parent_empty = is_empty
                elif parent_value is None or parent_value == "":
                    parent_empty = True
            
            if status_match and parent_empty:
                package_record = ApplePackageRecord.from_feishu_fields(
                    fields=fields,
                    record_id=raw_record['record_id']
                )
                main_apps.append(package_record)
                main_app_record_ids.add(raw_record['record_id'])
        
        log_info(f"  找到 {len(main_apps)} 个主应用")
        
        # 步骤3: 查找每个主应用的所有子记录（版本记录）
        # 只包含状态为"提审中"或"已发布"的子记录
        log_info("步骤3: 查找每个主应用的子记录（版本记录）...")
        log_info("  子记录过滤条件: 包状态 = '提审中' 或 '已发布'")
        valid_child_statuses = ["提审中", "已发布"]
        
        for main_app in main_apps:
            children = []
            for raw_record in all_raw_records:
                fields = raw_record['fields']
                if not fields or parent_field not in fields:
                    continue
                
                # 检查该记录是否指向当前主应用
                parent_value = fields[parent_field]
                if isinstance(parent_value, list):
                    for item in parent_value:
                        if isinstance(item, dict):
                            record_ids = item.get('record_ids', [])
                            # 确保 record_ids 不为 None
                            if record_ids and main_app.record_id in record_ids:
                                # 这是当前主应用的子记录，检查状态
                                child_status = None
                                if status_field in fields:
                                    status_value = fields[status_field]
                                    if isinstance(status_value, list):
                                        child_status = [str(item) for item in status_value]
                                    else:
                                        child_status = str(status_value)
                                
                                # 只添加状态为"提审中"或"已发布"的子记录
                                status_valid = False
                                if isinstance(child_status, list):
                                    status_valid = any(s in valid_child_statuses for s in child_status)
                                elif child_status:
                                    status_valid = child_status in valid_child_statuses
                                
                                if status_valid:
                                    child_record = ApplePackageRecord.from_feishu_fields(
                                        fields=fields,
                                        record_id=raw_record['record_id']
                                    )
                                    children.append(child_record)
                                break
            
            main_app.children = children
            log_info(f"  主应用 {main_app.package_name} (ID: {main_app.record_id}) 有 {len(children)} 条有效版本记录")
        
        log_success(f"查询完成，共找到 {len(main_apps)} 个主应用及其版本记录")
        return main_apps

    def update_record_fields(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: Dict[str, Any]
    ) -> bool:
        """
        更新飞书表格中记录的字段
        
        Args:
            app_token: 多维表格的应用 Token
            table_id: 表格 ID
            record_id: 记录 ID
            fields: 要更新的字段字典，例如 {"包状态": "已发布", "过审时间": 1234567890000}
        
        Returns:
            更新是否成功
        """
        try:
            # 构建请求
            request = UpdateAppTableRecordRequest.builder() \
                .app_token(app_token) \
                .table_id(table_id) \
                .record_id(record_id) \
                .request_body(
                    AppTableRecord.builder()
                    .fields(fields)
                    .build()
                ) \
                .build()
            
            # 发起请求
            response = self.client.bitable.v1.app_table_record.update(request)
            
            if response.success():
                # 格式化更新信息
                update_info = ", ".join([f"{k}={v}" for k, v in fields.items()])
                log_success(f"更新成功: Record ID {record_id} ({update_info})")
                return True
            else:
                log_error(f"更新失败: Record ID {record_id}")
                log_info(f"  错误码: {response.code}")
                log_info(f"  错误信息: {response.msg}")
                return False
                
        except Exception as e:
            log_error(f"更新异常: Record ID {record_id}, 错误: {str(e)}")
            return False
