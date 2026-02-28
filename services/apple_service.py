"""
Apple Store API 服务模块
"""
import requests
import json
from typing import Optional, Dict, Any
from utils.logger import log_info, log_warning, log_success, log_error


class AppleStoreService:
    """Apple Store API 服务类"""
    
    def __init__(self):
        self.api_url = "https://itunes.apple.com/lookup"
    
    def query_app_status(self, apple_id: int, verbose: bool = False) -> Optional[Dict[str, Any]]:
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
        params = {
            'id': apple_id,
            'country': 'us'
        }
        
        try:
            if verbose:
                log_info(f"🔍 查询 Apple 应用状态，Apple ID: {apple_id}")
                log_info(f"  API URL: {self.api_url}")
                log_info(f"  参数: {params}")
            
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('resultCount', 0) == 0:
                if verbose:
                    log_warning(f"未找到应用信息（Apple ID: {apple_id}）")
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
                log_success("查询成功")
                log_info(f"  应用名称: {app_info['track_name']}")
                log_info(f"  版本号: {app_info['version']}")
                log_info(f"  是否上线: 是")
                log_info(f"  发布日期: {app_info['release_date']}")
                log_info(f"  当前版本发布日期: {app_info['current_version_release_date']}")
                log_info("\n  完整信息:")
                log_info(json.dumps(result, indent=2, ensure_ascii=False))
            
            return app_info
            
        except requests.exceptions.RequestException as e:
            log_error(f"请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            log_error(f"JSON 解析失败: {str(e)}")
            return None
        except Exception as e:
            log_error(f"查询异常: {str(e)}")
            return None
