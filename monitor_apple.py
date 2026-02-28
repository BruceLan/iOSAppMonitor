"""
Apple 应用监控主程序
负责业务流程编排
"""
from datetime import datetime
from typing import List, Tuple
from models.record import ApplePackageRecord
from services.feishu_service import FeishuBitableService
from services.feishu_messenger import FeishuMessenger
from services.apple_service import AppleStoreService
from utils.logger import (
    log_group, log_endgroup, log_info, log_warning, 
    log_error, log_success, is_github_actions
)
from utils.url_parser import parse_wiki_url
from config.settings import settings


class AppleMonitor:
    """Apple 应用监控类 - 负责业务流程编排"""
    
    def __init__(
        self,
        feishu_service: FeishuBitableService,
        feishu_messenger: FeishuMessenger,
        apple_service: AppleStoreService
    ):
        """
        初始化监控器
        
        Args:
            feishu_service: 飞书表格服务
            feishu_messenger: 飞书消息服务
            apple_service: Apple Store 服务
        """
        self.feishu_service = feishu_service
        self.feishu_messenger = feishu_messenger
        self.apple_service = apple_service
    
    def validate_records(
        self,
        records: List[ApplePackageRecord]
    ) -> Tuple[List[ApplePackageRecord], List[Tuple[ApplePackageRecord, List[str]]]]:
        """
        验证记录数据的完整性
        
        Args:
            records: 要验证的记录列表
        
        Returns:
            (valid_records, invalid_records) 元组
            - valid_records: 有效记录列表
            - invalid_records: 异常记录列表，每个元素是 (record, errors) 元组
        """
        valid_records = []
        invalid_records = []
        
        for record in records:
            validation_result = record.validate_data()
            
            if validation_result['is_valid']:
                valid_records.append(record)
                latest_version = record.get_latest_version()
                
                # 调试信息：打印子记录详情
                if record.children:
                    log_info(f"✅ {record.package_name}: 最新版本 = {latest_version} (来自子记录)")
                    log_info(f"  父记录版本: {record.version}")
                    log_info(f"  子记录数量: {len(record.children)}")
                    for idx, child in enumerate(record.children, 1):
                        log_info(f"    子记录{idx}: 版本={child.version}, 提审时间={child.submission_time}")
                else:
                    log_info(f"✅ {record.package_name}: 最新版本 = {latest_version} (主记录)")
            else:
                invalid_records.append((record, validation_result['errors']))
                log_warning(f"❌ {record.package_name}: 数据异常")
                for error in validation_result['errors']:
                    log_warning(f"  - {error}")
        
        return valid_records, invalid_records

    def update_app_status(
        self,
        app_token: str,
        table_id: str,
        record: ApplePackageRecord,
        latest_version: str,
        current_date_timestamp: int
    ) -> None:
        """
        更新应用的飞书表格状态
        
        Args:
            app_token: 多维表格的应用 Token
            table_id: 表格 ID
            record: 应用记录
            latest_version: 最新版本号
            current_date_timestamp: 当前日期的时间戳（毫秒）
        """
        log_info("📝 更新飞书表格状态...")

        # 要更新的字段
        update_child_fields = {
            "包状态": "已发布",
            "过审时间": current_date_timestamp  # 使用时间戳（毫秒）
        }

        # 更新主记录的字段
        update_fields = {
            "包状态": "已发布",
        }    
        
        if record.children:
            # 有子记录：找到对应版本号的子记录并更新
            target_child = None
            for child in record.children:
                if child.version == latest_version:
                    target_child = child
                    break
            
            if target_child:
                # 更新子记录状态
                log_info(f"  更新子记录: {target_child.record_id} (版本: {target_child.version})")
                self.feishu_service.update_record_fields(
                    app_token=app_token,
                    table_id=table_id,
                    record_id=target_child.record_id,
                    fields=update_child_fields
                )
        else:        
            # 如果没有子记录, 那么当前记录只有一条记录，则记录过审时间
            update_fields = {
                "包状态": "已发布",
                "过审时间": current_date_timestamp 
            } 

        # 没有子记录：只更新主记录, 只更新状态，不更新时间
        log_info(f"  更新主记录: {record.record_id}")
        self.feishu_service.update_record_fields(
            app_token=app_token,
            table_id=table_id,
            record_id=record.record_id,
            fields=update_fields
        )

    def run(self) -> List[ApplePackageRecord]:
        """
        运行监控任务
        
        Returns:
            有效记录列表
        """
        # 打印任务开始信息
        log_group("🚀 Apple 应用监控任务开始")
        log_info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_info(f"运行环境: {'GitHub Actions' if is_github_actions() else 'Local'}")
        log_endgroup()
        
        # 验证配置
        if not settings.validate():
            log_error("缺少必要的环境变量")
            log_info("请设置以下环境变量：")
            log_info("  - FEISHU_APP_ID")
            log_info("  - FEISHU_APP_SECRET")
            log_info("  - FEISHU_WIKI_URL")
            return []
        
        # 解析 wiki URL
        log_group("📋 步骤 0: 解析 Wiki URL")
        wiki_node_token, table_id, view_id = parse_wiki_url(settings.FEISHU_WIKI_URL)
        
        if not wiki_node_token:
            log_error("无法从 URL 中提取 wiki 节点 token")
            log_endgroup()
            return []
        
        log_success("解析成功")
        log_info(f"Wiki 节点 token: {wiki_node_token}")
        log_info(f"Table ID: {table_id}")
        log_info(f"View ID: {view_id}")
        log_endgroup()
        
        # 从 wiki 节点获取 app_token
        log_group("🔑 步骤 1: 从知识库节点获取 app_token")
        app_token = self.feishu_service.get_app_token_from_wiki(wiki_node_token)
        
        if not app_token:
            log_error("无法获取 app_token")
            log_info("   请检查：")
            log_info("   1. 应用是否有访问知识库的权限")
            log_info("   2. wiki_node_token 是否正确")
            log_info("   3. 节点是否是多维表格类型")
            log_endgroup()
            return []
        log_endgroup()
        
        # 测试连接
        log_group("🔌 步骤 2: 测试连接")
        if not self.feishu_service.test_connection(app_token):
            log_error("连接失败，请检查 app_token 是否正确")
            log_endgroup()
            return []
        log_endgroup()
        
        # 读取并筛选数据
        log_group("📊 步骤 3: 读取并筛选数据")
        
        if not table_id:
            log_error("未找到 table_id，无法继续")
            log_endgroup()
            return []
        
        records = self.feishu_service.get_records_by_status(
            app_token=app_token,
            table_id=table_id,
            status_field="包状态",
            target_status="提审中",
            view_id=view_id
        )
        log_endgroup()
        
        # 过滤出阶段 != "五图" 的所有记录
        log_group("🔍 步骤 4: 过滤阶段 != '五图' 的记录")
        filtered_records = []
        for record in records:
            if record.stage != "五图":
                filtered_records.append(record)
            else:
                log_info(f"过滤掉: {record.package_name} (阶段: {record.stage})")
        
        log_info(f"过滤前: {len(records)} 个主应用")
        log_info(f"过滤后: {len(filtered_records)} 个主应用（阶段 != '五图'）")
        log_endgroup()
        
        # 数据验证：分离有效记录和异常记录
        log_group("📦 步骤 5: 数据验证")
        valid_records, invalid_records = self.validate_records(filtered_records)
        
        log_info(f"\n数据验证结果：")
        log_info(f"  有效记录: {len(valid_records)} 个")
        log_info(f"  异常记录: {len(invalid_records)} 个")
        
        # 打印异常记录详细信息
        if invalid_records:
            log_info(f"\n异常记录详情：")
            for idx, (record, errors) in enumerate(invalid_records, 1):
                log_warning(f"  [{idx}] {record.package_name} (Record ID: {record.record_id})")
                for error in errors:
                    log_warning(f"      - {error}")
                if record.children:
                    log_info(f"      子记录数量: {len(record.children)}")
                    for child_idx, child in enumerate(record.children, 1):
                        # 格式化提审时间
                        submission_time_str = "无"
                        if child.submission_time:
                            try:
                                dt = datetime.fromtimestamp(child.submission_time / 1000)
                                submission_time_str = dt.strftime('%Y-%m-%d')
                            except:
                                submission_time_str = str(child.submission_time)
                        
                        log_info(f"        子记录{child_idx}: 版本={child.version}, 状态={child.package_status}, 提审时间={submission_time_str}, ID={child.record_id}")
        
        log_endgroup()
        
        # 发送异常记录警告（调试期间暂时注释）
        if invalid_records:
            log_group("⚠️  步骤 6: 发送数据异常警告")
            # 找到配置了 mention_all = True 的群聊
            warning_chat_id = None
            for config in settings.FEISHU_NOTIFICATIONS:
                if config.get("mention_all"):
                    warning_chat_id = config.get("chat_id")
                    break
            
            if warning_chat_id:
                self.feishu_messenger.send_warning_message(
                    chat_id=warning_chat_id,
                    invalid_records=invalid_records
                )
            else:
                log_warning("未找到配置 mention_all=True 的群聊，跳过发送警告")
            log_endgroup()
        
        # 查询 Apple Store 状态并更新（只处理有效记录）
        log_group("🍎 步骤 7: 查询 Apple Store 状态并更新")
        log_info(f"只处理有效记录（共 {len(valid_records)} 个）")
        
        # 获取当前时间戳（毫秒）
        current_timestamp = int(datetime.now().timestamp() * 1000)
        
        success_count = 0
        skip_count = 0
        
        for record in valid_records:
            if not record.apple_id:
                log_warning(f"{record.package_name} - 没有 Apple ID，跳过")
                skip_count += 1
                continue
            
            # 获取本地最新版本
            local_latest_version = record.get_latest_version()
            if not local_latest_version:
                log_warning(f"{record.package_name} - 没有最新版本，跳过")
                skip_count += 1
                continue
            
            # 查询 Apple Store 状态
            app_status = self.apple_service.query_app_status(record.apple_id, verbose=False)
            
            # 判断版本是否已上线
            is_version_online = False
            if app_status and app_status['is_online']:
                store_version = app_status['version']
                if store_version and store_version == local_latest_version:
                    is_version_online = True
            
            # 处理已上线的应用
            if is_version_online:
                log_success(f"{record.package_name} - 指定版本已上线")
                log_info(f"  📱 应用名称: {app_status['track_name']}")
                log_info(f"  📦 版本号: {store_version} (本地最新版本: {local_latest_version})")
                log_info(f"  🆔 Apple ID: {record.apple_id}")
                log_info(f"  📅 发布日期: {app_status['release_date']}")
                log_info(f"  🔄 当前版本发布日期: {app_status['current_version_release_date']}")
                if app_status.get('track_view_url'):
                    log_info(f"  🔗 应用链接: {app_status['track_view_url']}")
                
                # 更新飞书表格状态
                self.update_app_status(
                    app_token=app_token,
                    table_id=table_id,
                    record=record,
                    latest_version=local_latest_version,
                    current_date_timestamp=current_timestamp
                )
                
                # 发送飞书通知到多个群聊（调试期间暂时注释）
                self.feishu_messenger.send_notifications(
                    notifications=settings.FEISHU_NOTIFICATIONS,
                    app_name=record.package_name,
                    stage=record.stage or "未知",
                    version=local_latest_version
                )
                success_count += 1
            else:
                # 未上线的应用
                log_info(f"{record.package_name} - 指定版本未上线")
                log_info(f"  📱 应用名称: {record.package_name}")
                log_info(f"  📦 版本号: {local_latest_version}")
                log_info(f"  🆔 Apple ID: {record.apple_id}")
 
        log_endgroup()
        
        # 打印任务总结
        log_group("📊 任务执行总结")
        log_info(f"总共筛选: {len(filtered_records)} 个应用")
        log_info(f"有效记录: {len(valid_records)} 个")
        log_info(f"异常记录: {len(invalid_records)} 个")
        log_info(f"成功上线: {success_count} 个")
        log_info(f"跳过处理: {skip_count} 个")
        log_info(f"等待上线: {len(valid_records) - success_count - skip_count} 个")
        log_info(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_endgroup()
        
        return valid_records


def main():
    """主函数"""
    # 创建服务实例
    feishu_service = FeishuBitableService(
        app_id=settings.FEISHU_APP_ID,
        app_secret=settings.FEISHU_APP_SECRET
    )
    
    feishu_messenger = FeishuMessenger(
        app_id=settings.FEISHU_APP_ID,
        app_secret=settings.FEISHU_APP_SECRET
    )
    
    apple_service = AppleStoreService()
    
    # 创建监控器并运行
    monitor = AppleMonitor(
        feishu_service=feishu_service,
        feishu_messenger=feishu_messenger,
        apple_service=apple_service
    )
    
    monitor.run()


if __name__ == "__main__":
    try:
        main()
        log_success("✅ 监控任务执行完成")
    except Exception as e:
        log_error(f"监控任务执行失败: {str(e)}")
        import traceback
        log_info(traceback.format_exc())
        exit(1)
