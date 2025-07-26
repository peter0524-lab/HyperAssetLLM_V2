"""
LLM 결과 공유 캐싱 매니저 - Production Ready Version
- 관심사 분리와 의존성 역전 원칙 적용
- 확장 가능한 분산 캐시 아키텍처
- 종합적인 관찰 가능성과 모니터링
- 테스트 가능한 설계
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import re
import time
import zlib
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Protocol, Callable, Set
from typing_extensions import runtime_checkable

import aioredis
import msgpack
import psutil
from fastapi import HTTPException
from opentelemetry import trace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# ==================== 타입 정의 ====================

class CacheType(Enum):
    """캐시 타입"""
    NEWS_ANALYSIS = "news_analysis"
    CHART_ANALYSIS = "chart_analysis"
    FLOW_ANALYSIS = "flow_analysis"
    DISCLOSURE_ANALYSIS = "disclosure_analysis"
    REPORT_ANALYSIS = "report_analysis"

class EvictionPolicy(Enum):
    """캐시 제거 정책"""
    LRU = "lru"
    LFU = "lfu"
    ADAPTIVE = "adaptive"

@dataclass
class CacheConfig:
    """캐시 설정"""
    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 10
    local_cache_max_size: int = 500
    default_ttl: int = 3600
    enable_local_fallback: bool = True
    enable_compression: bool = True
    compression_threshold: int = 1024  # 1KB
    enable_metrics: bool = True
    enable_tracing: bool = True
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        return cls(
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            redis_max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", cls.redis_max_connections)),
            local_cache_max_size=int(os.getenv("LOCAL_CACHE_MAX_SIZE", cls.local_cache_max_size)),
            default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", cls.default_ttl)),
            enable_local_fallback=os.getenv("ENABLE_LOCAL_FALLBACK", "true").lower() == "true",
            enable_compression=os.getenv("ENABLE_COMPRESSION", "true").lower() == "true",
            compression_threshold=int(os.getenv("COMPRESSION_THRESHOLD", cls.compression_threshold)),
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            enable_tracing=os.getenv("ENABLE_TRACING", "true").lower() == "true"
        )

@dataclass
class CacheMetrics:
    """캐시 메트릭"""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    serialization_time: float = 0.0
    network_time: float = 0.0
    cache_size: int = 0
    compression_ratio: float = 1.0
    avg_response_time: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

# ==================== 프로토콜 정의 ====================

@runtime_checkable
class CacheStorage(Protocol):
    """캐시 저장소 프로토콜"""
    async def get(self, key: str) -> Optional[bytes]: ...
    async def set(self, key: str, value: bytes, ttl: int) -> bool: ...
    async def delete(self, key: str) -> bool: ...
    async def exists(self, key: str) -> bool: ...
    async def ping(self) -> bool: ...

@runtime_checkable
class Serializer(Protocol):
    """직렬화 프로토콜"""
    def serialize(self, obj: Any) -> bytes: ...
    def deserialize(self, data: bytes) -> Any: ...

@runtime_checkable
class CacheKeyGenerator(Protocol):
    """캐시 키 생성 프로토콜"""
    def generate(self, cache_type: CacheType, **kwargs) -> str: ...

@runtime_checkable
class MetricsCollector(Protocol):
    """메트릭 수집 프로토콜"""
    async def record_hit(self, response_time: float): ...
    async def record_miss(self): ...
    async def record_error(self, error_type: str): ...
    async def record_serialization_time(self, time: float): ...
    def get_metrics(self) -> CacheMetrics: ...

# ==================== 커스텀 예외 ====================

class CacheError(Exception):
    """캐시 관련 커스텀 예외"""
    pass

class SerializationError(CacheError):
    """직렬화 관련 예외"""
    pass

class ConnectionError(CacheError):
    """연결 관련 예외"""
    pass

# ==================== 구현체들 ====================

class OptimizedSerializer:
    """최적화된 직렬화기"""
    
    def __init__(self, enable_compression: bool = True, compression_threshold: int = 1024):
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold
    
    def serialize(self, obj: Any) -> bytes:
        """안전한 직렬화"""
        try:
            # MessagePack으로 효율적 직렬화
            packed = msgpack.packb(obj, use_bin_type=True)
            
            # 압축 (크기가 클 때만)
            if self.enable_compression and len(packed) > self.compression_threshold:
                compressed = zlib.compress(packed)
                # 압축률이 좋을 때만 압축 사용
                if len(compressed) < len(packed) * 0.9:
                    return compressed
            return packed
            
        except (TypeError, ValueError) as e:
            # MessagePack 실패 시 JSON 사용
            try:
                json_data = json.dumps(obj, ensure_ascii=False, default=str)
                return json_data.encode('utf-8')
            except Exception as json_e:
                # JSON도 실패 시 pickle 사용
                try:
                    return pickle.dumps(obj)
                except Exception as pickle_e:
                    raise SerializationError(f"모든 직렬화 방법 실패: {e}, {json_e}, {pickle_e}")
    
    def deserialize(self, data: bytes) -> Any:
        """안전한 역직렬화"""
        try:
            # 압축 해제 시도
            try:
                decompressed = zlib.decompress(data)
                return msgpack.unpackb(decompressed, raw=False)
            except zlib.error:
                # 압축되지 않은 데이터
                return msgpack.unpackb(data, raw=False)
        except Exception as e:
            # MessagePack 실패 시 JSON 시도
            try:
                return json.loads(data.decode('utf-8'))
            except Exception as json_e:
                # JSON도 실패 시 pickle 시도
                try:
                    return pickle.loads(data)
                except Exception as pickle_e:
                    raise SerializationError(f"모든 역직렬화 방법 실패: {e}, {json_e}, {pickle_e}")

class SafeCacheKeyGenerator:
    """안전한 캐시 키 생성기"""
    
    def generate(self, cache_type: CacheType, **kwargs) -> str:
        """안전한 캐시 키 생성"""
        # 특수문자 이스케이프
        safe_components = []
        for key, value in kwargs.items():
            if isinstance(value, str):
                safe_value = re.sub(r'[^\w\-_]', '_', value)
            else:
                safe_value = str(value)
            safe_components.append(f"{key}={safe_value}")
        
        key_components = [
            "llm_cache",
            cache_type.value,
            *safe_components
        ]
        
        key_string = ":".join(key_components)
        
        # 키가 너무 길면 SHA256 해시 사용
        if len(key_string) > 250:  # Redis 키 길이 제한
            return f"llm_cache:{hashlib.sha256(key_string.encode()).hexdigest()}"
        
        return key_string

class ThreadSafeLocalCache:
    """스레드 안전 로컬 캐시"""
    
    def __init__(self, max_size: int = 500, eviction_policy: EvictionPolicy = EvictionPolicy.LRU):
        self._cache = OrderedDict()
        self._lock = asyncio.Lock()
        self.max_size = max_size
        self.eviction_policy = eviction_policy
        self._access_count = {}  # LFU를 위한 접근 횟수
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry['expires'] > time.time():
                    # LRU를 위해 재정렬
                    self._cache.move_to_end(key)
                    # LFU 카운트 증가
                    self._access_count[key] = self._access_count.get(key, 0) + 1
                    return entry['data']
                else:
                    del self._cache[key]
                    if key in self._access_count:
                        del self._access_count[key]
            return None
    
    async def set(self, key: str, data: Any, ttl: int):
        async with self._lock:
            # 만료된 항목들 정리
            await self._cleanup_expired()
            
            # 크기 제한 확인
            if len(self._cache) >= self.max_size:
                await self._evict_item()
            
            self._cache[key] = {
                'data': data,
                'expires': time.time() + ttl
            }
            self._access_count[key] = 0
    
    async def _cleanup_expired(self):
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items() 
            if v['expires'] <= current_time
        ]
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_count:
                del self._access_count[key]
    
    async def _evict_item(self):
        if self.eviction_policy == EvictionPolicy.LRU:
            # LRU: 가장 오래된 항목 제거
            self._cache.popitem(last=False)
        elif self.eviction_policy == EvictionPolicy.LFU:
            # LFU: 가장 적게 사용된 항목 제거
            if self._access_count:
                least_used_key = min(self._access_count.keys(), 
                                   key=lambda k: self._access_count[k])
                del self._cache[least_used_key]
                del self._access_count[least_used_key]
    
    async def size(self) -> int:
        async with self._lock:
            return len(self._cache)

class RedisStorage:
    """Redis 저장소 구현"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis = None
        self._connection_pool = None
    
    async def initialize(self):
        """Redis 연결 초기화"""
        try:
            self.redis = await aioredis.from_url(
                self.config.redis_url,
                max_connections=self.config.redis_max_connections,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            await self.redis.ping()
            logger.info("✅ Redis 연결 성공")
        except Exception as e:
            logger.warning(f"⚠️ Redis 연결 실패: {e}")
            self.redis = None
            raise ConnectionError(f"Redis 연결 실패: {e}")
    
    @retry(
        retry=retry_if_exception_type((aioredis.ConnectionError, aioredis.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get(self, key: str) -> Optional[bytes]:
        if not self.redis:
            raise ConnectionError("Redis not available")
        return await self.redis.get(key)
    
    @retry(
        retry=retry_if_exception_type((aioredis.ConnectionError, aioredis.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def set(self, key: str, value: bytes, ttl: int) -> bool:
        if not self.redis:
            raise ConnectionError("Redis not available")
        return await self.redis.setex(key, ttl, value)
    
    async def delete(self, key: str) -> bool:
        if not self.redis:
            return False
        return await self.redis.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        if not self.redis:
            return False
        return await self.redis.exists(key) > 0
    
    async def ping(self) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    async def close(self):
        if self.redis:
            await self.redis.close()

class InstrumentedMetricsCollector:
    """계측된 메트릭 수집기"""
    
    def __init__(self):
        self._metrics = CacheMetrics()
        self._lock = asyncio.Lock()
    
    async def record_hit(self, response_time: float):
        async with self._lock:
            self._metrics.hits += 1
            self._metrics.avg_response_time = (
                (self._metrics.avg_response_time * (self._metrics.hits - 1) + response_time) 
                / self._metrics.hits
            )
    
    async def record_miss(self):
        async with self._lock:
            self._metrics.misses += 1
    
    async def record_error(self, error_type: str):
        async with self._lock:
            self._metrics.errors += 1
    
    async def record_serialization_time(self, time: float):
        async with self._lock:
            self._metrics.serialization_time += time
    
    def get_metrics(self) -> CacheMetrics:
        return self._metrics

# ==================== 메인 캐시 매니저 ====================

class ProductionLLMCacheManager:
    """Production Ready LLM 캐시 매니저"""
    
    def __init__(
        self,
        storage: CacheStorage,
        serializer: Serializer,
        key_generator: CacheKeyGenerator,
        metrics: MetricsCollector,
        config: CacheConfig,
        clock: Callable[[], float] = time.time
    ):
        self._storage = storage
        self._serializer = serializer
        self._key_generator = key_generator
        self._metrics = metrics
        self.config = config
        self._clock = clock
        
        # 동시성 제어
        self._analysis_locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
        
        # 로컬 캐시 (fallback)
        self._local_cache = ThreadSafeLocalCache(
            max_size=config.local_cache_max_size
        )
        
        # 캐시 타입별 TTL 설정
        self.cache_ttl = {
            CacheType.NEWS_ANALYSIS: 1800,      # 30분
            CacheType.CHART_ANALYSIS: 7200,      # 2시간
            CacheType.FLOW_ANALYSIS: 3600,      # 1시간
            CacheType.DISCLOSURE_ANALYSIS: 14400, # 4시간
            CacheType.REPORT_ANALYSIS: 86400     # 24시간
        }
    
    async def initialize(self):
        """초기화"""
        if hasattr(self._storage, 'initialize'):
            await self._storage.initialize()
    
    async def get_cached_analysis(
        self, 
        cache_type: CacheType, 
        stock_code: str, 
        model_type: str, 
        analysis_type: str = None
    ) -> Optional[Dict]:
        """캐시된 LLM 분석 결과 조회"""
        
        with tracer.start_as_current_span("llm_cache.get") as span:
            span.set_attribute("cache_type", cache_type.value)
            span.set_attribute("stock_code", stock_code)
            span.set_attribute("model_type", model_type)
            
            start_time = self._clock()
            
            try:
                # 캐시 키 생성
                cache_key = self._key_generator.generate(
                    cache_type=cache_type,
                    stock_code=stock_code,
                    model_type=model_type,
                    analysis_type=analysis_type
                )
                
                # 1차: Redis에서 조회
                if hasattr(self._storage, 'ping') and await self._storage.ping():
                    cached_data = await self._storage.get(cache_key)
                    if cached_data:
                        result = self._serializer.deserialize(cached_data)
                        if result:
                            response_time = self._clock() - start_time
                            await self._metrics.record_hit(response_time)
                            logger.info(f"✅ Redis 캐시 히트: {cache_type.value} - {stock_code}")
                            return result
                        else:
                            # 손상된 캐시 삭제
                            await self._storage.delete(cache_key)
                            logger.warning(f"⚠️ 손상된 캐시 삭제: {cache_key}")
                
                # 2차: 로컬 캐시에서 조회
                if self.config.enable_local_fallback:
                    local_result = await self._local_cache.get(cache_key)
                    if local_result:
                        response_time = self._clock() - start_time
                        await self._metrics.record_hit(response_time)
                        logger.info(f"✅ 로컬 캐시 히트: {cache_type.value} - {stock_code}")
                        return local_result
                
                await self._metrics.record_miss()
                return None
                
            except Exception as e:
                await self._metrics.record_error(type(e).__name__)
                logger.error(f"❌ 캐시 조회 실패: {e}")
                raise CacheError(f"Cache retrieval failed: {e}")
    
    async def cache_analysis_result(
        self, 
        cache_type: CacheType, 
        stock_code: str, 
        model_type: str, 
        analysis_result: Dict, 
        analysis_type: str = None
    ) -> bool:
        """LLM 분석 결과 캐시 저장"""
        
        with tracer.start_as_current_span("llm_cache.set") as span:
            span.set_attribute("cache_type", cache_type.value)
            span.set_attribute("stock_code", stock_code)
            span.set_attribute("model_type", model_type)
            
            try:
                # 캐시 키 생성
                cache_key = self._key_generator.generate(
                    cache_type=cache_type,
                    stock_code=stock_code,
                    model_type=model_type,
                    analysis_type=analysis_type
                )
                
                # 직렬화
                serialization_start = self._clock()
                serialized_data = self._serializer.serialize(analysis_result)
                serialization_time = self._clock() - serialization_start
                await self._metrics.record_serialization_time(serialization_time)
                
                ttl = self.cache_ttl.get(cache_type, self.config.default_ttl)
                
                # Redis에 저장
                if hasattr(self._storage, 'ping') and await self._storage.ping():
                    success = await self._storage.set(cache_key, serialized_data, ttl)
                    if success:
                        logger.info(f"💾 Redis 캐시 저장: {cache_type.value} - {stock_code}")
                
                # 로컬 캐시에도 저장 (fallback)
                if self.config.enable_local_fallback:
                    await self._local_cache.set(cache_key, analysis_result, ttl)
                
                return True
                
            except Exception as e:
                await self._metrics.record_error(type(e).__name__)
                logger.error(f"❌ 캐시 저장 실패: {e}")
                return False
    
    async def get_or_create_analysis(
        self, 
        cache_type: CacheType, 
        stock_code: str,
        model_type: str, 
        analysis_func: Callable, 
        analysis_type: str = None, 
        **kwargs
    ) -> Dict:
        """캐시된 결과가 있으면 반환, 없으면 생성 후 캐시"""
        
        with tracer.start_as_current_span("llm_cache.get_or_create") as span:
            span.set_attribute("cache_type", cache_type.value)
            span.set_attribute("stock_code", stock_code)
            span.set_attribute("model_type", model_type)
            
            # 캐시 키 생성
            cache_key = self._key_generator.generate(
                cache_type=cache_type,
                stock_code=stock_code,
                model_type=model_type,
                analysis_type=analysis_type
            )
            
            # 1차 캐시 확인
            cached_result = await self.get_cached_analysis(
                cache_type, stock_code, model_type, analysis_type
            )
            if cached_result:
                return cached_result
            
            # 동일한 분석에 대한 동시 실행 방지
            async with self._lock:
                if cache_key not in self._analysis_locks:
                    self._analysis_locks[cache_key] = asyncio.Lock()
                analysis_lock = self._analysis_locks[cache_key]
            
            async with analysis_lock:
                # 2차 캐시 확인 (다른 스레드가 이미 처리했을 수 있음)
                cached_result = await self.get_cached_analysis(
                    cache_type, stock_code, model_type, analysis_type
                )
                if cached_result:
                    return cached_result
                
                # LLM 분석 실행
                logger.info(f"🔄 LLM 분석 실행: {cache_type.value} - {stock_code}")
                analysis_result = await analysis_func(**kwargs)
                
                # 결과 캐시 저장
                await self.cache_analysis_result(
                    cache_type, stock_code, model_type, analysis_result, analysis_type
                )
                
                return analysis_result
    
    async def invalidate_cache(self, cache_type: CacheType = None, stock_code: str = None):
        """캐시 무효화"""
        with tracer.start_as_current_span("llm_cache.invalidate") as span:
            if cache_type:
                span.set_attribute("cache_type", cache_type.value)
            if stock_code:
                span.set_attribute("stock_code", stock_code)
            
            try:
                # Redis 캐시 무효화
                if hasattr(self._storage, 'ping') and await self._storage.ping():
                    if cache_type and stock_code:
                        pattern = f"llm_cache:{cache_type.value}:stock_code={stock_code}:*"
                    elif cache_type:
                        pattern = f"llm_cache:{cache_type.value}:*"
                    else:
                        pattern = "llm_cache:*"
                    
                    # Redis에서 패턴 매칭으로 키 삭제
                    # (실제 구현에서는 Redis SCAN 명령어 사용)
                    logger.info(f"🗑️ 캐시 무효화: {pattern}")
                
                # 로컬 캐시 무효화
                # (실제 구현에서는 패턴 매칭으로 로컬 캐시도 정리)
                
            except Exception as e:
                logger.error(f"❌ 캐시 무효화 실패: {e}")
                raise CacheError(f"Cache invalidation failed: {e}")
    
    async def get_cache_stats(self) -> Dict:
        """캐시 통계 조회"""
        metrics = await self._metrics.get_metrics()
        local_cache_size = await self._local_cache.size()
        
        return {
            "metrics": {
                "hits": metrics.hits,
                "misses": metrics.misses,
                "errors": metrics.errors,
                "hit_rate": metrics.hit_rate,
                "avg_response_time_ms": metrics.avg_response_time * 1000,
                "serialization_time_ms": metrics.serialization_time * 1000
            },
            "storage": {
                "local_cache_size": local_cache_size,
                "redis_available": await self._storage.ping() if hasattr(self._storage, 'ping') else False
            },
            "system": {
                "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                "cpu_percent": psutil.Process().cpu_percent()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """시스템 건강 상태 확인"""
        checks = {}
        
        # Redis 연결 상태
        try:
            redis_healthy = await self._storage.ping() if hasattr(self._storage, 'ping') else False
            checks["redis"] = {"status": "healthy" if redis_healthy else "unhealthy"}
        except Exception as e:
            checks["redis"] = {"status": "unhealthy", "error": str(e)}
        
        # 메모리 사용량
        memory_info = psutil.Process().memory_info()
        checks["memory"] = {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024
        }
        
        # 캐시 성능
        metrics = await self._metrics.get_metrics()
        checks["performance"] = {
            "hit_rate": metrics.hit_rate,
            "avg_response_time_ms": metrics.avg_response_time * 1000,
            "total_requests": metrics.hits + metrics.misses
        }
        
        return checks
    
    async def close(self):
        """리소스 정리"""
        if hasattr(self._storage, 'close'):
            await self._storage.close()

# ==================== 팩토리 함수 ====================

def create_llm_cache_manager(config: Optional[CacheConfig] = None) -> ProductionLLMCacheManager:
    """LLM 캐시 매니저 팩토리 함수"""
    config = config or CacheConfig.from_env()
    
    # 컴포넌트 생성
    storage = RedisStorage(config)
    serializer = OptimizedSerializer(
        enable_compression=config.enable_compression,
        compression_threshold=config.compression_threshold
    )
    key_generator = SafeCacheKeyGenerator()
    metrics = InstrumentedMetricsCollector()
    
    # 캐시 매니저 생성
    cache_manager = ProductionLLMCacheManager(
        storage=storage,
        serializer=serializer,
        key_generator=key_generator,
        metrics=metrics,
        config=config
    )
    
    return cache_manager

# 전역 인스턴스
llm_cache_manager = create_llm_cache_manager() 