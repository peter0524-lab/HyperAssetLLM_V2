"""
UserConfigLoader - 마이크로서비스용 사용자 설정 로더

각 마이크로서비스가 시작할 때 사용자별 설정을 로드하여
개인화된 서비스를 제공할 수 있도록 하는 모듈
"""

import asyncio
import logging
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class UserConfigLoader:
    """사용자 설정 로더 클래스"""
    
    def __init__(self, api_gateway_url: str = "http://localhost:8005"):
        self.api_gateway_url = api_gateway_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.config_cache = {}
        self.cache_ttl = timedelta(minutes=5)  # 5분 캐시
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    async def load_user_config(self, user_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        사용자 종합 설정 로드
        
        Args:
            user_id: 사용자 ID
            force_refresh: 캐시 무시하고 강제 새로고침
            
        Returns:
            사용자 설정 딕셔너리 또는 None
        """
        try:
            # 캐시 확인
            if not force_refresh and user_id in self.config_cache:
                cached_data, cached_time = self.config_cache[user_id]
                if datetime.now() - cached_time < self.cache_ttl:
                    logger.debug(f"📦 사용자 설정 캐시 반환: {user_id}")
                    return cached_data
            
            # API 호출
            response = await self.http_client.get(f"{self.api_gateway_url}/users/{user_id}/config")
            response.raise_for_status()
            
            result = response.json()
            if result.get("success"):
                config_data = result.get("data")
                
                # 캐시 저장
                self.config_cache[user_id] = (config_data, datetime.now())
                
                logger.info(f"✅ 사용자 설정 로드 완료: {user_id}")
                return config_data
            else:
                logger.warning(f"⚠️ 사용자 설정 로드 실패: {user_id} - {result.get('message')}")
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"⚠️ 사용자를 찾을 수 없음: {user_id}")
            else:
                logger.error(f"❌ HTTP 에러 - 사용자 설정 로드 실패: {user_id} - {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 사용자 설정 로드 실패: {user_id} - {e}")
            return None
    
    async def get_user_stocks(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자의 활성화된 종목 목록 조회"""
        config = await self.load_user_config(user_id)
        return config.get("stocks", []) if config else []
    
    async def get_user_model(self, user_id: str) -> str:
        """사용자의 선택된 AI 모델 조회"""
        config = await self.load_user_config(user_id)
        return config.get("model_type", "hyperclova") if config else "hyperclova"
    
    async def get_user_thresholds(self, user_id: str) -> Dict[str, float]:
        """사용자의 임계값 설정 조회"""
        config = await self.load_user_config(user_id)
        if not config:
            return {
                "news_similarity_threshold": 0.7,
                "news_impact_threshold": 0.8
            }
        
        return {
            "news_similarity_threshold": config.get("news_similarity_threshold", 0.7),
            "news_impact_threshold": config.get("news_impact_threshold", 0.8)
        }
    
    async def is_service_active_for_user(self, user_id: str, service_name: str) -> bool:
        """특정 사용자에 대해 해당 서비스가 활성화되어 있는지 확인"""
        config = await self.load_user_config(user_id)
        if not config:
            return False
        
        active_services = config.get("active_services", {})
        return bool(active_services.get(f"{service_name}_service", 0))
    
    async def get_all_active_users(self) -> List[str]:
        """
        모든 활성 사용자 ID 목록 조회
        
        주의: 이 메서드는 별도의 API가 필요하며, 현재는 캐시된 사용자만 반환
        """
        return list(self.config_cache.keys())
    
    def clear_cache(self, user_id: Optional[str] = None):
        """캐시 클리어"""
        if user_id:
            self.config_cache.pop(user_id, None)
            logger.debug(f"🧹 사용자 설정 캐시 클리어: {user_id}")
        else:
            self.config_cache.clear()
            logger.debug("🧹 모든 사용자 설정 캐시 클리어")
    
    async def close(self):
        """리소스 정리"""
        await self.http_client.aclose()

# 전역 인스턴스 (싱글톤 패턴)
_global_config_loader = None

async def get_config_loader() -> UserConfigLoader:
    """전역 설정 로더 인스턴스 반환"""
    global _global_config_loader
    if _global_config_loader is None:
        _global_config_loader = UserConfigLoader()
    return _global_config_loader

async def cleanup_config_loader():
    """전역 설정 로더 정리"""
    global _global_config_loader
    if _global_config_loader:
        await _global_config_loader.close()
        _global_config_loader = None 