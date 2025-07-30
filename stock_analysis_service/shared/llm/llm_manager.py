"""
LLM Manager - 통합 LLM 클라이언트 관리자
사용자가 선택한 모델에 따라 적절한 클라이언트를 반환
"""
import os
import logging
from typing import Optional, Dict, Any
from .hyperclova_client import HyperCLOVAClient
from .gemini_client import GeminiClient
from .gemini_api_client import GeminiAPIClient
from .chat_gpt import OpenAIClient
from .claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class LLMManager:
    """통합 LLM 관리자 - 사용자 모델 선택에 따라 적절한 클라이언트 반환"""
    
    def __init__(self):
        """LLM 클라이언트들 초기화"""
        self.clients: Dict[str, Any] = {}
        self._initialize_clients()
        self.logger = logging.getLogger(__name__)
    
    def _initialize_clients(self):
        """사용 가능한 LLM 클라이언트들 초기화"""
        try:
            # 각 클라이언트가 자체적으로 API 키를 가져옴
            self.clients["hyperclova"] = HyperCLOVAClient()
            self.clients["gemini"] = GeminiAPIClient()  # API 방식으로 변경
            self.clients["openai"] = OpenAIClient()
            self.clients["claude"] = ClaudeClient()
            
            # 추후 구현 예정
            # self.clients["grok"] = GrokClient()
            
        except Exception as e:
            self.logger.error(f"❌ LLM 클라이언트 초기화 실패: {e}")
            # 최소한 HyperCLOVA는 사용 가능하도록 설정
            if "hyperclova" not in self.clients:
                self.clients["hyperclova"] = HyperCLOVAClient()
    
    async def get_client_for_user(self, user_id) -> Any:
        """사용자가 선택한 모델의 클라이언트 반환
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            선택된 모델의 LLM 클라이언트
        """
        try:
            # MySQL에서 사용자 모델 조회
            from shared.user_config.user_config_manager import user_config_manager
            user_model = await user_config_manager.get_user_model(user_id)
            
            # 선택된 모델의 클라이언트 반환
            if user_model in self.clients:
                client = self.clients[user_model]
                self.logger.debug(f"📱 사용자 {user_id}의 선택 모델: {user_model}")
                return client
            else:
                # 지원하지 않는 모델인 경우 HyperCLOVA로 대체
                self.logger.warning(f"⚠️ 지원하지 않는 모델 {user_model}, HyperCLOVA로 대체")
                return self.clients["hyperclova"]
                
        except Exception as e:
            self.logger.error(f"❌ 사용자 모델 조회 실패: {e}, HyperCLOVA로 대체")
            return self.clients["hyperclova"]
    
    async def generate_response(self, user_id, prompt: str, **kwargs) -> Optional[str]:
        """통합 응답 생성 (프롬프트는 서비스에서 전달받음)
        
        Args:
            user_id: 사용자 ID
            prompt: 입력 프롬프트 (서비스에서 생성된 완전한 프롬프트)
            **kwargs: 각 클라이언트별 추가 파라미터
            
        Returns:
            LLM 응답
        """
        try:
            client = await self.get_client_for_user(user_id)
            
            # 클라이언트가 사용 가능한지 확인
            if not client.is_available():
                self.logger.warning(f"⚠️ {client.__class__.__name__} 사용 불가, 기본 클라이언트로 대체")
                client = self.clients["hyperclova"]
            
            # LLM 응답 생성
            response = await client.generate_response(prompt, **kwargs)
            
            self.logger.debug(f"✅ LLM 응답 생성 완료: {client.__class__.__name__}")
            return response
            
        except Exception as e:
            self.logger.error(f"❌ LLM 응답 생성 실패: {e}")
            return None
    
    async def generate_text(self, user_id, prompt: str, max_tokens: int = 1000) -> str:
        """통합 텍스트 생성 (호환성을 위한 메서드)
        
        Args:
            user_id: 사용자 ID
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            
        Returns:
            생성된 텍스트
        """
        try:
            client = await self.get_client_for_user(user_id)
            
            if not client.is_available():
                client = self.clients["hyperclova"]
            
            response = await client.generate_text(prompt, max_tokens)
            return response
            
        except Exception as e:
            self.logger.error(f"❌ 텍스트 생성 실패: {e}")
            return "텍스트 생성 실패"
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """사용 가능한 모델 목록 반환
        
        Returns:
            사용 가능한 모델들의 정보
        """
        available_models = {}
        for model_name, client in self.clients.items():
            available_models[model_name] = {
                "available": client.is_available(),
                "client_info": client.get_client_info()
            }
        return available_models
    
    async def close(self):
        """리소스 정리"""
        for client in self.clients.values():
            if hasattr(client, 'close'):
                try:
                    await client.close()
                except Exception as e:
                    self.logger.error(f"❌ 클라이언트 종료 실패: {e}")


# 전역 인스턴스 생성
llm_manager = LLMManager()


async def get_llm_manager() -> LLMManager:
    """LLM 매니저 인스턴스 반환"""
    return llm_manager 