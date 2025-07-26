"""
사용자 설정 관리자 클래스
MySQL에서 사용자별 설정을 조회하고 캐싱하는 기능
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from shared.database.mysql_client import MySQLClient
from .user_config_schema import CREATE_ALL_TABLES

logger = logging.getLogger(__name__)

class UserConfigManager:
    """사용자 설정 관리자"""
    
    def __init__(self):
        self.mysql_client = MySQLClient()
        self._cache = {}  # 메모리 캐시
        self._cache_ttl = 300  # 캐시 TTL (5분)
        self._cache_timestamps = {}  # 캐시 타임스탬프
        
    async def initialize_tables(self):
        """사용자 설정 테이블들 초기화"""
        try:
            for query in CREATE_ALL_TABLES:
                await self.mysql_client.execute_query_async(query)
            logger.info("✅ 사용자 설정 테이블 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 사용자 설정 테이블 초기화 실패: {e}")
            raise
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        return (datetime.now() - cache_time).total_seconds() < self._cache_ttl
    
    def _set_cache(self, cache_key: str, data: Any):
        """캐시 설정"""
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.now()
    
    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """캐시 조회"""
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        return None
    
    def _clear_cache(self, user_id = None):
        """캐시 클리어"""
        if user_id:
            # 특정 사용자 캐시만 클리어
            keys_to_remove = [k for k in self._cache.keys() if f"user_{user_id}" in k or f"_{user_id}" in k]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
        else:
            # 전체 캐시 클리어
            self._cache.clear()
            self._cache_timestamps.clear()
    
    async def get_user_config(self, user_id) -> Dict:
        """사용자 전체 설정 조회 (캐싱 포함)"""
        cache_key = f"user_config_{user_id}"
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            logger.debug(f"📋 캐시에서 사용자 설정 조회: {user_id}")
            return cached_data
        
        try:
            # 사용자 프로필 조회
            profile_query = """
            SELECT user_id, username, phone_number, 
                   news_similarity_threshold, news_impact_threshold
            FROM user_profiles 
            WHERE user_id = %s
            """
            profile_result = await self.mysql_client.execute_query_async(
                profile_query, (user_id,), fetch=True
            )
            
            if not profile_result:
                logger.warning(f"⚠️ 사용자 프로필 없음: {user_id}")
                return self._get_default_config()
            
            profile = profile_result[0]
            
            # 사용자 종목 조회
            stocks_query = """
            SELECT stock_code, stock_name, enabled
            FROM user_stocks 
            WHERE user_id = %s AND enabled = TRUE
            ORDER BY stock_code
            """
            stocks_result = await self.mysql_client.execute_query_async(
                stocks_query, (user_id,), fetch=True
            )
            
            # 사용자 모델 조회
            model_query = """
            SELECT model_type
            FROM user_model 
            WHERE user_id = %s
            """
            model_result = await self.mysql_client.execute_query_async(
                model_query, (user_id,), fetch=True
            )
            
            # 설정 조합
            config = {
                "user_id": profile["user_id"],
                "username": profile["username"],
                "phone_number": profile["phone_number"],
                "news_similarity_threshold": float(profile["news_similarity_threshold"]),
                "news_impact_threshold": float(profile["news_impact_threshold"]),
                "stocks": [
                    {
                        "stock_code": stock["stock_code"],
                        "stock_name": stock["stock_name"],
                        "enabled": bool(stock["enabled"])
                    }
                    for stock in stocks_result
                ],
                "model_type": model_result[0]["model_type"] if model_result else "hyperclova"
            }
            
            # 캐시에 저장
            self._set_cache(cache_key, config)
            logger.info(f"✅ 사용자 설정 조회 완료: {user_id} ({len(config['stocks'])}개 종목)")
            
            return config
            
        except Exception as e:
            logger.error(f"❌ 사용자 설정 조회 실패: {e}")
            return self._get_default_config()
    
    async def update_user_config(self, user_id, config_data: Dict) -> bool:
        """사용자 전체 설정 업데이트 (중앙 집중식)"""
        try:
            logger.info(f"🔄 사용자 설정 업데이트 시작: {user_id}")
            
            # 1. 모델 타입 업데이트
            if "model_type" in config_data:
                await self.set_user_model(user_id, config_data["model_type"])
            
            # 2. 종목 설정 업데이트
            if "stocks" in config_data:
                await self.update_user_stocks(user_id, config_data["stocks"])
            
            # 3. 임계값 업데이트
            threshold_updates = {}
            if "news_similarity_threshold" in config_data:
                threshold_updates["news_similarity_threshold"] = config_data["news_similarity_threshold"]
            if "news_impact_threshold" in config_data:
                threshold_updates["news_impact_threshold"] = config_data["news_impact_threshold"]
            
            if threshold_updates:
                await self.update_user_thresholds(user_id, threshold_updates)
            
            # 4. 캐시 갱신
            self._clear_cache(user_id)
            await self.get_user_config(user_id)  # 캐시 재생성
            
            logger.info(f"✅ 사용자 설정 업데이트 완료: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 사용자 설정 업데이트 실패: {e}")
            return False
    
    async def set_user_model(self, user_id, model_type: str) -> bool:
        """사용자 모델 타입 설정 (UPSERT)"""
        try:
            # UPSERT 쿼리 (INSERT ON DUPLICATE KEY UPDATE)
            query = """
            INSERT INTO user_model (user_id, model_type, updated_at) 
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
            model_type = VALUES(model_type), 
            updated_at = NOW()
            """
            
            await self.mysql_client.execute_query_async(query, (user_id, model_type))
            
            # 캐시 갱신
            self._clear_cache(user_id)
            
            logger.info(f"✅ 사용자 모델 설정 완료: {user_id} -> {model_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 사용자 모델 설정 실패: {e}")
            return False
    
    async def update_user_stocks(self, user_id, stocks: List[Dict]) -> bool:
        """사용자 종목 설정 업데이트"""
        try:
            # 기존 종목 비활성화
            disable_query = """
            UPDATE user_stocks 
            SET enabled = FALSE, updated_at = NOW()
            WHERE user_id = %s
            """
            await self.mysql_client.execute_query_async(disable_query, (user_id,))
            
            # 새 종목 설정 (UPSERT)
            for stock in stocks:
                stock_code = stock.get("stock_code")
                stock_name = stock.get("stock_name", stock_code)
                enabled = stock.get("enabled", True)
                
                upsert_query = """
                INSERT INTO user_stocks (user_id, stock_code, stock_name, enabled, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                stock_name = VALUES(stock_name),
                enabled = VALUES(enabled),
                updated_at = NOW()
                """
                
                await self.mysql_client.execute_query_async(
                    upsert_query, (user_id, stock_code, stock_name, enabled)
                )
            
            # 캐시 갱신
            self._clear_cache(user_id)
            
            logger.info(f"✅ 사용자 종목 설정 완료: {user_id} ({len(stocks)}개 종목)")
            return True
            
        except Exception as e:
            logger.error(f"❌ 사용자 종목 설정 실패: {e}")
            return False
    
    async def update_user_thresholds(self, user_id, thresholds: Dict) -> bool:
        """사용자 임계값 설정 업데이트"""
        try:
            # 동적 쿼리 생성
            update_fields = []
            params = []
            
            if "news_similarity_threshold" in thresholds:
                update_fields.append("news_similarity_threshold = %s")
                params.append(thresholds["news_similarity_threshold"])
            
            if "news_impact_threshold" in thresholds:
                update_fields.append("news_impact_threshold = %s")
                params.append(thresholds["news_impact_threshold"])
            
            if not update_fields:
                return True  # 업데이트할 내용이 없음
            
            update_fields.append("updated_at = NOW()")
            params.append(user_id)
            
            query = f"""
            UPDATE user_profiles 
            SET {', '.join(update_fields)}
            WHERE user_id = %s
            """
            
            await self.mysql_client.execute_query_async(query, params)
            
            # 캐시 갱신
            self._clear_cache(user_id)
            
            logger.info(f"✅ 사용자 임계값 설정 완료: {user_id} -> {thresholds}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 사용자 임계값 설정 실패: {e}")
            return False

    async def get_user_stocks(self, user_id) -> List[Dict]:
        """사용자 종목 설정 조회"""
        cache_key = f"user_stocks_{user_id}"
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            query = """
            SELECT stock_code, stock_name, enabled
            FROM user_stocks 
            WHERE user_id = %s AND enabled = TRUE
            ORDER BY stock_code
            """
            result = await self.mysql_client.execute_query_async(
                query, (user_id,), fetch=True
            )
            
            stocks = [
                {
                    "stock_code": row["stock_code"],
                    "stock_name": row["stock_name"],
                    "enabled": bool(row["enabled"])
                }
                for row in result
            ]
            
            self._set_cache(cache_key, stocks)
            return stocks
            
        except Exception as e:
            logger.error(f"❌ 사용자 종목 조회 실패: {e}")
            return []
    
    async def get_user_thresholds(self, user_id) -> Dict:
        """사용자 임계값 설정 조회"""
        cache_key = f"user_thresholds_{user_id}"
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            query = """
            SELECT news_similarity_threshold, news_impact_threshold
            FROM user_profiles 
            WHERE user_id = %s
            """
            result = await self.mysql_client.execute_query_async(
                query, (user_id,), fetch=True
            )
            
            if result:
                thresholds = {
                    "news_similarity_threshold": float(result[0]["news_similarity_threshold"]),
                    "news_impact_threshold": float(result[0]["news_impact_threshold"])
                }
            else:
                thresholds = self._get_default_thresholds()
            
            self._set_cache(cache_key, thresholds)
            return thresholds
            
        except Exception as e:
            logger.error(f"❌ 사용자 임계값 조회 실패: {e}")
            return self._get_default_thresholds()
    
    async def get_user_model(self, user_id) -> str:
        """사용자 모델 타입 조회"""
        cache_key = f"user_model_{user_id}"
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            query = """
            SELECT model_type
            FROM user_model 
            WHERE user_id = %s
            """
            result = await self.mysql_client.execute_query_async(
                query, (user_id,), fetch=True
            )
            
            model_type = result[0]["model_type"] if result else "hyperclova"
            self._set_cache(cache_key, model_type)
            return model_type
            
        except Exception as e:
            logger.error(f"❌ 사용자 모델 조회 실패: {e}")
            return "hyperclova"
    
    def _get_default_config(self) -> Dict:
        """기본 설정 반환"""
        return {
            "user_id": 1,  # 기본 사용자 ID
            "username": "default_user",
            "phone_number": "01000000000",
            "news_similarity_threshold": 0.7,
            "news_impact_threshold": 0.8,
            "stocks": [
                {"stock_code": "005930", "stock_name": "삼성전자", "enabled": True},
                {"stock_code": "000660", "stock_name": "SK하이닉스", "enabled": True}
            ],
            "model_type": "hyperclova"
        }
    
    def _get_default_thresholds(self) -> Dict:
        """기본 임계값 반환"""
        return {
            "news_similarity_threshold": 0.7,
            "news_impact_threshold": 0.8
        }
    
    async def update_user_cache(self, user_id):
        """사용자 캐시 갱신"""
        self._clear_cache(user_id)
        await self.get_user_config(user_id)  # 캐시 재생성
        logger.info(f"🔄 사용자 캐시 갱신 완료: {user_id}")
    
    async def close(self):
        """리소스 정리"""
        try:
            await self.mysql_client.close()
            self._clear_cache()
            logger.info("✅ UserConfigManager 리소스 정리 완료")
        except Exception as e:
            logger.error(f"❌ UserConfigManager 정리 실패: {e}")


# 전역 인스턴스
user_config_manager = UserConfigManager() 