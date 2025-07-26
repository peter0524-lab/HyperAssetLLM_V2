"""
API Gateway 설정 관리
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class ServiceConfig:
    """개별 서비스 설정"""
    name: str
    instances: List[str]
    base_path: str
    enabled: bool = True
    timeout: float = 10.0
    retry_count: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60

@dataclass
class GatewayConfig:
    """API Gateway 메인 설정"""
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8005
    workers: int = 1
    
    # Redis 캐시 설정
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 300  # 5분
    use_local_cache_fallback: bool = True
    
    # 성능 설정
    connection_pool_size: int = 100
    connection_per_host: int = 30
    keepalive_timeout: int = 30
    
    # 모니터링 설정
    enable_prometheus: bool = True
    enable_health_check: bool = True
    health_check_interval: int = 30
    
    # Circuit Breaker 기본 설정
    default_circuit_breaker_threshold: int = 5
    default_circuit_breaker_timeout: int = 60
    
    # 로깅 설정
    log_level: str = "INFO"
    structured_logging: bool = True
    
    # CORS 설정
    cors_origins: List[str] = None
    cors_allow_credentials: bool = True
    
    def __post_init__(self):
        """환경변수에서 설정 오버라이드"""
        # 환경변수 우선 적용
        self.host = os.getenv("GATEWAY_HOST", self.host)
        self.port = int(os.getenv("GATEWAY_PORT", str(self.port)))
        self.redis_url = os.getenv("REDIS_URL", self.redis_url)
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        
        # CORS origins 설정
        if self.cors_origins is None:
            cors_env = os.getenv("CORS_ORIGINS", "*")
            self.cors_origins = [origin.strip() for origin in cors_env.split(",")]

# 서비스별 설정
SERVICES_CONFIG = {
    "news": ServiceConfig(
        name="News Service",
        instances=["http://localhost:8001"],
        base_path="/api/news",
        timeout=15.0,
        circuit_breaker_threshold=5
    ),
    "disclosure": ServiceConfig(
        name="Disclosure Service",
        instances=["http://localhost:8002"],
        base_path="/api/disclosure",
        timeout=20.0,
        circuit_breaker_threshold=5
    ),
    "chart": ServiceConfig(
        name="Chart Service",
        instances=["http://localhost:8003"],
        base_path="/api/chart",
        timeout=10.0,
        circuit_breaker_threshold=3
    ),
    "report": ServiceConfig(
        name="Report Service",
        instances=["http://localhost:8004"],
        base_path="/api/report",
        timeout=30.0,
        circuit_breaker_threshold=5
    ),
    "flow_analysis": ServiceConfig(
        name="Flow Analysis Service",
        instances=["http://localhost:8010"],
        base_path="/api/flow",
        timeout=15.0,
        circuit_breaker_threshold=5
    ),
    "user": ServiceConfig(
        name="User Service",
        instances=["http://localhost:8006"],
        base_path="/api/user",
        timeout=5.0,
        circuit_breaker_threshold=3
    ),
    "orchestrator": ServiceConfig(
        name="Orchestrator Service",
        instances=["http://localhost:8000"],
        base_path="/api/orchestrator",
        timeout=10.0,
        circuit_breaker_threshold=3
    ),
    "issue_scheduler": ServiceConfig(
        name="Issue Scheduler Service",
        instances=["http://localhost:8007"],
        base_path="/api/issue",
        timeout=15.0,
        circuit_breaker_threshold=5
    ),
    "business_report": ServiceConfig(
        name="Business Report Service",
        instances=["http://localhost:8008"],
        base_path="/api/business",
        timeout=30.0,
        circuit_breaker_threshold=5
    ),
    "analysis": ServiceConfig(
        name="Analysis Service",
        instances=["http://localhost:8009"],
        base_path="/api/analysis",
        timeout=20.0,
        circuit_breaker_threshold=5
    )
}

def get_gateway_config() -> GatewayConfig:
    """Gateway 설정 인스턴스 반환"""
    return GatewayConfig()

def get_service_config(service_name: str) -> Optional[ServiceConfig]:
    """특정 서비스 설정 반환"""
    return SERVICES_CONFIG.get(service_name)

def get_all_services_config() -> Dict[str, ServiceConfig]:
    """모든 서비스 설정 반환"""
    return SERVICES_CONFIG.copy()

# 개발/운영 환경별 설정
class Environment:
    """환경별 설정"""
    
    @staticmethod
    def is_development() -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    @staticmethod
    def is_production() -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @staticmethod
    def get_environment() -> str:
        return os.getenv("ENVIRONMENT", "development").lower()

# 환경별 설정 오버라이드
if Environment.is_production():
    # 운영환경에서는 더 엄격한 설정
    for service_config in SERVICES_CONFIG.values():
        service_config.circuit_breaker_threshold = 3
        service_config.timeout = min(service_config.timeout, 15.0)
elif Environment.is_development():
    # 개발환경에서는 더 관대한 설정
    for service_config in SERVICES_CONFIG.values():
        service_config.circuit_breaker_threshold = 10
        service_config.timeout = service_config.timeout * 1.5 