"""
모니터링 미들웨어
- 요청/응답 메트릭 수집
- 성능 모니터링
- 에러 추적
"""

import time
import uuid
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
REQUEST_COUNT = Counter(
    'api_gateway_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code', 'service']
)

REQUEST_DURATION = Histogram(
    'api_gateway_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint', 'service']
)

ACTIVE_REQUESTS = Gauge(
    'api_gateway_active_requests',
    'Number of active requests'
)

ERROR_COUNT = Counter(
    'api_gateway_errors_total',
    'Total errors',
    ['error_type', 'service']
)

REQUEST_SIZE = Histogram(
    'api_gateway_request_size_bytes',
    'Request size in bytes',
    ['method', 'endpoint']
)

RESPONSE_SIZE = Histogram(
    'api_gateway_response_size_bytes',
    'Response size in bytes',
    ['method', 'endpoint', 'status_code']
)

logger = structlog.get_logger(__name__)

class MonitoringMiddleware(BaseHTTPMiddleware):
    """모니터링 미들웨어"""
    
    def __init__(self, app, enable_detailed_logging: bool = True):
        super().__init__(app)
        self.enable_detailed_logging = enable_detailed_logging
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 및 모니터링"""
        
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # 요청 정보 추출
        method = request.method
        url_path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # 서비스명 추출 (URL 경로에서)
        service_name = self._extract_service_name(url_path)
        
        # 요청 크기 측정
        content_length = request.headers.get("content-length")
        request_size = int(content_length) if content_length else 0
        
        # 활성 요청 수 증가
        ACTIVE_REQUESTS.inc()
        
        # 요청 시작 로깅
        if self.enable_detailed_logging:
            logger.info(
                "request_started",
                request_id=request_id,
                method=method,
                path=url_path,
                client_ip=client_ip,
                user_agent=user_agent,
                service=service_name,
                request_size=request_size
            )
        
        # 요청 크기 메트릭
        if request_size > 0:
            REQUEST_SIZE.labels(method=method, endpoint=url_path).observe(request_size)
        
        # 요청에 ID 추가
        request.state.request_id = request_id
        request.state.start_time = start_time
        request.state.service_name = service_name
        
        try:
            # 다음 미들웨어/라우터 호출
            response = await call_next(request)
            
            # 응답 처리
            return await self._handle_response(
                request, response, start_time, request_id, service_name
            )
            
        except Exception as e:
            # 에러 처리
            return await self._handle_error(
                request, e, start_time, request_id, service_name
            )
        finally:
            # 활성 요청 수 감소
            ACTIVE_REQUESTS.dec()
    
    async def _handle_response(
        self, 
        request: Request, 
        response: Response, 
        start_time: float,
        request_id: str,
        service_name: str
    ) -> Response:
        """정상 응답 처리"""
        
        # 응답 시간 계산
        duration = time.time() - start_time
        
        # 응답 정보
        status_code = response.status_code
        method = request.method
        url_path = request.url.path
        
        # 응답 크기 (가능한 경우)
        response_size = 0
        if hasattr(response, 'body'):
            response_size = len(response.body) if response.body else 0
        
        # 메트릭 업데이트
        REQUEST_COUNT.labels(
            method=method,
            endpoint=url_path,
            status_code=status_code,
            service=service_name
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=url_path,
            service=service_name
        ).observe(duration)
        
        if response_size > 0:
            RESPONSE_SIZE.labels(
                method=method,
                endpoint=url_path,
                status_code=status_code
            ).observe(response_size)
        
        # 응답 완료 로깅
        if self.enable_detailed_logging:
            logger.info(
                "request_completed",
                request_id=request_id,
                method=method,
                path=url_path,
                status_code=status_code,
                duration=duration,
                service=service_name,
                response_size=response_size
            )
        
        # 응답 헤더에 메타데이터 추가
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Service"] = service_name
        
        return response
    
    async def _handle_error(
        self,
        request: Request,
        error: Exception,
        start_time: float,
        request_id: str,
        service_name: str
    ) -> Response:
        """에러 응답 처리"""
        
        duration = time.time() - start_time
        method = request.method
        url_path = request.url.path
        error_type = type(error).__name__
        
        # 에러 메트릭 업데이트
        ERROR_COUNT.labels(
            error_type=error_type,
            service=service_name
        ).inc()
        
        REQUEST_COUNT.labels(
            method=method,
            endpoint=url_path,
            status_code=500,
            service=service_name
        ).inc()
        
        # 에러 로깅
        logger.error(
            "request_error",
            request_id=request_id,
            method=method,
            path=url_path,
            error_type=error_type,
            error_message=str(error),
            duration=duration,
            service=service_name
        )
        
        # 에러 응답 생성
        from fastapi.responses import JSONResponse
        
        error_response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal Server Error",
                    "request_id": request_id,
                    "service": service_name
                }
            }
        )
        
        # 응답 헤더 추가
        error_response.headers["X-Request-ID"] = request_id
        error_response.headers["X-Response-Time"] = f"{duration:.3f}s"
        error_response.headers["X-Service"] = service_name
        
        return error_response
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        # X-Forwarded-For 헤더 확인 (프록시 환경)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 직접 연결
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _extract_service_name(self, url_path: str) -> str:
        """URL 경로에서 서비스명 추출"""
        # /api/{service_name}/... 패턴에서 서비스명 추출
        path_parts = url_path.strip("/").split("/")
        
        if len(path_parts) >= 2 and path_parts[0] == "api":
            return path_parts[1]
        
        # 기본값
        return "gateway" 