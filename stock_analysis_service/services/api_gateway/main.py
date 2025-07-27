"""
API Gateway Service - 성능 및 모니터링 최적화 버전
- 모든 마이크로서비스의 단일 진입점
- 고성능 비동기 처리 및 연결 풀링
- 통합 모니터링 및 메트릭 수집
- 캐싱 및 Circuit Breaker 패턴
- 로드 밸런싱 및 헬스체크
"""

import asyncio
import aiohttp
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import sys
import os

# FastAPI 및 관련 패키지
from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 모니터링 및 메트릭 (옵셔널)
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

# Circuit Breaker (옵셔널)
try:
    from pybreaker import CircuitBreaker
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

# 캐싱 (옵셔널)
try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    
from functools import wraps

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# config 경로 직접 추가
config_path = project_root / "config"
sys.path.append(str(config_path))

from env_local import get_config

# User Config Manager 추가
from shared.user_config.user_config_manager import user_config_manager

# Service Manager 추가
from service_manager import ServiceManager

# 구조화된 로깅 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus 메트릭 정의 (중복 방지 - 새 레지스트리 사용)
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge
custom_registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    'api_gateway_requests_total',
    'Total API requests',
    ['method', 'service', 'endpoint', 'status_code'],
    registry=custom_registry
)

REQUEST_DURATION = Histogram(
    'api_gateway_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'service', 'endpoint'],
    registry=custom_registry
)

ACTIVE_CONNECTIONS = Gauge(
    'api_gateway_active_connections',
    'Number of active connections to backend services',
    ['service'],
    registry=custom_registry
)

BACKEND_RESPONSE_TIME = Histogram(
    'api_gateway_backend_response_seconds',
    'Backend service response time',
    ['service'],
    registry=custom_registry
)

CACHE_HITS = Counter(
    'api_gateway_cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=custom_registry
)

CACHE_MISSES = Counter(
    'api_gateway_cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=custom_registry
)

CIRCUIT_BREAKER_STATE = Gauge(
    'api_gateway_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service'],
    registry=custom_registry
)

# FastAPI 앱 생성
app = FastAPI(
    title="Stock Analysis API Gateway - Optimized",
    description="고성능 주식 분석 시스템 API Gateway",
    version="2.0.0"
)

# Service Manager 인스턴스 생성
service_manager = ServiceManager()

# CORS 설정 (개발 모드 - 모든 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 서비스 상태 열거형
class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class ServiceConfig:
    name: str
    instances: List[str]  # 여러 인스턴스 지원
    base_path: str
    enabled: bool
    circuit_breaker: CircuitBreaker
    health_check_interval: int = 30
    timeout: float = 10.0
    retry_count: int = 3

class LoadBalancer:
    """라운드 로빈 로드 밸런서"""

    def __init__(self):
        self.current_index = {}

    def get_next_instance(self, service_name: str, instances: List[str]) -> str:
        if service_name not in self.current_index:
            self.current_index[service_name] = 0

        instance = instances[self.current_index[service_name]]
        self.current_index[service_name] = (self.current_index[service_name] + 1) % len(instances)
        return instance

class CacheManager:
    """Redis 기반 캐시 매니저"""

    def __init__(self):
        self.redis = None
        self.local_cache = {}  # 백업 로컬 캐시
        self.cache_ttl = 300  # 기본 5분

    async def initialize(self):
        """Redis 연결 초기화"""
        try:
            self.redis = await aioredis.from_url("redis://localhost:6379")
            await self.redis.ping()
            logger.info("Redis 캐시 연결 성공")
        except Exception as e:
            logger.warning(f"Redis 연결 실패, 로컬 캐시 사용: {e}")
            self.redis = None

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        try:
            if self.redis:
                value = await self.redis.get(key)
                if value:
                    CACHE_HITS.labels(cache_type="redis").inc()
                    return json.loads(value)
                else:
                    CACHE_MISSES.labels(cache_type="redis").inc()
            else:
                # 로컬 캐시 사용
                cache_entry = self.local_cache.get(key)
                if cache_entry and cache_entry['expires'] > time.time():
                    CACHE_HITS.labels(cache_type="local").inc()
                    return cache_entry['data']
                else:
                    CACHE_MISSES.labels(cache_type="local").inc()
                    if key in self.local_cache:
                        del self.local_cache[key]
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        try:
            ttl = ttl or self.cache_ttl

            if self.redis:
                await self.redis.setex(key, ttl, json.dumps(value))
            else:
                # 로컬 캐시 사용
                self.local_cache[key] = {
                    'data': value,
                    'expires': time.time() + ttl
                }

                # 로컬 캐시 크기 제한 (1000개)
                if len(self.local_cache) > 1000:
                    oldest_key = min(self.local_cache.keys(),
                                     key=lambda k: self.local_cache[k]['expires'])
                    del self.local_cache[oldest_key]

            return True
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
            return False

    def generate_cache_key(self, service: str, method: str, path: str, params: Dict = None) -> str:
        """캐시 키 생성"""
        key_data = f"{service}:{method}:{path}"
        if params:
            key_data += f":{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

class OptimizedAPIGateway:
    """최적화된 API Gateway 클래스"""

    def __init__(self):
        self.config = get_config()
        self.session_pool = {}  # 서비스별 세션 풀
        self.load_balancer = LoadBalancer()
        self.cache_manager = CacheManager()

        # Circuit Breaker 설정
        self.circuit_breakers = {}

        # 서비스 설정
        self.services = {
            "news": ServiceConfig(
                name="News Service",
                instances=["http://localhost:8001"],
                base_path="/api/news",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=5,
                    reset_timeout=60,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=60.0
            ),
            "disclosure": ServiceConfig(
                name="Disclosure Service",
                instances=["http://localhost:8002"],
                base_path="/api/disclosure",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=5,
                    reset_timeout=60,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=20.0
            ),
            "chart": ServiceConfig(
                name="Chart Service",
                instances=["http://localhost:8003"],
                base_path="/api/chart",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=3,
                    reset_timeout=30,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=10.0
            ),
            "report": ServiceConfig(
                name="Report Service",
                instances=["http://localhost:8004"],
                base_path="/api/report",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=5,
                    reset_timeout=120,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=30.0
            ),
            "flow_analysis": ServiceConfig(
                name="Flow Analysis Service",
                instances=["http://localhost:8010"],
                base_path="/api/flow",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=5,
                    reset_timeout=60,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=15.0
            ),
            "user": ServiceConfig(
                name="User Service",
                instances=["http://localhost:8006"],
                base_path="/api/user",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=3,
                    reset_timeout=30,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=5.0
            ),
            "orchestrator": ServiceConfig(
                name="Orchestrator Service",
                instances=["http://localhost:8000"],
                base_path="/api/orchestrator",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=3,
                    reset_timeout=30,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=10.0
            ),
            "issue_scheduler": ServiceConfig(
                name="Issue Scheduler Service",
                instances=["http://localhost:8007"],
                base_path="/api/issue",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=5,
                    reset_timeout=60,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=15.0
            ),
            "business_report": ServiceConfig(
                name="Business Report Service",
                instances=["http://localhost:8008"],
                base_path="/api/business",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=5,
                    reset_timeout=60,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=30.0
            ),
            "analysis": ServiceConfig(
                name="Analysis Service",
                instances=["http://localhost:8009"],
                base_path="/api/analysis",
                enabled=True,
                circuit_breaker=CircuitBreaker(
                    fail_max=5,
                    reset_timeout=60,
                    exclude=[aiohttp.ClientTimeout]
                ),
                timeout=20.0
            )
        }

        # 헬스체크 상태
        self.service_health = {}

    async def initialize(self):
        """Gateway 초기화"""
        await self.cache_manager.initialize()
        await self._initialize_session_pools()

        # 백그라운드 헬스체크 시작
        asyncio.create_task(self._background_health_check())

        logger.info("API Gateway 초기화 완료")

    async def _initialize_session_pools(self):
        """서비스별 HTTP 세션 풀 초기화"""
        for service_name, service_config in self.services.items():
            if service_config.enabled:
                connector = aiohttp.TCPConnector(
                    limit=100,  # 총 연결 수 제한
                    limit_per_host=30,  # 호스트당 연결 수 제한
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )

                timeout = aiohttp.ClientTimeout(total=service_config.timeout)

                self.session_pool[service_name] = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "User-Agent": "API-Gateway-Optimized/2.0",
                        "X-Gateway-Version": "2.0.0"
                    }
                )

                logger.info(f"세션 풀 초기화 완료: {service_name}")

    async def _background_health_check(self):
        """백그라운드 헬스체크"""
        while True:
            try:
                for service_name, service_config in self.services.items():
                    if service_config.enabled:
                        await self._check_service_health(service_name, service_config)

                await asyncio.sleep(30)  # 30초마다 헬스체크
            except Exception as e:
                logger.error(f"헬스체크 실패: {e}")
                await asyncio.sleep(60)

    async def _check_service_health(self, service_name: str, service_config: ServiceConfig):
        """개별 서비스 헬스체크"""
        healthy_instances = []

        for instance in service_config.instances:
            try:
                session = self.session_pool.get(service_name)
                if not session:
                    continue

                start_time = time.time()

                async with session.get(f"{instance}/health") as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        healthy_instances.append(instance)
                        BACKEND_RESPONSE_TIME.labels(service=service_name).observe(response_time)

                        # Circuit Breaker 상태 업데이트
                        if service_config.circuit_breaker.current_state == "open":
                            CIRCUIT_BREAKER_STATE.labels(service=service_name).set(1)
                        elif service_config.circuit_breaker.current_state == "half-open":
                            CIRCUIT_BREAKER_STATE.labels(service=service_name).set(2)
                        else:
                            CIRCUIT_BREAKER_STATE.labels(service=service_name).set(0)

            except Exception as e:
                logger.warning(f"헬스체크 실패: {service_name} - {instance}: {e}")

        # 서비스 상태 업데이트
        if len(healthy_instances) == len(service_config.instances):
            self.service_health[service_name] = ServiceStatus.HEALTHY
        elif len(healthy_instances) > 0:
            self.service_health[service_name] = ServiceStatus.DEGRADED
        else:
            self.service_health[service_name] = ServiceStatus.UNHEALTHY

        ACTIVE_CONNECTIONS.labels(service=service_name).set(len(healthy_instances))

    async def forward_request(
        self,
        service_name: str,
        method: str,
        path: str,
        headers: Dict = None,
        params: Dict = None,
        data: Any = None,
        use_cache: bool = True
    ) -> Dict:
        """요청을 해당 서비스로 전달 (최적화 버전)"""

        start_time = time.time()

        try:
            if service_name not in self.services:
                raise HTTPException(status_code=404, detail=f"Service {service_name} not found")

            service_config = self.services[service_name]
            if not service_config.enabled:
                raise HTTPException(status_code=503, detail=f"Service {service_name} is disabled")

            # 캐시 확인 (GET 요청만)
            cache_key = None
            if use_cache and method.upper() == "GET":
                cache_key = self.cache_manager.generate_cache_key(
                    service_name, method, path, params
                )
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result:
                    logger.info("캐시 히트", service=service_name, path=path)
                    return cached_result

            # 로드 밸런싱으로 인스턴스 선택
            healthy_instances = [
                instance for instance in service_config.instances
                if self.service_health.get(service_name) in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
            ]

            if not healthy_instances:
                raise HTTPException(status_code=503, detail=f"No healthy instances for {service_name}")

            target_instance = self.load_balancer.get_next_instance(service_name, healthy_instances)
            target_url = f"{target_instance}{path}"

            # 요청 헤더 설정
            request_headers = {
                "Content-Type": "application/json",
                "X-Gateway-Request-ID": f"gw-{int(time.time() * 1000000)}",
                "X-Forwarded-For": "api-gateway"
            }
            if headers:
                request_headers.update(headers)

            # Circuit Breaker를 통한 요청 전송
            @service_config.circuit_breaker
            async def make_request():
                session = self.session_pool.get(service_name)
                if not session:
                    raise Exception(f"No session available for {service_name}")

                if method.upper() == "GET":
                    async with session.get(target_url, headers=request_headers, params=params) as response:
                        return await self._handle_response(response, service_name, start_time)
                elif method.upper() == "POST":
                    async with session.post(target_url, headers=request_headers, json=data) as response:
                        return await self._handle_response(response, service_name, start_time)
                elif method.upper() == "PUT":
                    async with session.put(target_url, headers=request_headers, json=data) as response:
                        return await self._handle_response(response, service_name, start_time)
                elif method.upper() == "DELETE":
                    async with session.delete(target_url, headers=request_headers) as response:
                        return await self._handle_response(response, service_name, start_time)
                else:
                    raise HTTPException(status_code=405, detail=f"Method {method} not allowed")

            result = await make_request()

            # 캐시 저장 (성공적인 GET 응답만)
            if use_cache and method.upper() == "GET" and cache_key and result.get("status_code", 500) < 400:
                await self.cache_manager.set(cache_key, result, ttl=300)

            # 메트릭 업데이트
            REQUEST_COUNT.labels(
                method=method,
                service=service_name,
                endpoint=path,
                status_code=result.get("status_code", 500)
            ).inc()

            REQUEST_DURATION.labels(
                method=method,
                service=service_name,
                endpoint=path
            ).observe(time.time() - start_time)

            return result

        except aiohttp.ClientError as e:
            logger.error(f"Service {service_name} connection error", error=str(e), path=path)
            REQUEST_COUNT.labels(
                method=method,
                service=service_name,
                endpoint=path,
                status_code=503
            ).inc()
            raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")

        except Exception as e:
            logger.error(f"Gateway error", error=str(e), service=service_name, path=path)
            REQUEST_COUNT.labels(
                method=method,
                service=service_name,
                endpoint=path,
                status_code=500
            ).inc()
            raise HTTPException(status_code=500, detail="Internal gateway error")

    async def _handle_response(self, response, service_name: str, start_time: float) -> Dict:
        """응답 처리"""
        try:
            response_time = time.time() - start_time
            BACKEND_RESPONSE_TIME.labels(service=service_name).observe(response_time)

            response_data = await response.json()

            if response.status >= 400:
                logger.warning(
                    f"Service {service_name} returned error",
                    status=response.status,
                    response_time=response_time
                )

            return {
                "data": response_data,
                "service": service_name,
                "timestamp": datetime.now().isoformat(),
                "status_code": response.status,
                "response_time": response_time
            }

        except json.JSONDecodeError:
            # JSON이 아닌 응답 처리
            text_response = await response.text()
            return {
                "data": {"message": text_response},
                "service": service_name,
                "timestamp": datetime.now().isoformat(),
                "status_code": response.status,
                "response_time": time.time() - start_time
            }

    async def close(self):
        """리소스 정리"""
        for session in self.session_pool.values():
            await session.close()

        if self.cache_manager.redis:
            await self.cache_manager.redis.close()

        logger.info("API Gateway 리소스 정리 완료")

# API Gateway 인스턴스
gateway = OptimizedAPIGateway()

# 미들웨어 설정
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """로깅 미들웨어"""
    start_time = time.time()
    request_id = f"req-{int(time.time() * 1000000)}"

    # 요청 로깅
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
        forwarded_for=request.headers.get("x-forwarded-for")
    )

    response = await call_next(request)

    # 응답 로깅
    process_time = time.time() - start_time
    logger.info(
        "request_completed",
        request_id=request_id,
        status_code=response.status_code,
        process_time=process_time
    )

    # 응답 시간 헤더 추가
    response.headers["X-Response-Time"] = f"{process_time:.3f}s"
    response.headers["X-Request-ID"] = request_id

    return response

# === 애플리케이션 라이프사이클 ===
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작시 실행"""
    logger.info("🚀 API Gateway 시작")
    await gateway.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료시 실행"""
    await gateway.close()
    logger.info("🛑 API Gateway 종료")

# === 루트 엔드포인트 ===
@app.get("/")
async def root():
    """API Gateway 루트"""
    return {
        "message": "Stock Analysis API Gateway - Optimized",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": {name: {
            "enabled": service.enabled,
            "instances": service.instances,
            "status": gateway.service_health.get(name, ServiceStatus.UNKNOWN).value
        } for name, service in gateway.services.items()}
    }

@app.get("/health")
async def health_check():
    """게이트웨이 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "gateway": "running",
        "version": "2.0.0"
    }

@app.get("/metrics")
async def get_metrics():
    """Prometheus 메트릭 엔드포인트"""
    return Response(generate_latest(), media_type="text/plain")

@app.get("/services/status")
async def check_all_services():
    """모든 서비스 상태 확인 (상세)"""
    results = {}

    for service_name, service_config in gateway.services.items():
        try:
            result = await gateway.forward_request(service_name, "GET", "/health", use_cache=False)
            results[service_name] = {
                "status": gateway.service_health.get(service_name, ServiceStatus.UNKNOWN).value,
                "instances": service_config.instances,
                "response_time": result.get("response_time", 0),
                "response": result["data"],
                "circuit_breaker_state": service_config.circuit_breaker.current_state
            }
        except Exception as e:
            results[service_name] = {
                "status": "unhealthy",
                "instances": service_config.instances,
                "error": str(e),
                "circuit_breaker_state": service_config.circuit_breaker.current_state
            }

    return {
        "timestamp": datetime.now().isoformat(),
        "services": results
    }

@app.get("/cache/stats")
async def get_cache_stats():
    """캐시 통계 정보"""
    stats = {}

    if gateway.cache_manager.redis:
        try:
            info = await gateway.cache_manager.redis.info()
            stats["redis"] = {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception:
            stats["redis"] = {"connected": False}
    else:
        stats["local_cache"] = {
            "size": len(gateway.cache_manager.local_cache),
            "max_size": 1000
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "cache_stats": stats
    }

# === 뉴스 서비스 라우팅 ===
@app.get("/api/news/health")
async def news_health():
    return await gateway.forward_request("news", "GET", "/health")

@app.get("/api/news/signal")
async def news_signal():
    return await gateway.forward_request("news", "GET", "/signal")

@app.post("/api/news/check-schedule")
async def news_check_schedule():
    return await gateway.forward_request("news", "POST", "/check-schedule", use_cache=False)

@app.post("/api/news/execute")
async def news_execute(request: Request):
    # user_id 추출 (Header 또는 Query Param에서)
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id", "1")
    headers = {"X-User-ID": str(user_id)}
    return await gateway.forward_request("news", "POST", "/execute", 
                                       headers=headers, use_cache=False)

# === 공시 서비스 라우팅 ===
@app.get("/api/disclosure/health")
async def disclosure_health():
    return await gateway.forward_request("disclosure", "GET", "/health")

@app.post("/api/disclosure/check-schedule")
async def disclosure_check_schedule():
    return await gateway.forward_request("disclosure", "POST", "/check-schedule", use_cache=False)

@app.post("/api/disclosure/execute")
async def disclosure_execute(request: Request):
    # user_id 추출 (Header 또는 Query Param에서)
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id", "1")
    headers = {"X-User-ID": str(user_id)}
    return await gateway.forward_request("disclosure", "POST", "/execute",
                                       headers=headers, use_cache=False)

@app.get("/api/disclosure/recent")
async def disclosure_recent():
    return await gateway.forward_request("disclosure", "GET", "/recent")

# === 차트 서비스 라우팅 ===
@app.get("/api/chart/health")
async def chart_health():
    return await gateway.forward_request("chart", "GET", "/health")

@app.post("/api/chart/check-schedule")
async def chart_check_schedule():
    return await gateway.forward_request("chart", "POST", "/check-schedule", use_cache=False)

@app.post("/api/chart/execute")
async def chart_execute(request: Request):
    # user_id 추출 (Header 또는 Query Param에서)
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id", "1")
    headers = {"X-User-ID": str(user_id)}
    return await gateway.forward_request("chart", "POST", "/execute",
                                       headers=headers, use_cache=False)

@app.get("/api/chart/analysis/{stock_code}")
async def chart_analysis(stock_code: str):
    return await gateway.forward_request("chart", "GET", f"/analysis/{stock_code}")

# === 리포트 서비스 라우팅 ===
@app.get("/api/report/health")
async def report_health():
    return await gateway.forward_request("report", "GET", "/health")

@app.post("/api/report/check-schedule")
async def report_check_schedule():
    return await gateway.forward_request("report", "POST", "/check-schedule", use_cache=False)

@app.post("/api/report/execute")
async def report_execute(request: Request):
    # user_id 추출 (Header 또는 Query Param에서)
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id", "1")
    headers = {"X-User-ID": str(user_id)}
    return await gateway.forward_request("report", "POST", "/execute",
                                       headers=headers, use_cache=False)

@app.get("/api/report/latest")
async def report_latest():
    return await gateway.forward_request("report", "GET", "/latest")

@app.get("/api/report/history")
async def report_history():
    return await gateway.forward_request("report", "GET", "/history")

# === 플로우 분석 서비스 라우팅 ===
@app.get("/api/flow/health")
async def flow_health():
    return await gateway.forward_request("flow_analysis", "GET", "/health")

@app.post("/api/flow/check-schedule")
async def flow_check_schedule():
    return await gateway.forward_request("flow_analysis", "POST", "/check-schedule", use_cache=False)

@app.post("/api/flow/execute")
async def flow_execute(request: Request):
    # user_id 추출 (Header 또는 Query Param에서)
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id", "1")
    headers = {"X-User-ID": str(user_id)}
    return await gateway.forward_request("flow_analysis", "POST", "/execute",
                                       headers=headers, use_cache=False)

@app.get("/api/flow/analysis/{stock_code}")
async def flow_analysis_result(stock_code: str):
    return await gateway.forward_request("flow_analysis", "GET", f"/analysis/{stock_code}")

# === 중앙 집중식 사용자 설정 관리 ===
@app.get("/api/user/health")
async def user_health():
    """사용자 서비스 헬스체크"""
    return {"status": "healthy", "service": "User Config Manager", "timestamp": datetime.now().isoformat()}

@app.post("/users/profile")
async def create_user_profile(request: Request):
    """사용자 프로필 생성 (User Service로 프록시)"""
    try:
        data = await request.json()
        return await gateway.forward_request("user", "POST", "/users/profile", data=data, use_cache=False)
    except Exception as e:
        logger.error(f"❌ 사용자 프로필 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"프로필 생성 실패: {str(e)}")

@app.get("/users/{user_id}/config")
async def get_user_comprehensive_config(user_id: str):
    """사용자 종합 설정 조회 (서비스 개인화용 - User Service로 프록시)"""
    try:
        return await gateway.forward_request("user", "GET", f"/users/{user_id}/config", use_cache=True)
    except Exception as e:
        logger.error(f"❌ 사용자 종합 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 설정 조회 실패: {str(e)}")

@app.get("/api/user/config/{user_id}")
async def get_user_config(user_id: str):
    """사용자 전체 설정 조회 (중앙 집중식) - user_id 또는 phone_number 지원"""
    try:
        # phone_number 형식인지 확인 (010으로 시작하는 11자리 숫자)
        if user_id.startswith('010') and len(user_id) == 11 and user_id.isdigit():
            # phone_number로 user_id 찾기
            actual_user_id = await _get_user_id_by_phone(user_id)
            if actual_user_id:
                config = await user_config_manager.get_user_config(actual_user_id)
            else:
                # 해당 phone_number의 사용자가 없으면 기본값 반환
                config = user_config_manager._get_default_config()
        else:
            # 기존 user_id로 조회
            config = await user_config_manager.get_user_config(user_id)
        
        return {
            "success": True,
            "data": config,
            "message": f"사용자 설정 조회 완료: {user_id}"
        }
    except Exception as e:
        logger.error(f"❌ 사용자 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 설정 조회 실패: {str(e)}")

async def _get_user_id_by_phone(phone_number: str) -> Optional[int]:
    """전화번호로 user_id 조회"""
    try:
        from shared.database.mysql_client import MySQLClient
        mysql_client = MySQLClient()
        
        query = "SELECT user_id FROM user_profiles WHERE phone_number = %s"
        result = await mysql_client.execute_query_async(query, (phone_number,), fetch=True)
        
        if result:
            return result[0]["user_id"]
        return None
    except Exception as e:
        logger.error(f"❌ 전화번호로 user_id 조회 실패: {e}")
        return None

@app.post("/api/user/config/{user_id}")
async def update_user_config_centralized(user_id: str, request: Request):
    """사용자 전체 설정 업데이트 (중앙 집중식)"""
    try:
        data = await request.json()
        success = await user_config_manager.update_user_config(user_id, data)
        
        if success:
            return {
                "success": True,
                "message": f"사용자 설정 업데이트 완료: {user_id}",
                "updated_fields": list(data.keys())
            }
        else:
            raise HTTPException(status_code=500, detail="사용자 설정 업데이트에 실패했습니다")
            
    except Exception as e:
        logger.error(f"❌ 사용자 설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 설정 업데이트 실패: {str(e)}")

@app.get("/api/user/stocks/{user_id}")
async def get_user_stocks(user_id: str):
    """사용자 종목 설정 조회"""
    try:
        stocks = await user_config_manager.get_user_stocks(user_id)
        return {
            "success": True,
            "data": stocks,
            "message": f"사용자 종목 조회 완료: {user_id} ({len(stocks)}개 종목)"
        }
    except Exception as e:
        logger.error(f"❌ 사용자 종목 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 종목 조회 실패: {str(e)}")

@app.post("/api/user/stocks/{user_id}")
async def update_user_stocks(user_id: str, request: Request):
    """사용자 종목 설정 업데이트"""
    try:
        data = await request.json()
        stocks = data.get("stocks", [])
        
        success = await user_config_manager.update_user_stocks(user_id, stocks)
        
        if success:
            return {
                "success": True,
                "message": f"사용자 종목 설정 완료: {user_id} ({len(stocks)}개 종목)"
            }
        else:
            raise HTTPException(status_code=500, detail="사용자 종목 설정에 실패했습니다")
            
    except Exception as e:
        logger.error(f"❌ 사용자 종목 설정 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 종목 설정 실패: {str(e)}")

@app.get("/api/user/model/{user_id}")
async def get_user_model(user_id: str):
    """사용자 모델 타입 조회"""
    try:
        model_type = await user_config_manager.get_user_model(user_id)
        return {
            "success": True,
            "data": {"model_type": model_type},
            "message": f"사용자 모델 조회 완료: {user_id} -> {model_type}"
        }
    except Exception as e:
        logger.error(f"❌ 사용자 모델 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 모델 조회 실패: {str(e)}")

@app.post("/api/user/model/{user_id}")
async def set_user_model(user_id: str, request: Request):
    """사용자 모델 타입 설정"""
    try:
        data = await request.json()
        model_type = data.get("model_type")
        
        if not model_type:
            raise HTTPException(status_code=400, detail="model_type이 필요합니다")
        
        success = await user_config_manager.set_user_model(user_id, model_type)
        
        if success:
            return {
                "success": True,
                "message": f"사용자 모델 설정 완료: {user_id} -> {model_type}"
            }
        else:
            raise HTTPException(status_code=500, detail="사용자 모델 설정에 실패했습니다")
            
    except Exception as e:
        logger.error(f"❌ 사용자 모델 설정 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 모델 설정 실패: {str(e)}")

@app.get("/api/user/thresholds/{user_id}")
async def get_user_thresholds(user_id: str):
    """사용자 임계값 설정 조회"""
    try:
        thresholds = await user_config_manager.get_user_thresholds(user_id)
        return {
            "success": True,
            "data": thresholds,
            "message": f"사용자 임계값 조회 완료: {user_id}"
        }
    except Exception as e:
        logger.error(f"❌ 사용자 임계값 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 임계값 조회 실패: {str(e)}")

@app.post("/api/user/thresholds/{user_id}")
async def update_user_thresholds(user_id: str, request: Request):
    """사용자 임계값 설정 업데이트"""
    try:
        data = await request.json()
        
        success = await user_config_manager.update_user_thresholds(user_id, data)
        
        if success:
            return {
                "success": True,
                "message": f"사용자 임계값 설정 완료: {user_id}",
                "updated_fields": list(data.keys())
            }
        else:
            raise HTTPException(status_code=500, detail="사용자 임계값 설정에 실패했습니다")
            
    except Exception as e:
        logger.error(f"❌ 사용자 임계값 설정 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 임계값 설정 실패: {str(e)}")

# === 사용자 원하는 서비스 관리 ===
@app.post("/api/user/wanted-services/{user_id}")
async def create_user_wanted_services(user_id: str, request: Request):
    """사용자 원하는 서비스 설정 생성"""
    try:
        data = await request.json()
        return await gateway.forward_request("user", "POST", f"/users/{user_id}/wanted-services", data=data, use_cache=False)
    except Exception as e:
        logger.error(f"❌ 사용자 원하는 서비스 설정 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서비스 설정 생성 실패: {str(e)}")

@app.get("/api/user/wanted-services/{user_id}")
async def get_user_wanted_services(user_id: str):
    """사용자 원하는 서비스 설정 조회"""
    try:
        return await gateway.forward_request("user", "GET", f"/users/{user_id}/wanted-services", use_cache=True, cache_ttl=300)
    except Exception as e:
        logger.error(f"❌ 사용자 원하는 서비스 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서비스 설정 조회 실패: {str(e)}")

@app.put("/api/user/wanted-services/{user_id}")
async def update_user_wanted_services(user_id: str, request: Request):
    """사용자 원하는 서비스 설정 수정"""
    try:
        data = await request.json()
        result = await gateway.forward_request("user", "PUT", f"/users/{user_id}/wanted-services", data=data, use_cache=False)
        
        # 캐시 무효화
        cache_key = f"user_wanted_services_{user_id}"
        if hasattr(gateway, 'cache') and gateway.cache:
            gateway.cache.pop(cache_key, None)
        
        return result
    except Exception as e:
        logger.error(f"❌ 사용자 원하는 서비스 설정 수정 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서비스 설정 수정 실패: {str(e)}")

# === 서비스 활성화 관리 ===
@app.post("/api/services/activate")
async def activate_selected_services(request: Request):
    """선택된 서비스들 활성화"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        services = data.get('services', [])
        
        if not user_id or not services:
            raise HTTPException(status_code=400, detail="user_id와 services가 필요합니다")
        
        # 서비스 매니저를 통해 서비스 활성화
        from pathlib import Path
        import subprocess
        import sys
        
        service_manager_path = Path(__file__).parent.parent.parent / "service_manager.py"
        service_list = ','.join(services)
        
        # 백그라운드에서 서비스 시작
        process = subprocess.Popen([
            sys.executable, str(service_manager_path), 
            "start-services", service_list
        ], cwd=str(service_manager_path.parent))
        
        return {
            "success": True,
            "message": f"서비스 활성화 시작: {services}",
            "data": {
                "user_id": user_id,
                "services": services,
                "process_id": process.pid
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 서비스 활성화 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서비스 활성화 실패: {str(e)}")

@app.get("/api/services/status")
async def get_services_status():
    """모든 서비스 상태 조회"""
    try:
        status = service_manager.get_service_status()
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "services": status
        }
    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@app.post("/api/services/start-core")
async def start_core_services():
    """핵심 서비스들(user_service, api_gateway) 시작"""
    try:
        from pathlib import Path  
        import subprocess
        import json
        
        service_manager_path = Path(__file__).parent.parent.parent / "service_manager.py"
        
        # 핵심 서비스 시작
        result = subprocess.run([
            sys.executable, str(service_manager_path), "start-core"
        ], cwd=str(service_manager_path.parent), capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "핵심 서비스 시작 완료",
                "data": {"stdout": result.stdout, "stderr": result.stderr}
            }
        else:
            raise Exception(f"핵심 서비스 시작 실패: {result.stderr}")
        
    except subprocess.TimeoutExpired:
        logger.error("❌ 핵심 서비스 시작 시간 초과")
        return {
            "success": False,
            "message": "서비스 시작 시간이 초과되었습니다",
            "data": {}
        }
    except Exception as e:
        logger.error(f"❌ 핵심 서비스 시작 실패: {e}")
        return {
            "success": False,
            "message": f"핵심 서비스 시작 실패: {str(e)}",
            "data": {}
        }

# === 기존 User Service 라우팅 (백업용) ===
@app.put("/api/user/config/{user_id}")
async def update_user_config_legacy(user_id: str, request: Request):
    """기존 사용자 서비스 라우팅 (백업용)"""
    data = await request.json()
    return await gateway.forward_request("user", "PUT", f"/config/{user_id}", data=data, use_cache=False)

@app.delete("/api/user/stocks/{user_id}/{stock_code}")
async def remove_user_stock(user_id: str, stock_code: str):
    return await gateway.forward_request("user", "DELETE", f"/stocks/{user_id}/{stock_code}", use_cache=False)

# === 오케스트레이터 라우팅 ===
@app.get("/api/orchestrator/health")
async def orchestrator_health():
    return await gateway.forward_request("orchestrator", "GET", "/health")

@app.get("/api/orchestrator/services")
async def orchestrator_services():
    return await gateway.forward_request("orchestrator", "GET", "/services")

@app.post("/api/orchestrator/start/{service_name}")
async def start_service(service_name: str):
    return await gateway.forward_request("orchestrator", "POST", f"/start/{service_name}", use_cache=False)

@app.post("/api/orchestrator/stop/{service_name}")
async def stop_service(service_name: str):
    return await gateway.forward_request("orchestrator", "POST", f"/stop/{service_name}", use_cache=False)

@app.post("/api/orchestrator/restart/{service_name}")
async def restart_service(service_name: str):
    return await gateway.forward_request("orchestrator", "POST", f"/restart/{service_name}", use_cache=False)

@app.post("/api/orchestrator/start-all")
async def start_all_services():
    return await gateway.forward_request("orchestrator", "POST", "/start-all", use_cache=False)

@app.post("/api/orchestrator/stop-all")
async def stop_all_services():
    return await gateway.forward_request("orchestrator", "POST", "/stop-all", use_cache=False)

# === 고급 기능 엔드포인트 ===

@app.post("/cache/clear")
async def clear_cache():
    """캐시 수동 클리어"""
    try:
        if gateway.cache_manager.redis:
            await gateway.cache_manager.redis.flushall()
        else:
            gateway.cache_manager.local_cache.clear()

        logger.info("캐시 수동 클리어 완료")
        return {"message": "Cache cleared successfully", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"캐시 클리어 실패: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.post("/cache/warm-up")
async def warm_up_cache():
    """캐시 웜업 - 자주 사용되는 엔드포인트 미리 로딩"""
    warm_up_endpoints = [
        ("news", "GET", "/health"),
        ("disclosure", "GET", "/health"),
        ("chart", "GET", "/health"),
        ("report", "GET", "/health"),
        ("flow_analysis", "GET", "/health"),
        ("user", "GET", "/health"),
        ("orchestrator", "GET", "/health")
    ]

    warmed_up = 0
    for service, method, path in warm_up_endpoints:
        try:
            await gateway.forward_request(service, method, path, use_cache=True)
            warmed_up += 1
        except Exception as e:
            logger.warning(f"캐시 웜업 실패: {service}{path} - {e}")

    return {
        "message": f"Cache warm-up completed: {warmed_up}/{len(warm_up_endpoints)} endpoints",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/performance/stats")
async def get_performance_stats():
    """성능 통계 정보"""

    # 메모리 사용량 (가능한 경우)
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
    except ImportError:
        memory_info = None
        cpu_percent = None

    # 연결 풀 상태
    connection_stats = {}
    for service_name, session in gateway.session_pool.items():
        if hasattr(session, '_connector'):
            connector = session._connector
            connection_stats[service_name] = {
                "total_connections": len(connector._conns),
                "available_connections": connector.limit,
                "limit_per_host": connector.limit_per_host
            }

    stats = {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - gateway.config.get("start_time", time.time()),
        "connection_pools": connection_stats,
        "services_health": {
            name: status.value for name, status in gateway.service_health.items()
        }
    }

    if memory_info:
        stats["system"] = {
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "cpu_percent": cpu_percent
        }

    return stats

@app.post("/circuit-breaker/{service_name}/reset")
async def reset_circuit_breaker(service_name: str):
    """Circuit Breaker 수동 리셋"""
    if service_name not in gateway.services:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")

    try:
        service_config = gateway.services[service_name]
        service_config.circuit_breaker.reset()

        logger.info(f"Circuit Breaker 리셋: {service_name}")

        return {
            "message": f"Circuit breaker reset for {service_name}",
            "service": service_name,
            "state": service_config.circuit_breaker.current_state,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Circuit Breaker 리셋 실패: {service_name} - {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breaker")

@app.get("/circuit-breaker/status")
async def get_circuit_breaker_status():
    """모든 서비스의 Circuit Breaker 상태"""
    status = {}

    for service_name, service_config in gateway.services.items():
        cb = service_config.circuit_breaker
        status[service_name] = {
            "state": cb.current_state,
            "fail_counter": cb.fail_counter,
            "success_counter": cb.success_counter,
            "last_failure": cb.last_failure.isoformat() if cb.last_failure else None,
            "next_attempt": (cb.last_failure + timedelta(seconds=cb.reset_timeout)).isoformat()
                          if cb.last_failure and cb.current_state == "open" else None
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "circuit_breakers": status
    }

@app.post("/services/{service_name}/toggle")
async def toggle_service(service_name: str):
    """서비스 활성화/비활성화 토글"""
    if service_name not in gateway.services:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")

    service_config = gateway.services[service_name]
    service_config.enabled = not service_config.enabled

    status_str = "enabled" if service_config.enabled else "disabled"
    logger.info(f"서비스 상태 변경: {service_name} - {status_str}")

    return {
        "message": f"Service {service_name} {status_str}",
        "service": service_name,
        "enabled": service_config.enabled,
        "timestamp": datetime.now().isoformat()
    }

# === 배치 작업 및 유틸리티 ===

@app.post("/maintenance/cleanup")
async def maintenance_cleanup():
    """유지보수 - 리소스 정리"""
    cleaned_items = []

    try:
        # 로컬 캐시 정리 (만료된 항목)
        if not gateway.cache_manager.redis:
            current_time = time.time()
            expired_keys = [
                key for key, value in gateway.cache_manager.local_cache.items()
                if value['expires'] < current_time
            ]

            for key in expired_keys:
                del gateway.cache_manager.local_cache[key]

            cleaned_items.append(f"Expired cache entries: {len(expired_keys)}")

        # 연결 풀 정리
        for service_name, session in gateway.session_pool.items():
            if hasattr(session, '_connector'):
                # 유휴 연결 정리 (aiohttp에서 자동 처리되지만 명시적으로 호출)
                await session._connector._cleanup_closed()

        cleaned_items.append("Connection pools cleaned")

        logger.info(f"유지보수 정리 완료: {cleaned_items}")

        return {
            "message": "Maintenance cleanup completed",
            "cleaned_items": cleaned_items,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"유지보수 정리 실패: {e}")
        raise HTTPException(status_code=500, detail="Maintenance cleanup failed")

@app.get("/debug/config")
async def get_debug_config():
    """디버그 - 현재 설정 정보 (민감한 정보 제외)"""
    debug_config = {}

    for service_name, service_config in gateway.services.items():
        debug_config[service_name] = {
            "name": service_config.name,
            "instances": service_config.instances,
            "base_path": service_config.base_path,
            "enabled": service_config.enabled,
            "timeout": service_config.timeout,
            "retry_count": service_config.retry_count,
            "health_check_interval": service_config.health_check_interval
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "services": debug_config,
        "gateway_version": "2.0.0",
        "cache_type": "redis" if gateway.cache_manager.redis else "local"
    }

# === 에러 핸들러 ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 핸들러"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path
            }
        }
    )

# === 메인 실행 함수 ===

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="API Gateway - Optimized")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8005, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Log level")

    args = parser.parse_args()

    # 시작 시간 저장
    gateway.config["start_time"] = time.time()

    logger.info(
        "API Gateway 시작 준비",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level
    )

    try:
        uvicorn.run(
            app,  # 직접 앱 객체 전달
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("API Gateway 중단 요청")
    except Exception as e:
        logger.error(f"API Gateway 실행 실패: {e}")
        raise

# ==========================================
# 🚀 서비스 관리 API 엔드포인트들
# ==========================================

@app.post("/api/services/start-selected")
async def start_selected_services(request_data: Dict[str, Any]):
    """선택된 서비스들 시작"""
    try:
        service_list = request_data.get("services", [])
        user_id = request_data.get("user_id", None)  # 🔥 사용자 ID 받기
        
        logger.info(f"Starting selected services: {service_list} for user: {user_id}")
        
        success = service_manager.start_selected_services(service_list, user_id)
        
        if success:
            status = service_manager.get_service_status()
            return {
                "success": True,
                "message": f"Selected services started: {service_list} for user: {user_id}",
                "services": status
            }
        else:
            return {
                "success": False,
                "message": "Failed to start some services. Check logs for details.",
                "services": service_manager.get_service_status()
            }
    except Exception as e:
        logger.error(f"❌ Error starting selected services: {e}")
        raise HTTPException(status_code=500, detail=f"Service start failed: {str(e)}")

@app.post("/api/services/start-core")
async def start_core_services():
    """핵심 서비스들 시작 (API Gateway, User Service)"""
    try:
        logger.info("Starting core services...")
        success = service_manager.start_core_services()
        
        if success:
            status = service_manager.get_service_status()
            return {
                "success": True,
                "message": "Core services started successfully",
                "services": status
            }
        else:
            return {
                "success": False,
                "message": "Failed to start core services",
                "services": service_manager.get_service_status()
            }
    except Exception as e:
        logger.error(f"Failed to start core services: {e}")
        raise HTTPException(status_code=500, detail=f"Core service start failed: {str(e)}")

@app.post("/api/services/{service_name}/start")
async def start_single_service(service_name: str):
    """개별 서비스 시작"""
    try:
        logger.info(f"Starting service: {service_name}")
        success = service_manager.start_service(service_name)
        
        if success:
            return {
                "success": True,
                "message": f"Service {service_name} started successfully",
                "service": service_manager.get_service_status().get(service_name, {})
            }
        else:
            return {
                "success": False,
                "message": f"Failed to start service {service_name}",
                "service": service_manager.get_service_status().get(service_name, {})
            }
    except Exception as e:
        logger.error(f"Failed to start service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Service start failed: {str(e)}")

@app.post("/api/services/{service_name}/stop")
async def stop_single_service(service_name: str):
    """개별 서비스 중지"""
    try:
        logger.info(f"Stopping service: {service_name}")
        success = service_manager.stop_service(service_name)
        
        if success:
            return {
                "success": True,
                "message": f"Service {service_name} stopped successfully",
                "service": service_manager.get_service_status().get(service_name, {})
            }
        else:
            return {
                "success": False,
                "message": f"Failed to stop service {service_name}",
                "service": service_manager.get_service_status().get(service_name, {})
            }
    except Exception as e:
        logger.error(f"Failed to stop service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Service stop failed: {str(e)}")

@app.get("/api/services/{service_name}/status")
async def get_single_service_status(service_name: str):
    """개별 서비스 상태 조회"""
    try:
        all_status = service_manager.get_service_status()
        service_status = all_status.get(service_name)
        
        if service_status is None:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        
        return {
            "success": True,
            "service_name": service_name,
            "status": service_status,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

if __name__ == "__main__":
    main()