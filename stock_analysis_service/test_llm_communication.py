"""
LLM 통신 상태 체크 스크립트
HyperCLOVA, ChatGPT, Gemini 3개 모델의 API 통신을 테스트합니다.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 환경 변수 로드
from config.env_local import load_env_vars
load_env_vars()

from shared.llm.hyperclova_client import HyperCLOVAClient
from shared.llm.chat_gpt import OpenAIClient
from shared.llm.gemini_api_client import GeminiAPIClient
from shared.llm.claude_client import ClaudeClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMCommunicationTester:
    """LLM 통신 상태 테스터"""
    
    def __init__(self):
        self.test_prompt = "안녕하세요! 주식 시장에 대해 간단히 설명해주세요."
        self.results = {}
    
    async def test_hyperclova(self):
        """HyperCLOVA 통신 테스트"""
        logger.info("🔍 HyperCLOVA 통신 테스트 시작...")
        
        try:
            client = HyperCLOVAClient()
            
            # 사용 가능 여부 확인
            is_available = client.is_available()
            logger.info(f"📊 HyperCLOVA 사용 가능: {is_available}")
            
            if is_available:
                # API 호출 테스트
                start_time = datetime.now()
                response = await client.generate_text(self.test_prompt, max_tokens=100)
                end_time = datetime.now()
                
                duration = (end_time - start_time).total_seconds()
                
                self.results["hyperclova"] = {
                    "available": True,
                    "response_length": len(response) if response else 0,
                    "duration": duration,
                    "response_preview": response[:100] if response else "None",
                    "success": bool(response and len(response) > 10)
                }
                
                logger.info(f"✅ HyperCLOVA 테스트 완료 - 응답 길이: {len(response)}, 소요시간: {duration:.2f}초")
            else:
                self.results["hyperclova"] = {
                    "available": False,
                    "error": "API 키 없음"
                }
                logger.warning("⚠️ HyperCLOVA API 키가 없습니다.")
                
        except Exception as e:
            logger.error(f"❌ HyperCLOVA 테스트 실패: {e}")
            self.results["hyperclova"] = {
                "available": False,
                "error": str(e)
            }
    
    async def test_chatgpt(self):
        """ChatGPT 통신 테스트"""
        logger.info("🔍 ChatGPT 통신 테스트 시작...")
        
        try:
            client = OpenAIClient()
            
            # 사용 가능 여부 확인
            is_available = client.is_available()
            logger.info(f"📊 ChatGPT 사용 가능: {is_available}")
            
            if is_available:
                # API 호출 테스트
                start_time = datetime.now()
                response = await client.generate_text(self.test_prompt, max_tokens=100)
                end_time = datetime.now()
                
                duration = (end_time - start_time).total_seconds()
                
                self.results["chatgpt"] = {
                    "available": True,
                    "response_length": len(response) if response else 0,
                    "duration": duration,
                    "response_preview": response[:100] if response else "None",
                    "success": bool(response and len(response) > 10)
                }
                
                logger.info(f"✅ ChatGPT 테스트 완료 - 응답 길이: {len(response)}, 소요시간: {duration:.2f}초")
            else:
                self.results["chatgpt"] = {
                    "available": False,
                    "error": "API 키 없음"
                }
                logger.warning("⚠️ ChatGPT API 키가 없습니다.")
                
        except Exception as e:
            logger.error(f"❌ ChatGPT 테스트 실패: {e}")
            self.results["chatgpt"] = {
                "available": False,
                "error": str(e)
            }
    
    async def test_gemini(self):
        """Gemini 통신 테스트"""
        logger.info("🔍 Gemini 통신 테스트 시작...")
        
        try:
            client = GeminiAPIClient()
            
            # 사용 가능 여부 확인
            is_available = client.is_available()
            logger.info(f"📊 Gemini 사용 가능: {is_available}")
            
            if is_available:
                # API 호출 테스트
                start_time = datetime.now()
                response = await client.generate_text(self.test_prompt, max_tokens=100)
                end_time = datetime.now()
                
                duration = (end_time - start_time).total_seconds()
                
                self.results["gemini"] = {
                    "available": True,
                    "response_length": len(response) if response else 0,
                    "duration": duration,
                    "response_preview": response[:100] if response else "None",
                    "success": bool(response and len(response) > 10)
                }
                
                logger.info(f"✅ Gemini 테스트 완료 - 응답 길이: {len(response)}, 소요시간: {duration:.2f}초")
            else:
                self.results["gemini"] = {
                    "available": False,
                    "error": "API 키 없음"
                }
                logger.warning("⚠️ Gemini API 키가 없습니다.")
                
        except Exception as e:
            logger.error(f"❌ Gemini 테스트 실패: {e}")
            self.results["gemini"] = {
                "available": False,
                "error": str(e)
            }
    
    async def test_claude(self):
        """Claude 통신 테스트"""
        logger.info("🔍 Claude 통신 테스트 시작...")
        
        try:
            client = ClaudeClient()
            
            # 사용 가능 여부 확인
            is_available = client.is_available()
            logger.info(f"📊 Claude 사용 가능: {is_available}")
            
            if is_available:
                # API 호출 테스트
                start_time = datetime.now()
                response = await client.generate_text(self.test_prompt, max_tokens=100)
                end_time = datetime.now()
                
                duration = (end_time - start_time).total_seconds()
                
                self.results["claude"] = {
                    "available": True,
                    "response_length": len(response) if response else 0,
                    "duration": duration,
                    "response_preview": response[:100] if response else "None",
                    "success": bool(response and len(response) > 10)
                }
                
                logger.info(f"✅ Claude 테스트 완료 - 응답 길이: {len(response)}, 소요시간: {duration:.2f}초")
            else:
                self.results["claude"] = {
                    "available": False,
                    "error": "API 키 없음"
                }
                logger.warning("⚠️ Claude API 키가 없습니다.")
                
        except Exception as e:
            logger.error(f"❌ Claude 테스트 실패: {e}")
            self.results["claude"] = {
                "available": False,
                "error": str(e)
            }
    
    def print_results(self):
        """테스트 결과 출력"""
        print("\n" + "="*80)
        print("🧪 LLM 통신 상태 테스트 결과")
        print("="*80)
        
        for model, result in self.results.items():
            print(f"\n📊 {model.upper()} 결과:")
            print(f"   사용 가능: {'✅' if result['available'] else '❌'}")
            
            if result['available']:
                print(f"   응답 길이: {result['response_length']}자")
                print(f"   소요시간: {result['duration']:.2f}초")
                print(f"   성공 여부: {'✅' if result['success'] else '❌'}")
                print(f"   응답 미리보기: {result['response_preview']}")
            else:
                print(f"   오류: {result.get('error', '알 수 없는 오류')}")
        
        # 요약
        print("\n" + "="*80)
        print("📈 요약:")
        available_count = sum(1 for r in self.results.values() if r['available'])
        success_count = sum(1 for r in self.results.values() if r.get('success', False))
        
        print(f"   총 모델 수: {len(self.results)}")
        print(f"   사용 가능: {available_count}/{len(self.results)}")
        print(f"   통신 성공: {success_count}/{len(self.results)}")
        print("="*80)
    
    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("🚀 LLM 통신 상태 테스트 시작...")
        
        # 병렬로 모든 테스트 실행
        await asyncio.gather(
            self.test_hyperclova(),
            self.test_chatgpt(),
            self.test_gemini(),
            self.test_claude()
        )
        
        self.print_results()


async def main():
    """메인 함수"""
    tester = LLMCommunicationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 