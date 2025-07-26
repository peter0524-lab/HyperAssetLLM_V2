#!/usr/bin/env python3
"""
Frontend 데이터 흐름 테스트 스크립트
순서: 1. 프로필(데이터_85) -> 2. 종목(데이터_87) -> 3. 모델(데이터_86)
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

# 로깅 설정 - 상세한 디버그 로그 포함
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('frontend_data_flow_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# HTTP 요청/응답 로깅을 위한 추가 로거
http_logger = logging.getLogger("http_debug")
http_logger.setLevel(logging.DEBUG)

class FrontendDataFlowTester:
    """Frontend 데이터 흐름 테스트 클래스"""
    
    def __init__(self):
        self.base_url = "http://localhost:8005"  # API Gateway
        self.user_service_url = "http://localhost:8006"  # User Service 직접 호출
        self.session = None
        
        # 테스트 데이터 (Frontend에서 보내는 실제 데이터 형태)
        self.test_users = [
            {
                # 1단계: 사용자 프로필 (데이터_85.json 구조)
                                 "profile": {
                     "username": "김투자",
                     "phone_number": "01099998888",
                     "news_similarity_threshold": 0.8,
                     "news_impact_threshold": 0.6
                 },
                # 2단계: 사용자 종목 (데이터_87.json 구조)
                "stocks": [
                    {
                        "stock_code": "005930",
                        "stock_name": "삼성전자",
                        "enabled": True
                    },
                    {
                        "stock_code": "000660", 
                        "stock_name": "SK하이닉스",
                        "enabled": True
                    }
                ],
                                 # 3단계: 사용자 모델 (데이터_86.json 구조)
                 "model": {
                     "model_type": "hyperclova"
                 }
            },
            {
                                 "profile": {
                     "username": "박분석가",
                     "phone_number": "01077776666",
                     "news_similarity_threshold": 1.0,
                     "news_impact_threshold": 0.7
                 },
                "stocks": [
                    {
                        "stock_code": "035420",
                        "stock_name": "NAVER",
                        "enabled": True
                    },
                    {
                        "stock_code": "051910",
                        "stock_name": "LG화학", 
                        "enabled": False
                    }
                ],
                "model": {
                      "model_type": "hyperclova"
                }
            }
        ]
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def step1_create_profile(self, profile_data: Dict) -> str:
        """1단계: 사용자 프로필 생성 (데이터_85.json)"""
        logger.info("🔵 1단계: 사용자 프로필 생성 시작")
        logger.debug(f"📤 요청 URL: {self.user_service_url}/users/profile")
        logger.debug(f"📤 요청 데이터: {json.dumps(profile_data, ensure_ascii=False, indent=2)}")
        
        try:
            async with self.session.post(
                f"{self.user_service_url}/users/profile",
                json=profile_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                # 응답 헤더 로깅
                logger.debug(f"📥 응답 상태: {response.status}")
                logger.debug(f"📥 응답 헤더: {dict(response.headers)}")
                
                response_text = await response.text()
                logger.debug(f"📥 응답 본문: {response_text}")
                
                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        user_id = result["data"]["user_id"]
                        logger.info(f"✅ 프로필 생성 성공: user_id={user_id}")
                        logger.info(f"   - 사용자명: {profile_data['username']}")
                        logger.info(f"   - 전화번호: {profile_data['phone_number']}")
                        logger.info(f"   - 뉴스 유사도 임계값: {profile_data['news_similarity_threshold']}")
                        logger.info(f"   - 뉴스 영향도 임계값: {profile_data['news_impact_threshold']}")
                        logger.debug(f"📋 전체 응답 데이터: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        return user_id
                    except json.JSONDecodeError as je:
                        logger.error(f"❌ JSON 파싱 실패: {je}")
                        logger.error(f"❌ 원본 응답: {response_text}")
                        return None
                else:
                    logger.error(f"❌ 프로필 생성 실패: HTTP {response.status}")
                    logger.error(f"❌ 에러 응답: {response_text}")
                    
                    # 상태 코드별 상세 분석
                    if response.status == 400:
                        logger.error("💡 400 에러: 요청 데이터 검증 실패 또는 중복 전화번호")
                    elif response.status == 500:
                        logger.error("💡 500 에러: 서버 내부 오류 (DB 연결, 쿼리 실행 등)")
                    elif response.status == 404:
                        logger.error("💡 404 에러: User Service가 실행되지 않았거나 엔드포인트 경로 오류")
                    
                    return None
                    
        except aiohttp.ClientConnectorError as ce:
            logger.error(f"❌ 연결 실패: {ce}")
            logger.error("💡 User Service(Port 8006)가 실행 중인지 확인하세요")
            return None
        except asyncio.TimeoutError:
            logger.error("❌ 요청 타임아웃")
            logger.error("💡 서버 응답이 너무 느립니다")
            return None
        except Exception as e:
            logger.error(f"❌ 프로필 생성 중 예상치 못한 오류: {e}")
            logger.error(f"❌ 오류 타입: {type(e).__name__}")
            import traceback
            logger.debug(f"📋 상세 스택 트레이스:\n{traceback.format_exc()}")
            return None
    
    async def step2_set_stocks(self, user_id: str, stocks_data: List[Dict]) -> bool:
        """2단계: 사용자 종목 설정 (데이터_87.json)"""
        logger.info("🟡 2단계: 사용자 종목 설정 시작")
        
        request_data = {"stocks": stocks_data}
        url = f"{self.base_url}/api/user/stocks/{user_id}"
        
        logger.debug(f"📤 요청 URL: {url}")
        logger.debug(f"📤 사용자 ID: {user_id}")
        logger.debug(f"📤 요청 데이터: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        
        try:
            # API Gateway를 통해 종목 설정
            async with self.session.post(
                url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                # 응답 상세 로깅
                logger.debug(f"📥 응답 상태: {response.status}")
                logger.debug(f"📥 응답 헤더: {dict(response.headers)}")
                
                response_text = await response.text()
                logger.debug(f"📥 응답 본문: {response_text}")
                
                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        logger.info(f"✅ 종목 설정 성공: user_id={user_id}")
                        logger.debug(f"📋 API Gateway 응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        
                        for stock in stocks_data:
                            status = "활성화" if stock["enabled"] else "비활성화"
                            logger.info(f"   - {stock['stock_name']}({stock['stock_code']}): {status}")
                        return True
                    except json.JSONDecodeError as je:
                        logger.error(f"❌ JSON 파싱 실패: {je}")
                        logger.error(f"❌ 원본 응답: {response_text}")
                        return False
                else:
                    logger.error(f"❌ 종목 설정 실패: HTTP {response.status}")
                    logger.error(f"❌ 에러 응답: {response_text}")
                    
                    # 상태 코드별 상세 분석
                    if response.status == 400:
                        logger.error("💡 400 에러: 잘못된 요청 데이터 또는 user_id 형식 오류")
                    elif response.status == 404:
                        logger.error("💡 404 에러: 존재하지 않는 user_id 또는 API Gateway 연결 실패")
                    elif response.status == 500:
                        logger.error("💡 500 에러: User Service 내부 오류 또는 DB 연결 실패")
                    elif response.status == 503:
                        logger.error("💡 503 에러: User Service가 응답하지 않음")
                    
                    return False
                    
        except aiohttp.ClientConnectorError as ce:
            logger.error(f"❌ 연결 실패: {ce}")
            logger.error("💡 API Gateway(Port 8005)가 실행 중인지 확인하세요")
            return False
        except asyncio.TimeoutError:
            logger.error("❌ 요청 타임아웃")
            logger.error("💡 API Gateway 또는 User Service 응답이 너무 느립니다")
            return False
        except Exception as e:
            logger.error(f"❌ 종목 설정 중 예상치 못한 오류: {e}")
            logger.error(f"❌ 오류 타입: {type(e).__name__}")
            import traceback
            logger.debug(f"📋 상세 스택 트레이스:\n{traceback.format_exc()}")
            return False
    
    async def step3_set_model(self, user_id: str, model_data: Dict) -> bool:
        """3단계: 사용자 모델 설정 (데이터_86.json)"""
        logger.info("🟢 3단계: 사용자 모델 설정 시작")
        
        url = f"{self.base_url}/api/user/model/{user_id}"
        
        logger.debug(f"📤 요청 URL: {url}")
        logger.debug(f"📤 사용자 ID: {user_id}")
        logger.debug(f"📤 요청 데이터: {json.dumps(model_data, ensure_ascii=False, indent=2)}")
        
        try:
            # API Gateway를 통해 모델 설정
            async with self.session.post(
                url,
                json=model_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                # 응답 상세 로깅
                logger.debug(f"📥 응답 상태: {response.status}")
                logger.debug(f"📥 응답 헤더: {dict(response.headers)}")
                
                response_text = await response.text()
                logger.debug(f"📥 응답 본문: {response_text}")
                
                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        logger.info(f"✅ 모델 설정 성공: user_id={user_id}")
                        logger.info(f"   - 선택된 모델: {model_data['model_type']}")
                        logger.debug(f"📋 API Gateway 응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        return True
                    except json.JSONDecodeError as je:
                        logger.error(f"❌ JSON 파싱 실패: {je}")
                        logger.error(f"❌ 원본 응답: {response_text}")
                        return False
                else:
                    logger.error(f"❌ 모델 설정 실패: HTTP {response.status}")
                    logger.error(f"❌ 에러 응답: {response_text}")
                    
                    # 상태 코드별 상세 분석
                    if response.status == 400:
                        logger.error("💡 400 에러: 잘못된 model_type 또는 요청 데이터 형식 오류")
                        logger.error("💡 허용되는 모델: hyperclova, chatgpt, claude, grok, gemini")
                    elif response.status == 404:
                        logger.error("💡 404 에러: 존재하지 않는 user_id")
                    elif response.status == 500:
                        logger.error("💡 500 에러: User Service 내부 오류 또는 DB 연결 실패")
                    elif response.status == 503:
                        logger.error("💡 503 에러: User Service가 응답하지 않음")
                    
                    return False
                    
        except aiohttp.ClientConnectorError as ce:
            logger.error(f"❌ 연결 실패: {ce}")
            logger.error("💡 API Gateway(Port 8005)가 실행 중인지 확인하세요")
            return False
        except asyncio.TimeoutError:
            logger.error("❌ 요청 타임아웃")
            logger.error("💡 API Gateway 또는 User Service 응답이 너무 느립니다")
            return False
        except Exception as e:
            logger.error(f"❌ 모델 설정 중 예상치 못한 오류: {e}")
            logger.error(f"❌ 오류 타입: {type(e).__name__}")
            import traceback
            logger.debug(f"📋 상세 스택 트레이스:\n{traceback.format_exc()}")
            return False
    
    async def verify_complete_config(self, user_id: str) -> bool:
        """설정 완료 후 전체 설정 검증"""
        logger.info("🔍 설정 검증: 전체 사용자 설정 조회")
        
        url = f"{self.base_url}/api/user/config/{user_id}"
        logger.debug(f"📤 검증 요청 URL: {url}")
        logger.debug(f"📤 검증 대상 사용자 ID: {user_id}")
        
        try:
            async with self.session.get(
                url,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                # 응답 상세 로깅
                logger.debug(f"📥 응답 상태: {response.status}")
                logger.debug(f"📥 응답 헤더: {dict(response.headers)}")
                
                response_text = await response.text()
                logger.debug(f"📥 응답 본문: {response_text}")
                
                if response.status == 200:
                    try:
                        response_data = json.loads(response_text)
                        logger.debug(f"📋 전체 설정 데이터: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                        
                        # API Gateway 응답에서 실제 데이터 추출
                        config = response_data.get('data', response_data)
                        
                        logger.info("✅ 전체 설정 검증 성공:")
                        logger.info(f"   📋 사용자 정보:")
                        logger.info(f"      - ID: {config.get('user_id')}")
                        logger.info(f"      - 이름: {config.get('username')}")
                        logger.info(f"      - 전화번호: {config.get('phone_number')}")
                        logger.info(f"   📊 임계값 설정:")
                        logger.info(f"      - 뉴스 유사도: {config.get('news_similarity_threshold')}")
                        logger.info(f"      - 뉴스 영향도: {config.get('news_impact_threshold')}")
                        logger.info(f"   📈 종목 설정:")
                        
                        stocks = config.get('stocks', [])
                        if stocks:
                            for stock in stocks:
                                status = "✓" if stock.get('enabled') else "✗"
                                logger.info(f"      - {stock.get('stock_name')}({stock.get('stock_code')}): {status}")
                        else:
                            logger.warning("⚠️ 종목 설정이 없습니다")
                            
                        logger.info(f"   🤖 모델 설정: {config.get('model_type')}")
                        
                        # 데이터 완성도 검증
                        missing_fields = []
                        if not config.get('user_id'):
                            missing_fields.append('user_id')
                        if not config.get('username'):
                            missing_fields.append('username')
                        if not config.get('phone_number'):
                            missing_fields.append('phone_number')
                        if config.get('news_similarity_threshold') is None:
                            missing_fields.append('news_similarity_threshold')
                        if config.get('news_impact_threshold') is None:
                            missing_fields.append('news_impact_threshold')
                        if not config.get('model_type'):
                            missing_fields.append('model_type')
                        
                        if missing_fields:
                            logger.warning(f"⚠️ 누락된 필드: {', '.join(missing_fields)}")
                        else:
                            logger.info("✨ 모든 필수 필드가 완성되었습니다")
                        
                        return True
                        
                    except json.JSONDecodeError as je:
                        logger.error(f"❌ JSON 파싱 실패: {je}")
                        logger.error(f"❌ 원본 응답: {response_text}")
                        return False
                else:
                    logger.error(f"❌ 설정 검증 실패: HTTP {response.status}")
                    logger.error(f"❌ 에러 응답: {response_text}")
                    
                    # 상태 코드별 상세 분석
                    if response.status == 404:
                        logger.error("💡 404 에러: 존재하지 않는 user_id 또는 설정이 완전히 생성되지 않음")
                    elif response.status == 500:
                        logger.error("💡 500 에러: API Gateway 또는 User Service 내부 오류")
                    elif response.status == 503:
                        logger.error("💡 503 에러: User Service가 응답하지 않음")
                    
                    return False
                    
        except aiohttp.ClientConnectorError as ce:
            logger.error(f"❌ 연결 실패: {ce}")
            logger.error("💡 API Gateway(Port 8005)가 실행 중인지 확인하세요")
            return False
        except asyncio.TimeoutError:
            logger.error("❌ 요청 타임아웃")
            logger.error("💡 API Gateway 또는 User Service 응답이 너무 느립니다")
            return False
        except Exception as e:
            logger.error(f"❌ 설정 검증 중 예상치 못한 오류: {e}")
            logger.error(f"❌ 오류 타입: {type(e).__name__}")
            import traceback
            logger.debug(f"📋 상세 스택 트레이스:\n{traceback.format_exc()}")
            return False
    
    async def test_service_execution(self, user_id: str) -> bool:
        """보너스: 설정된 사용자로 서비스 실행 테스트"""
        logger.info("🚀 보너스: 서비스 실행 테스트")
        logger.debug(f"📤 서비스 실행 대상 사용자 ID: {user_id}")
        
        services = [
            ("뉴스 서비스", "/api/news/execute"),
            ("공시 서비스", "/api/disclosure/execute"),
            ("차트 서비스", "/api/chart/execute"),
            ("리포트 서비스", "/api/report/execute"),
            ("플로우 분석 서비스", "/api/flow/execute")
        ]
        
        success_count = 0
        
        for service_name, endpoint in services:
            url = f"{self.base_url}{endpoint}"
            headers = {"X-User-ID": user_id, "Content-Type": "application/json"}
            
            logger.debug(f"📤 {service_name} 요청 URL: {url}")
            logger.debug(f"📤 {service_name} 요청 헤더: {headers}")
            
            try:
                async with self.session.post(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    # 응답 상세 로깅
                    logger.debug(f"📥 {service_name} 응답 상태: {response.status}")
                    logger.debug(f"📥 {service_name} 응답 헤더: {dict(response.headers)}")
                    
                    response_text = await response.text()
                    logger.debug(f"📥 {service_name} 응답 본문: {response_text}")
                    
                    if response.status == 200:
                        try:
                            result = json.loads(response_text)
                            logger.debug(f"📋 {service_name} 파싱된 응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
                            
                            # API Gateway 응답에서 실제 데이터 추출
                            service_data = result.get('data', result)
                            if result.get("success", False) or service_data.get("success", False):
                                logger.info(f"✅ {service_name} 실행 성공")
                                success_count += 1
                            else:
                                message = result.get('message', service_data.get('message', 'Unknown'))
                                logger.warning(f"⚠️ {service_name} 실행 완료 (결과: {message})")
                                
                        except json.JSONDecodeError as je:
                            logger.warning(f"⚠️ {service_name} JSON 파싱 실패: {je}")
                            logger.warning(f"⚠️ 원본 응답: {response_text}")
                    else:
                        logger.warning(f"⚠️ {service_name} 실행 실패: HTTP {response.status}")
                        logger.warning(f"⚠️ 에러 응답: {response_text}")
                        
                        # 상태 코드별 상세 분석
                        if response.status == 404:
                            logger.warning(f"💡 {service_name} 404 에러: 서비스가 실행되지 않았거나 엔드포인트 오류")
                        elif response.status == 500:
                            logger.warning(f"💡 {service_name} 500 에러: 서비스 내부 오류")
                        elif response.status == 503:
                            logger.warning(f"💡 {service_name} 503 에러: 서비스가 응답하지 않음")
                        
            except aiohttp.ClientConnectorError as ce:
                logger.warning(f"⚠️ {service_name} 연결 실패: {ce}")
                logger.warning("💡 해당 서비스가 실행 중인지 확인하세요")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ {service_name} 실행 타임아웃 (30초 초과)")
                logger.warning("💡 서비스 처리 시간이 너무 오래 걸립니다")
            except Exception as e:
                logger.warning(f"⚠️ {service_name} 실행 중 예상치 못한 오류: {e}")
                logger.warning(f"⚠️ 오류 타입: {type(e).__name__}")
                import traceback
                logger.debug(f"📋 {service_name} 상세 스택 트레이스:\n{traceback.format_exc()}")
        
        logger.info(f"📊 서비스 실행 결과: {success_count}/{len(services)} 성공")
        return success_count > 0
    
    async def test_single_user_flow(self, user_data: Dict) -> bool:
        """단일 사용자의 전체 데이터 흐름 테스트"""
        logger.info("=" * 80)
        logger.info(f"🧪 사용자 데이터 흐름 테스트 시작: {user_data['profile']['username']}")
        logger.info("=" * 80)
        
        # 1단계: 프로필 생성
        user_id = await self.step1_create_profile(user_data["profile"])
        if not user_id:
            logger.error("❌ 1단계 실패 - 테스트 중단")
            return False
        
        await asyncio.sleep(1)  # API 간격 조절
        
        # 2단계: 종목 설정
        stocks_success = await self.step2_set_stocks(user_id, user_data["stocks"])
        if not stocks_success:
            logger.error("❌ 2단계 실패 - 테스트 중단")
            return False
        
        await asyncio.sleep(1)  # API 간격 조절
        
        # 3단계: 모델 설정
        model_success = await self.step3_set_model(user_id, user_data["model"])
        if not model_success:
            logger.error("❌ 3단계 실패 - 테스트 중단")
            return False
        
        await asyncio.sleep(1)  # API 간격 조절
        
        # 설정 검증
        verify_success = await self.verify_complete_config(user_id)
        if not verify_success:
            logger.error("❌ 설정 검증 실패")
            return False
        
        await asyncio.sleep(2)  # 서비스 실행 전 대기
        
        # 서비스 실행 테스트
        execution_success = await self.test_service_execution(user_id)
        
        logger.info("=" * 80)
        if verify_success:
            logger.info(f"✅ 사용자 '{user_data['profile']['username']}' 데이터 흐름 테스트 완료")
        else:
            logger.error(f"❌ 사용자 '{user_data['profile']['username']}' 데이터 흐름 테스트 실패")
        logger.info("=" * 80)
        
        return verify_success
    
    async def run_all_tests(self):
        """모든 테스트 사용자에 대한 데이터 흐름 테스트 실행"""
        logger.info("🎯 Frontend 데이터 흐름 테스트 시작")
        logger.info(f"📅 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"👥 테스트 사용자 수: {len(self.test_users)}")
        logger.info(f"🔗 API Gateway URL: {self.base_url}")
        logger.info(f"👤 User Service URL: {self.user_service_url}")
        logger.info(f"📝 로그 파일: frontend_data_flow_test.log")
        
        # 테스트 환경 사전 체크
        logger.debug("🔍 테스트 환경 사전 체크 시작")
        await self._check_services_availability()
        
        success_count = 0
        failed_users = []
        
        for i, user_data in enumerate(self.test_users, 1):
            username = user_data['profile']['username']
            logger.info(f"\n🔄 테스트 진행: {i}/{len(self.test_users)} - {username}")
            logger.debug(f"📋 테스트 사용자 데이터: {json.dumps(user_data, ensure_ascii=False, indent=2)}")
            
            success = await self.test_single_user_flow(user_data)
            if success:
                success_count += 1
                logger.info(f"✅ {username} 테스트 성공")
            else:
                failed_users.append(username)
                logger.error(f"❌ {username} 테스트 실패")
            
            if i < len(self.test_users):
                logger.info("⏳ 다음 테스트를 위해 3초 대기...")
                await asyncio.sleep(3)
        
        # 최종 결과
        logger.info("\n" + "=" * 80)
        logger.info("📊 Frontend 데이터 흐름 테스트 최종 결과")
        logger.info("=" * 80)
        logger.info(f"✅ 성공: {success_count}/{len(self.test_users)} 사용자")
        logger.info(f"❌ 실패: {len(self.test_users) - success_count}/{len(self.test_users)} 사용자")
        
        if failed_users:
            logger.error(f"❌ 실패한 사용자: {', '.join(failed_users)}")
        
        if success_count == len(self.test_users):
            logger.info("🎉 모든 사용자 데이터 흐름 테스트 성공!")
        else:
            logger.warning("⚠️ 일부 사용자 테스트 실패 - 상세 로그를 확인하세요")
            logger.warning("💡 로그 파일에서 더 자세한 정보를 확인할 수 있습니다: frontend_data_flow_test.log")
        
        return success_count == len(self.test_users)
    
    async def _check_services_availability(self):
        """서비스 가용성 사전 체크"""
        logger.debug("🔍 서비스 가용성 체크 중...")
        
        # API Gateway 체크
        try:
            async with self.session.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    logger.debug("✅ API Gateway 연결 가능")
                else:
                    logger.warning(f"⚠️ API Gateway 응답 이상: {response.status}")
        except Exception as e:
            logger.warning(f"⚠️ API Gateway 연결 실패: {e}")
        
        # User Service 체크
        try:
            async with self.session.get(f"{self.user_service_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    logger.debug("✅ User Service 연결 가능")
                else:
                    logger.warning(f"⚠️ User Service 응답 이상: {response.status}")
        except Exception as e:
            logger.warning(f"⚠️ User Service 연결 실패: {e}")
            logger.warning("💡 start_all_services.py로 모든 서비스가 실행되었는지 확인하세요")

async def main():
    """메인 실행 함수"""
    try:
        async with FrontendDataFlowTester() as tester:
            success = await tester.run_all_tests()
            
            if success:
                logger.info("🎯 전체 테스트 성공!")
                return 0
            else:
                logger.error("❌ 전체 테스트 실패!")
                return 1
                
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자에 의해 테스트 중단")
        return 1
    except Exception as e:
        logger.error(f"💥 테스트 실행 중 치명적 오류: {e}")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 