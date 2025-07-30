"""
Google Gemini AI Client for stock analysis service
gemini_api_client.py의 subprocess 방식을 사용하여 순수 API 호출만 담당
"""

import subprocess
import json
import re
import logging
import asyncio
import os
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class GeminiClient:
    """Google Gemini AI 클라이언트 - 순수 API 호출만 담당"""
    
    def __init__(self, gemini_cmd_path: Optional[str] = None):
        """
        Gemini CLI 클라이언트 초기화
        
        Args:
            gemini_cmd_path: Gemini CLI 실행 파일 경로
        """
        # OS별 기본 경로 설정
        if gemini_cmd_path:
            self.gemini_cmd_path = gemini_cmd_path
        elif os.name == 'nt':  # Windows
            self.gemini_cmd_path = "C:/Users/User/AppData/Roaming/npm/gemini.cmd"
        else:  # macOS/Linux
            self.gemini_cmd_path = "gemini"
        
        # API 키 설정 (Gemini CLI는 API 키를 자체적으로 관리)
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        
        logger.debug(f"🔧 Gemini CLI 경로: {self.gemini_cmd_path}")
        logger.debug(f"🔧 Gemini API 키 존재: {bool(self.api_key)}")
    
    def is_available(self) -> bool:
        """Gemini CLI 사용 가능 여부 확인"""
        try:
            result = subprocess.run(
                [self.gemini_cmd_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False
    
    def get_client_info(self) -> Dict[str, Any]:
        """클라이언트 정보 반환"""
        return {
            "client_type": "GeminiClient",
            "gemini_cmd_path": self.gemini_cmd_path,
            "available": self.is_available()
        }
    
    def _parse_response(self, response_text: str) -> str:
        """Gemini 응답에서 JSON 추출 및 파싱"""
        try:
            # JSON 객체 추출
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                # JSON 유효성 검증
                json.loads(json_str)
                return json_str
            else:
                # JSON이 없으면 원본 텍스트 반환
                return response_text.strip()
                
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 원본 텍스트 반환
            logger.warning("⚠️ JSON 파싱 실패, 원본 텍스트 반환")
            return response_text.strip()
    
    async def generate_response(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Gemini API를 통한 텍스트 생성 (비동기)
        
        Args:
            prompt: 입력 프롬프트
            **kwargs: 추가 파라미터 (model 등)
            
        Returns:
            생성된 텍스트 또는 None (실패 시)
        """
        try:
            if not self.is_available():
                logger.error("❌ Gemini CLI를 사용할 수 없습니다")
                return None
            
            # 모델 설정 (기본값: gemini-2.5-flash)
            model = kwargs.get("model", "gemini-2.5-flash")
            
            # 명령어 구성
            command = [self.gemini_cmd_path, "--model", model]
            
            logger.debug(f"🚀 Gemini CLI 호출: {' '.join(command)}")
            
            # 비동기 subprocess 실행
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    command,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30
                )
            )
            
            # 실행 결과 확인
            if result.returncode != 0:
                logger.error(f"❌ Gemini CLI 실행 실패 (Exit Code: {result.returncode})")
                logger.error(f"stderr: {result.stderr}")
                return None
            
            # 응답 파싱 및 반환
            response = self._parse_response(result.stdout)
            logger.debug("✅ Gemini API 호출 성공")
            return response
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Gemini API 호출 타임아웃")
            return None
        except Exception as e:
            logger.error(f"❌ Gemini API 호출 중 오류: {e}")
            return None
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        텍스트 생성 (호환성을 위한 메서드)
        
        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수 (Gemini CLI에서는 사용되지 않음)
            
        Returns:
            생성된 텍스트
        """
        try:
            response = await self.generate_response(prompt)
            return response if response else "텍스트 생성 실패"
        except Exception as e:
            logger.error(f"❌ 텍스트 생성 실패: {e}")
            return "텍스트 생성 실패"
    
    async def close(self):
        """리소스 정리 (subprocess 방식이므로 특별한 정리 불필요)"""
        logger.debug("🔧 Gemini 클라이언트 정리 완료")
        pass


# 호환성을 위한 기본 인스턴스
gemini_client = GeminiClient()