"""
사용자 설정 API Pydantic 모델
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum

class ModelType(str, Enum):
    """사용 가능한 모델 타입"""
    HYPERCLOVA = "hyperclova"
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    GROK = "grok"
    GEMINI = "gemini"

class UserProfileCreate(BaseModel):
    """사용자 프로필 생성 모델"""
    username: str = Field(..., min_length=1, max_length=100, description="사용자명")
    phone_number: str = Field(..., min_length=10, max_length=20, description="전화번호")
    news_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="뉴스 유사도 임계값")
    news_impact_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="뉴스 영향도 임계값")
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """전화번호 형식 검증"""
        if not v.replace('-', '').replace(' ', '').isdigit():
            raise ValueError('전화번호는 숫자만 포함해야 합니다')
        return v

class UserProfileUpdate(BaseModel):
    """사용자 프로필 수정 모델"""
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    news_similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    news_impact_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None:
            if not v.replace('-', '').replace(' ', '').isdigit():
                raise ValueError('전화번호는 숫자만 포함해야 합니다')
        return v

class UserStockCreate(BaseModel):
    """사용자 종목 추가 모델"""
    stock_code: str = Field(..., min_length=6, max_length=6, description="종목코드")
    stock_name: str = Field(..., min_length=1, max_length=100, description="종목명")
    enabled: bool = Field(default=True, description="활성화 여부")
    
    @validator('stock_code')
    def validate_stock_code(cls, v):
        """종목코드 형식 검증"""
        if not v.isdigit():
            raise ValueError('종목코드는 숫자만 포함해야 합니다')
        return v

class UserStockUpdate(BaseModel):
    """사용자 종목 수정 모델"""
    stock_name: Optional[str] = Field(None, min_length=1, max_length=100)
    enabled: Optional[bool] = None

class UserModelCreate(BaseModel):
    """사용자 모델 설정 모델"""
    model_type: ModelType = Field(default=ModelType.HYPERCLOVA, description="선택할 모델 타입")

class UserConfigResponse(BaseModel):
    """사용자 설정 응답 모델"""
    user_id: str
    username: str
    phone_number: str
    news_similarity_threshold: float
    news_impact_threshold: float
    stocks: List[dict]
    model_type: str
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "username": "test_user",
                "phone_number": "01012345678",
                "news_similarity_threshold": 0.7,
                "news_impact_threshold": 0.8,
                "stocks": [
                    {"stock_code": "005930", "stock_name": "삼성전자", "enabled": True},
                    {"stock_code": "000660", "stock_name": "SK하이닉스", "enabled": True}
                ],
                "model_type": "hyperclova"
            }
        }

class UserWantedServiceCreate(BaseModel):
    """사용자 원하는 서비스 설정 모델"""
    news_service: bool = Field(default=False, description="뉴스 서비스 활성화")
    disclosure_service: bool = Field(default=False, description="공시 서비스 활성화")
    report_service: bool = Field(default=False, description="리포트 서비스 활성화")
    chart_service: bool = Field(default=False, description="차트 서비스 활성화")
    flow_service: bool = Field(default=False, description="자금흐름 서비스 활성화")

class UserWantedServiceUpdate(BaseModel):
    """사용자 원하는 서비스 수정 모델"""
    news_service: Optional[bool] = None
    disclosure_service: Optional[bool] = None
    report_service: Optional[bool] = None
    chart_service: Optional[bool] = None
    flow_service: Optional[bool] = None

class UserWantedServiceResponse(BaseModel):
    """사용자 원하는 서비스 응답 모델"""
    user_id: str
    phone_number: str
    news_service: bool
    disclosure_service: bool
    report_service: bool
    chart_service: bool
    flow_service: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "01012345678",
                "phone_number": "01012345678",
                "news_service": True,
                "disclosure_service": False,
                "report_service": True,
                "chart_service": False,
                "flow_service": True,
                "created_at": "2025-01-27T10:00:00",
                "updated_at": "2025-01-27T10:00:00"
            }
        }

class ApiResponse(BaseModel):
    """API 응답 공통 모델"""
    success: bool
    message: str
    data: Optional[dict] = None 