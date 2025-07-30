"""
Anthropic Claude AI Client for stock analysis service
"""

import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Anthropic Claude AI 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY", "")
        self.base_url = base_url or "https://api.anthropic.com/v1/messages"
        self.model = model
        self.session = None
        
    async def _get_session(self):
        """HTTP 세션 생성"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def close(self):
        """세션 정리"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def is_available(self) -> bool:
        """API 키 사용 가능 여부 확인"""
        return bool(self.api_key)
    
    def get_client_info(self) -> Dict[str, Any]:
        """클라이언트 정보 반환"""
        return {
            "client_type": "ClaudeClient",
            "has_api_key": bool(self.api_key),
            "base_url": self.base_url,
            "model": self.model
        }
    
    async def generate_response(self, prompt: str, **kwargs) -> Optional[str]:
        """Claude API를 통한 텍스트 생성
        
        Args:
            prompt: 입력 프롬프트
            **kwargs: 추가 파라미터
            
        Returns:
            생성된 텍스트 또는 None (실패 시)
        """
        try:
            if not self.is_available():
                logger.warning("⚠️ Claude API 키가 없습니다.")
                return None
            
            session = await self._get_session()
            
            # Claude API 요청 형식
            payload = {
                "model": kwargs.get("model", self.model),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.3),
                "top_p": kwargs.get("top_p", 0.8),
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            logger.debug(f"🔗 Claude API 호출: {self.base_url}")
            logger.debug(f"🔗 모델: {payload['model']}")
            
            async with session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status == 200:
                    raw_response = await response.json()
                    logger.debug("✅ Claude API 호출 성공")
                    
                    # Claude 응답 파싱
                    if "content" in raw_response and raw_response["content"]:
                        content = raw_response["content"][0]["text"]
                        return content
                    else:
                        logger.warning("⚠️ Claude 응답에 content가 없습니다.")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Claude API 오류 {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Claude API 호출 실패: {e}")
            return None
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        """호환성을 위한 텍스트 생성 메서드"""
        response = await self.generate_response(prompt, max_tokens=max_tokens)
        return response if response else "텍스트 생성 실패"
    
    async def analyze_news_impact(self, news_content: str, stock_name: str) -> Dict:
        """뉴스 영향도 분석"""
        try:
            prompt = f"""
            다음 뉴스를 분석하여 {stock_name} 주식에 미치는 영향을 평가해주세요.
            
            뉴스 내용:
            {news_content}
            
            다음 JSON 형식으로 응답해주세요:
            {{
                "summary": "뉴스 요약",
                "impact_score": 0.5,
                "sentiment": "positive/negative/neutral",
                "sentiment_reason": "감정 분석 근거",
                "keywords": ["키워드1", "키워드2"],
                "expected_impact": "예상 영향",
                "impact_duration": "단기/중기/장기"
            }}
            """
            
            response = await self.generate_response(prompt)
            if response:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    logger.error("❌ Claude 응답 JSON 파싱 실패")
                    return self._default_response("JSON 파싱 실패")
            else:
                return self._default_response("API 호출 실패")
                
        except Exception as e:
            logger.error(f"❌ 뉴스 영향도 분석 실패: {e}")
            return self._default_response(str(e))
    
    def _default_response(self, reason: str) -> Dict:
        """기본 응답 반환"""
        return {
            "summary": f"분석 실패: {reason}",
            "impact_score": 0.0,
            "sentiment": "neutral",
            "sentiment_reason": reason,
            "keywords": [],
            "expected_impact": "분석 불가",
            "impact_duration": "단기",
        }
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 