"""
飞书多维表格监控脚本
读取多维表格并筛选出"包状态"为"提审中"的记录
"""
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest, ListAppTableRequest, UpdateAppTableRecordRequest
from lark_oapi.api.bitable.v1.model import AppTableRecord
from lark_oapi.api.wiki.v2.model.get_node_space_request import GetNodeSpaceRequest
from typing import List, Dict, Any, Optional, Tuple
from model import ApplePackageRecord
import requests
import json


class FeishuBitableMonitor:
    """飞书多维表格监控类"""
    
    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书客户端
        
        Args:
            app_id: 飞书应用的 App ID
            app_secret: 飞书应用的 App Secret
        """
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
        print(f"🔍 从知识库节点获取 app_token，节点 token: {wiki_node_token}")
        try:
            request = GetNodeSpaceRequest.builder() \
                .token(wiki_node_token) \
                .build()
            
            response = self.client.wiki.v2.space.get_node(request)
            
            if response.success():
                node = response.data.node
                obj_type = node.obj_type
                obj_token = node.obj_token
                
                print(f"✅ 成功获取节点信息")
                print(f"  - 节点类型: {obj_type}")
                print(f"  - obj_token (app_token): {obj_token}")
                
                if obj_type == "bitable":
                    print(f"✅ 确认是多维表格节点")
                    return obj_token
                else:
                    print(f"⚠️  节点类型不是多维表格 (bitable)，而是: {obj_type}")
                    return None
            else:
                print(f"❌ 获取节点信息失败: {response.code}, {response.msg}")
                print(f"\n可能的原因：")
                print(f"1. wiki_node_token 不正确")
                print(f"2. 应用没有访问该知识库节点的权限")
                print(f"3. 节点不存在或已被删除")
                return None
        except Exception as e:
            print(f"❌ 获取节点信息异常: {str(e)}")
            return None
    
    def test_connection(self, app_token: str) -> bool:
        """
        测试连接，验证 app_token 是否正确
        
        Args:
            app_token: 多维表格的应用 Token
        
        Returns:
            连接是否成功
        """
        print(f"🔍 测试连接，app_token: {app_token}")
        try:
            request = ListAppTableRequest.builder() \
                .app_token(app_token) \
                .build()
            
            response = self.client.bitable.v1.app_table.list(request)
            
            if response.success():
                tables = response.data.items
                print(f"✅ 连接成功！找到 {len(tables)} 个表格")
                print("\n可用的表格列表：")
                for table in tables:
                    print(f"  - 表格名称: {table.name}")
                    print(f"    表格 ID: {table.table_id}")
                    print()
                return True
            else:
                print(f"❌ 连接失败: {response.code}, {response.msg}")
                print("\n可能的原因：")
                print("1. app_token 不正确")
                print("2. 应用没有访问该多维表格的权限")
                print("3. 多维表格不存在或已被删除")
                print("\n💡 如何获取正确的 app_token：")
                print("   1. 打开飞书多维表格")
                print("   2. 点击右上角「...」->「复制链接」")
                print("   3. 链接格式应该是: https://xxx.feishu.cn/base/AppToken?table=TableId")
                print("   4. 从链接中提取 AppToken 部分")
                return False
        except Exception as e:
            print(f"❌ 连接异常: {str(e)}")
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
                print(f"❌ 请求失败: {response.code}, {response.msg}")
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
        2. 查找这些主应用的所有子记录（版本记录）
        
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
        print(f"开始读取多维表格，查询逻辑：")
        print(f"  步骤1: 查找父记录为空且{status_field} = {target_status}的记录（主应用）")
        print(f"  步骤2: 查找步骤1中所有主应用的子记录（版本记录）")
        print(f"  app_token: {app_token}")
        print(f"  table_id: {table_id}")
        if view_id:
            print(f"  view_id: {view_id} (指定视图)")
        print()
        
        # 步骤1: 获取所有记录
        print("步骤1: 获取所有记录...")
        all_raw_records = self.get_all_records(app_token, table_id, view_id)
        print(f"  共获取 {len(all_raw_records)} 条记录")
        
        # 步骤2: 筛选父记录为空且包状态=提审中的主应用记录
        print("\n步骤2: 筛选主应用记录（父记录为空且包状态=提审中）...")
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
        
        print(f"  找到 {len(main_apps)} 个主应用")
        
        # 步骤3: 查找每个主应用的所有子记录（版本记录）
        print("\n步骤3: 查找每个主应用的子记录（版本记录）...")
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
                            if main_app.record_id in record_ids:
                                # 这是当前主应用的子记录
                                child_record = ApplePackageRecord.from_feishu_fields(
                                    fields=fields,
                                    record_id=raw_record['record_id']
                                )
                                children.append(child_record)
                                break
            
            main_app.children = children
            print(f"  主应用 {main_app.package_name} (ID: {main_app.record_id}) 有 {len(children)} 条版本记录")
        
        print(f"\n✅ 查询完成，共找到 {len(main_apps)} 个主应用及其版本记录")
        return main_apps
    
    def query_apple_app_status(self, apple_id: int, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """
        使用 Apple Lookup API (iTunes Search API) 查询应用状态
        
        Args:
            apple_id: Apple 应用 ID
            verbose: 是否打印详细信息
        
        Returns:
            应用信息字典，包含：
            - is_online: 是否已上线
            - version: 当前版本号
            - track_name: 应用名称
            - release_date: 发布日期
            - current_version_release_date: 当前版本发布日期
            如果查询失败返回 None
        """
        url = f"https://itunes.apple.com/lookup"
        params = {
            'id': apple_id,
            'country': 'us'
        }
        
        try:
            if verbose:
                print(f"\n🔍 查询 Apple 应用状态，Apple ID: {apple_id}")
                print(f"  API URL: {url}")
                print(f"  参数: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('resultCount', 0) == 0:
                if verbose:
                    print(f"  ⚠️  未找到应用信息（Apple ID: {apple_id}）")
                return {
                    'is_online': False,
                    'version': None,
                    'track_name': None,
                    'release_date': None,
                    'current_version_release_date': None
                }
            
            result = data['results'][0]
            
            app_info = {
                'is_online': True,
                'version': result.get('version'),
                'track_name': result.get('trackName'),
                'release_date': result.get('releaseDate'),
                'current_version_release_date': result.get('currentVersionReleaseDate'),
                'bundle_id': result.get('bundleId'),
                'track_view_url': result.get('trackViewUrl')
            }
            
            if verbose:
                print(f"  ✅ 查询成功")
                print(f"  应用名称: {app_info['track_name']}")
                print(f"  版本号: {app_info['version']}")
                print(f"  是否上线: 是")
                print(f"  发布日期: {app_info['release_date']}")
                print(f"  当前版本发布日期: {app_info['current_version_release_date']}")
                print(f"\n  完整信息:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            
            return app_info
            
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"  ❌ 请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            if verbose:
                print(f"  ❌ JSON 解析失败: {str(e)}")
            return None
        except Exception as e:
            if verbose:
                print(f"  ❌ 查询异常: {str(e)}")
            return None
    
    def update_record_status(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        status_field: str = "包状态",
        new_status: str = "已上线"
    ) -> bool:
        """
        更新飞书表格中记录的包状态
        
        Args:
            app_token: 多维表格的应用 Token
            table_id: 表格 ID
            record_id: 记录 ID
            status_field: 状态字段名称，默认为"包状态"
            new_status: 新状态值，默认为"已上线"
        
        Returns:
            更新是否成功
        """
        try:
            # 构建字段更新数据
            fields = {
                status_field: new_status
            }
            
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
                print(f"    ✅ 更新成功: Record ID {record_id} -> {new_status}")
                return True
            else:
                print(f"    ❌ 更新失败: Record ID {record_id}, 错误: {response.code}, {response.msg}")
                return False
                
        except Exception as e:
            print(f"    ❌ 更新异常: Record ID {record_id}, 错误: {str(e)}")
            return False
    
    def send_feishu_message(
        self,
        webhook_url: str,
        app_name: str,
        stage: str,
        version: str
    ) -> bool:
        """
        发送消息到飞书机器人
        
        Args:
            webhook_url: 飞书机器人 Webhook URL
            app_name: 应用名称
            stage: 阶段
            version: 版本号
        
        Returns:
            发送是否成功
        """
        if not webhook_url:
            print(f"    ⚠️  飞书机器人 URL 未配置，跳过发送消息")
            return False
        
        try:
            message = f"{app_name} {stage} {version} 过审并发布了"
            
            payload = {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                print(f"    ✅ 飞书消息发送成功: {message}")
                return True
            else:
                print(f"    ❌ 飞书消息发送失败: {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"    ❌ 发送飞书消息异常: {str(e)}")
            return False
    
    def print_records(self, records: List[ApplePackageRecord]):
        """
        打印记录信息（包括主应用和其版本记录）
        
        Args:
            records: 主应用记录列表（ApplePackageRecord 对象，包含子记录）
        """
        print(f"\n{'='*60}")
        print(f"找到 {len(records)} 个主应用")
        total_versions = sum(len(app.children) for app in records)
        print(f"共 {total_versions} 条版本记录")
        print(f"{'='*60}\n")
        
        for idx, main_app in enumerate(records, 1):
            print(f"{'='*60}")
            print(f"主应用 #{idx}: {main_app.package_name}")
            print(f"{'='*60}")
            print(f"  Record ID: {main_app.record_id}")
            print(f"  应用: {main_app.package_name}")
            print(f"  阶段: {main_app.stage}")
            print(f"  包状态: {main_app.package_status}")
            print(f"  Apple ID: {main_app.apple_id}")
            print(f"  版本号: {main_app.version}")
            latest_version = main_app.get_latest_version()
            print(f"  最新版本: {latest_version}")
            print(f"  团队: {main_app.team}")
            print(f"  所属季度: {main_app.quarter}")
            if main_app.developers:
                dev_names = [dev.name for dev in main_app.developers if hasattr(dev, 'name')]
                print(f"  开发人员: {', '.join(dev_names) if dev_names else 'N/A'}")
            if main_app.submission_time:
                from datetime import datetime
                dt = datetime.fromtimestamp(main_app.submission_time / 1000)
                print(f"  提审时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 打印子记录（版本记录）
            if main_app.children:
                print(f"\n  └─ 版本记录（共 {len(main_app.children)} 条）:")
                for child_idx, child in enumerate(main_app.children, 1):
                    print(f"     [{child_idx}] 版本: {child.version} | 状态: {child.package_status} | Record ID: {child.record_id}")
                    if child.submission_time:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(child.submission_time / 1000)
                        print(f"         提审时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"\n  └─ 无版本记录")
            print()


def parse_wiki_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    解析 wiki URL，提取节点 token、table_id 和 view_id
    
    Args:
        url: wiki URL
    
    Returns:
        (wiki_node_token, table_id, view_id) 元组
    """
    try:
        # 从 URL 中提取 wiki 节点 token
        # 格式: https://xxx.feishu.cn/wiki/NODE_TOKEN?table=TABLE_ID&view=VIEW_ID
        if "/wiki/" in url:
            parts = url.split("/wiki/")[1].split("?")[0]
            wiki_node_token = parts
            
            # 提取 table_id 和 view_id
            table_id = None
            view_id = None
            if "?" in url:
                params = url.split("?")[1]
                for param in params.split("&"):
                    if param.startswith("table="):
                        table_id = param.split("=")[1]
                    elif param.startswith("view="):
                        view_id = param.split("=")[1]
            
            return wiki_node_token, table_id, view_id
    except Exception as e:
        print(f"解析 URL 失败: {str(e)}")
    
    return None, None, None


def main():
    """主函数"""
    # 配置信息
    APP_ID = "cli_a9ccfb2bbf385cc6"
    APP_SECRET = "4RrEVRd6jXTBrPbOxncNEbprT34AloaH"
    
    # Wiki URL（知识库下的多维表格）
    WIKI_URL = "https://la1a59fdywl.feishu.cn/wiki/Nzmew2Przi0hQAkgbGHcTCvfn3c?fromScene=spaceOverview&table=tblburubNacfxW79&view=vewGZJS1AM"
    
    # 创建监控实例
    monitor = FeishuBitableMonitor(APP_ID, APP_SECRET)
    
    # 解析 wiki URL
    print("=" * 60)
    print("步骤 0: 解析 Wiki URL")
    print("=" * 60)
    wiki_node_token, table_id, view_id = parse_wiki_url(WIKI_URL)
    
    if not wiki_node_token:
        print("❌ 无法从 URL 中提取 wiki 节点 token")
        return []
    
    print(f"✅ 解析成功")
    print(f"  - Wiki 节点 token: {wiki_node_token}")
    print(f"  - Table ID: {table_id}")
    print(f"  - View ID: {view_id}")
    
    # 从 wiki 节点获取 app_token
    print("\n" + "=" * 60)
    print("步骤 1: 从知识库节点获取 app_token")
    print("=" * 60)
    app_token = monitor.get_app_token_from_wiki(wiki_node_token)
    
    if not app_token:
        print("\n⚠️  无法获取 app_token，请检查：")
        print("   1. 应用是否有访问知识库的权限")
        print("   2. wiki_node_token 是否正确")
        print("   3. 节点是否是多维表格类型")
        return []
    
    # 测试连接，验证 app_token 是否正确
    print("\n" + "=" * 60)
    print("步骤 2: 测试连接")
    print("=" * 60)
    if not monitor.test_connection(app_token):
        print("\n⚠️  连接失败，请检查 app_token 是否正确")
        return []
    
    print("\n" + "=" * 60)
    print("步骤 3: 读取并筛选数据")
    print("=" * 60)
    
    # 获取"包状态"为"提审中"的记录
    if not table_id:
        print("❌ 未找到 table_id，无法继续")
        return []
    
    records = monitor.get_records_by_status(
        app_token=app_token,
        table_id=table_id,
        status_field="包状态",
        target_status="提审中",
        view_id=view_id  # 传入视图 ID，从指定视图读取数据
    )
    
    # 过滤出阶段 != "五图" 的所有记录
    print("\n" + "=" * 60)
    print("步骤 4: 过滤阶段 != '五图' 的记录")
    print("=" * 60)
    filtered_records = []
    for record in records:
        if record.stage != "五图":
            filtered_records.append(record)
        else:
            print(f"  过滤掉: {record.package_name} (阶段: {record.stage})")
    
    print(f"  过滤前: {len(records)} 个主应用")
    print(f"  过滤后: {len(filtered_records)} 个主应用（阶段 != '五图'）")
    
    # 计算并显示每个记录的最新版本
    print("\n" + "=" * 60)
    print("步骤 5: 计算最新版本")
    print("=" * 60)
    for record in filtered_records:
        latest_version = record.get_latest_version()
        if record.children:
            print(f"  {record.package_name}: 最新版本 = {latest_version} (来自子记录)")
        else:
            print(f"  {record.package_name}: 最新版本 = {latest_version} (主记录)")
    
    # 查询每个 Apple ID 对应的版本，判断是否上线并更新状态
    print("\n" + "=" * 60)
    print("步骤 6: 查询每个应用的 Apple Store 状态并更新")
    print("=" * 60)
    print("  只显示指定版本已上线的应用\n")
    
    # 飞书机器人 Webhook URL（稍后配置）
    # FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/73f8286b-b226-4c72-9259-9ff9c341253f"  # TODO: 配置飞书机器人 URL
    FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/a43899b8-8f5f-4d28-9938-be3cfd3b02de"  # TODO: 配置飞书机器人 URL
    
    for record in filtered_records:
        if not record.apple_id:
            continue
        
        # 获取本地最新版本
        local_latest_version = record.get_latest_version()
        if not local_latest_version:
            continue
        
        # 查询 Apple Store 状态
        app_status = monitor.query_apple_app_status(record.apple_id, verbose=False)
        
        if app_status and app_status['is_online']:
            store_version = app_status['version']
            
            # 只有当 Store 版本与本地最新版本匹配时，才处理
            if store_version and store_version == local_latest_version:
                print(f"{'='*60}")
                print(f"✅ {record.package_name} - 指定版本已上线")
                print(f"{'='*60}")
                print(f"  📱 应用名称: {app_status['track_name']}")
                print(f"  📦 版本号: {store_version} (本地最新版本: {local_latest_version})")
                print(f"  🆔 Apple ID: {record.apple_id}")
                print(f"  📅 发布日期: {app_status['release_date']}")
                print(f"  🔄 当前版本发布日期: {app_status['current_version_release_date']}")
                if app_status.get('track_view_url'):
                    print(f"  🔗 应用链接: {app_status['track_view_url']}")
                print()
                
                # 更新飞书表格状态
                print(f"  📝 更新飞书表格状态...")
                
                if record.children:
                    # 有子记录：找到对应版本号的子记录并更新
                    target_child = None
                    for child in record.children:
                        if child.version == local_latest_version:
                            target_child = child
                            break
                    
                    if target_child:
                        # 更新子记录状态
                        print(f"    更新子记录: {target_child.record_id} (版本: {target_child.version})")
                        monitor.update_record_status(
                            app_token=app_token,
                            table_id=table_id,
                            record_id=target_child.record_id,
                            status_field="包状态",
                            new_status="已发布"
                        )
                    else:
                        print(f"    ⚠️  未找到版本号为 {local_latest_version} 的子记录")
                    
                    # 更新主记录状态
                    print(f"    更新主记录: {record.record_id}")
                    monitor.update_record_status(
                        app_token=app_token,
                        table_id=table_id,
                        record_id=record.record_id,
                        status_field="包状态",
                        new_status="已发布"
                    )
                else:
                    # 没有子记录：只更新主记录
                    print(f"    更新主记录: {record.record_id}")
                    monitor.update_record_status(
                        app_token=app_token,
                        table_id=table_id,
                        record_id=record.record_id,
                        status_field="包状态",
                        new_status="已发布"
                    )
                
                # 发送飞书消息
                print(f"  📨 发送飞书消息...")
                monitor.send_feishu_message(
                    webhook_url=FEISHU_WEBHOOK_URL,
                    app_name=record.package_name,
                    stage=record.stage or "未知",
                    version=local_latest_version
                )
                print()
    
    # 打印结果
    # monitor.print_records(filtered_records)
    
    return filtered_records


if __name__ == "__main__":
    main()

