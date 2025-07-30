"""
HyperCLOVA AI Client for stock analysis service
"""

import asyncio
import aiohttp
import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import re


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HyperCLOVAClient:
    """HyperCLOVA AI 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("HYPERCLOVA_API_KEY", "")
        self.base_url = base_url or "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003"
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
        """클라이언트 사용 가능 여부 확인"""
        # API 키나 기본 설정이 있으면 사용 가능으로 간주
        return True  # HyperCLOVA는 항상 사용 가능하다고 가정
            
    async def analyze_news_impact(self, news_content: str, stock_name: str) -> Dict:
        """뉴스 임팩트 분석"""
        try:
            prompt = f"""
            다음 뉴스가 {stock_name} 주식에 미치는 영향을 분석해주세요.
            
            뉴스 내용: {news_content}
            
            분석 결과를 다음 형식으로 제공해주세요:
            1. 영향도 점수 (0-1 사이): 
            2. 긍정/부정/중립: 
            3. 주요 키워드: 
            4. 예상 주가 영향: 
            """
            
            # 실제 API 호출 대신 시뮬레이션
            # 실제 구현시 HyperCLOVA API 호출
            
            # 키워드 기반 간단한 분석
            impact_score = self._calculate_simple_impact(news_content)
            
            return {
                "impact_score": impact_score,
                "sentiment": "긍정" if impact_score > 0.7 else "부정" if impact_score < 0.3 else "중립",
                "keywords": self._extract_keywords(news_content),
                "expected_impact": "상승" if impact_score > 0.7 else "하락" if impact_score < 0.3 else "보합",
                "analysis_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"뉴스 임팩트 분석 오류: {e}")
            return {
                "impact_score": 0.5,
                "sentiment": "중립",
                "keywords": [],
                "expected_impact": "보합",
                "analysis_time": datetime.now().isoformat()
            }
            
    async def analyze_disclosure_impact(self, disclosure_content: str, stock_name: str) -> Dict:
        """공시 임팩트 분석"""
        try:
            prompt = f"""
            당신은 주식 투자 전문가입니다. 다음 공시가 {stock_name} 주식에 미치는 영향을 분석해주세요.
            
            공시 내용:
            {disclosure_content}
            
            다음 분석 결과항목을 제공해주세요:


            1. 공시 요약 (3줄 이내):
            2. 영향도 점수 (0-1 사이, 0: 매우 부정적, 0.5: 중립, 1: 매우 긍정적):
            3. 긍정/부정/중립 판단 및 근거:
            4. 주요 키워드 (콤마로 구분):
            5. 예상 주가 영향 (상승/하락/보합):
            6. 영향 지속 시간(단기, 중기, 단기):
            

            위 분석 결과를 "정확하게 다음 형식으로" 대답해주세요
            형식:
            {{
                "공시 요약": "": ,
                "영향도 점수": float,
                "sentiment": "",
                "sentiment 판단근거":""
                "주요키워드": ["",""],
                "예상 주가 영향": "",
                "영향 지속 시간":""
            }}
            """
            
            session = await self._get_session()
            request_id = str(uuid.uuid4()).replace('-', '')
            
            headers = {
                
                    'Authorization': f'Bearer {self.api_key}',
                    'X-NCP-CLOVASTUDIO-REQUEST-ID': request_id,
                    'Content-Type': 'application/json; charset=utf-8',
                    'Accept': 'application/json'  # JSON 응답 요청
                }
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 주식 투자 전문가입니다. 공시 내용을 분석하여 투자자에게 도움이 되는 인사이트를 제공합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "topP": 0.8,
                "topK": 0,
                "maxTokens": 1000,
                "temperature": 0.3,
                "repeatPenalty": 5.0,
                "stopBefore": [],
                "includeAiFilters": True
            }
            def get_partial_key_value(d: dict, keyword: str):
                for k, v in d.items():
                    if keyword in k:
                        return v
                return None

                
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=timeout
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response_text = result["result"]["message"]["content"]
                        
                        # 응답 파싱############################################
        
                        try:
                            parsed = json.loads(response_text)
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ JSON 파싱 오류: {e}")
                            logger.error(f"⚠️ 실패한 응답 내용:\n{response_text}")
                            raise e
                    # 너가 원하는 필드 이름으로 key mapping
                        mapped_result = {
                            "summary": get_partial_key_value(parsed, "요약"),
                            "impact_score": get_partial_key_value(parsed, "점수"),
                            "sentiment": get_partial_key_value(parsed, "sentiment"),
                            "sentiment_reason": get_partial_key_value(parsed, "근거"),
                            "keywords": get_partial_key_value(parsed, "키워드"),
                            "expected_impact": get_partial_key_value(parsed, "예상"),
                            "impact_duration": get_partial_key_value(parsed, "지속"),
                        }
                        
                        print(mapped_result)

                        return mapped_result
                    else:
                        logger.error(f"API 호출 실패: {resp.status}")
                        raise Exception(f"API 호출 실패: {resp.status}")
                    
        except Exception as e:
            logger.error(f"공시 임팩트 분석 오류: {e}")
            return {
                        "summary": "공시 분석 실패",
                        "impact_score": 0.5,
                        "sentiment": "중립",
                        "sentiment_reason": "",
                        "keywords": [],
                        "expected_impact": "보합",
                        "impact_duration": "중기",
                    }
            
    async def generate_comprehensive_report_and_keywords(self, prompt) -> Dict:
        """
        최신 리서치 보고서 텍스트와 주간 시장 데이터를 기반으로 LLM에 프롬프트를 전달하여
        종합 주간 리포트와 핵심 키워드를 생성합니다.
        """
        try:

           
            
            session = await self._get_session()
            request_id = str(uuid.uuid4()).replace('-', '')
            
            # 'Authorization': 'Bearer nv-b8935535a68442e3bce731a356b119a4Xbzy',
            headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'X-NCP-CLOVASTUDIO-REQUEST-ID': request_id,
                    'Content-Type': 'application/json; charset=utf-8',
                    'Accept': 'application/json'  # JSON 응답 요청
                }
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 주식 투자 전문가입니다. 제공된 데이터를 기반으로 상세한 주간 리포트를 작성하고 핵심 키워드를 추출합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "topP": 0.8,
                "topK": 0,
                "maxTokens": 4000, # 충분한 토큰 설정
                "temperature": 0.3,
                "repeatPenalty": 5.0,
                "stopBefore": [],
                "includeAiFilters": True
            }
            
            def get_partial_key_value(d: dict, keyword: str):
                for k, v in d.items():
                    if keyword in k:
                        return v
                return None

            timeout = aiohttp.ClientTimeout(total=60)
            async with session.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=timeout
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response_text = result["result"]["message"]["content"]

                    # JSON 파싱 처리
                    import re
                    cleaned = re.sub(r'[\x00-\x1F\x7F]', '', response_text.strip())

                    try:
                        parsed = json.loads(cleaned)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON 파싱 오류: {e}")
                        logger.error(f"⚠️ 실패한 응답 내용:\n{response_text}")
                        return {"report": f"LLM 응답 파싱 실패: {e}", "keywords": []}

                    mapped_result = {
                        "report": get_partial_key_value(parsed, "report"),
                        "keywords": get_partial_key_value(parsed, "keyword"),
                    }

                    logger.info("LLM으로부터 주간 리포트 및 키워드 생성 완료")
                    return mapped_result

                else:
                    error_text = await resp.text()
                    logger.error(f"API 호출 실패: {resp.status}, 응답: {error_text}")
                    return {"report": f"API 호출 실패: {resp.status}", "keywords": []}
                    
        except Exception as e:
            logger.error(f"종합 리포트 및 키워드 생성 오류: {e}")
            return {"report": f"종합 리포트 생성 중 오류 발생: {e}", "keywords": []}

    async def analyze_price_movement(self, stock_name: str, price_change: float, volume: int, news_data: List[Dict], disclosure_data: List[Dict]) -> Dict:
        """주가 변동 원인 분석"""
        try:
            prompt = f"""
            {stock_name}의 주가가 {price_change}% 변동하고 거래량이 {volume}주를 기록했습니다.
            
            관련 뉴스: {news_data}
            관련 공시: {disclosure_data}
            
            주가 변동의 주요 원인을 분석해주세요:
            1. 주요 원인: 
            2. 영향도 순위: 
            3. 향후 전망: 
            """
            
            # 원인 분석
            causes = []
            if news_data:
                causes.append("뉴스 영향")
            if disclosure_data:
                causes.append("공시 영향")
            if volume > 10000000:  # 1천만주 이상
                causes.append("대량 거래")
            if abs(price_change) > 5:
                causes.append("급격한 변동")
                
            return {
                "main_cause": causes[0] if causes else "시장 전체 흐름",
                "all_causes": causes,
                "impact_ranking": causes,
                "future_outlook": "상승" if price_change > 0 else "하락" if price_change < 0 else "보합",
                "confidence": 0.8 if len(causes) > 1 else 0.6,
                "analysis_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"주가 변동 분석 오류: {e}")
            return {
                "main_cause": "시장 전체 흐름",
                "all_causes": [],
                "impact_ranking": [],
                "future_outlook": "보합",
                "confidence": 0.5,
                "analysis_time": datetime.now().isoformat()
            }
            
    async def generate_weekly_report(self, stock_name: str, weekly_data: Dict) -> Dict:
        """주간 보고서 생성"""
        try:
            prompt = f"""
            {stock_name}의 주간 데이터를 분석하여 보고서를 작성해주세요.
            
            주간 데이터: {weekly_data}
            
            보고서 형식:
            1. 주요 이슈 요약: 
            2. 주가 변동 분석: 
            3. 다음 주 전망: 
            4. 주요 모니터링 키워드: 
            """
            
            # 주간 데이터 분석
            news_count = len(weekly_data.get('news', []))
            disclosure_count = len(weekly_data.get('disclosures', []))
            price_change = weekly_data.get('price_change', 0)
            
            return {
                "summary": f"{stock_name} 주간 분석",
                "key_issues": [
                    f"뉴스 {news_count}건 발생",
                    f"공시 {disclosure_count}건 발생",
                    f"주가 {price_change}% 변동"
                ],
                "price_analysis": f"주가가 {price_change}% {'상승' if price_change > 0 else '하락' if price_change < 0 else '보합'}",
                "next_week_outlook": "상승" if price_change > 0 else "하락" if price_change < 0 else "보합",
                "monitoring_keywords": self._extract_keywords(str(weekly_data)),
                "generated_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"주간 보고서 생성 오류: {e}")
            return {
                "summary": f"{stock_name} 주간 분석",
                "key_issues": [],
                "price_analysis": "데이터 부족",
                "next_week_outlook": "보합",
                "monitoring_keywords": [],
                "generated_time": datetime.now().isoformat()
            }
            
    def _calculate_simple_impact(self, content: str) -> float:
        """간단한 임팩트 점수 계산"""
        positive_keywords = ["상승", "증가", "호재", "긍정", "성장", "개선", "확대", "투자", "계약", "흑자"]
        negative_keywords = ["하락", "감소", "악재", "부정", "감소", "악화", "축소", "적자", "손실", "취소"]
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in content)
        negative_count = sum(1 for keyword in negative_keywords if keyword in content)
        
        if positive_count + negative_count == 0:
            return 0.5
            
        return (positive_count) / (positive_count + negative_count)
        
    def _extract_keywords(self, content: str) -> List[str]:
        """키워드 추출"""
        keywords = []
        important_words = ["실적", "매출", "영업이익", "투자", "계약", "개발", "출시", "인수", "합병", "분할", "상장", "IPO"]
        
        for word in important_words:
            if word in content:
                keywords.append(word)
                
        return keywords[:5]  # 최대 5개

    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        """텍스트 생성 (API 키가 있으면 실제 API 호출, 없으면 키워드 기반 요약)"""
        try:
            logger.debug(f"📝 HyperCLOVA 클라이언트 - 프롬프트 수신: {len(prompt)}자")
            logger.debug(f"📝 프롬프트 내용 (처음 300자): {prompt[:300]}...")

            if not self.api_key:
                logger.warning("⚠️ HyperCLOVA API 키가 없습니다. 키워드 기반 요약으로 대체합니다.")
                return self._generate_keyword_based_summary(prompt)

            try:
                session = await self._get_session()
                
                # SkillStack1.1_1 방식으로 헤더 수정
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                # 프롬프트를 messages 포맷으로 변환
                messages = [
                    {"role": "system", "content": "당신은 주식 시장 전문 분석가입니다. 뉴스와 공시를 분석하여 투자자에게 유용한 정보를 제공합니다."},
                    {"role": "user", "content": prompt}
                ]
                
                # SkillStack1.1_1의 성공적인 페이로드 구조 사용
                payload = {
                    'messages': messages,
                    'topP': 0.8,
                    'topK': 0,
                    'maxTokens': max_tokens,
                    'temperature': 0.3,
                    'repeatPenalty': 1.2,
                    'stopBefore': [],
                    'includeAiFilters': True
                }
                
                logger.debug(f"🔗 API 호출 준비: URL={self.base_url}")
                logger.debug(f"🔗 요청 헤더: {headers}")
                logger.debug(f"🔗 요청 페이로드 크기: {len(str(payload))}자")
                
                timeout = aiohttp.ClientTimeout(total=60)  # 60초로 증가
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                ) as resp:
                    logger.debug(f"📡 API 응답 상태: {resp.status}")
                    
                    if resp.status == 200:
                        # 응답 텍스트 먼저 확인
                        response_text_raw = await resp.text()
                        logger.debug(f"📡 원본 응답 텍스트: {response_text_raw[:500]}...")
                        
                        try:
                            response_json = await resp.json()
                            logger.debug(f"🔍 API 응답 구조: {list(response_json.keys())}")
                            
                            # SkillStack1.1_1의 성공적인 응답 파싱 방식 사용
                            response_text = None
                            
                            # 방법 1: SkillStack1.1_1 방식 (result.message.content)
                            if "result" in response_json:
                                result = response_json["result"]
                                if "message" in result and "content" in result["message"]:
                                    response_text = result["message"]["content"]
                                    logger.debug("✅ 방법 1 성공: SkillStack1.1_1 방식")
                            
                            # 방법 2: 표준 OpenAI 형식
                            if not response_text and "choices" in response_json and response_json["choices"]:
                                choice = response_json["choices"][0]
                                if "message" in choice and "content" in choice["message"]:
                                    response_text = choice["message"]["content"]
                                    logger.debug("✅ 방법 2 성공: OpenAI 형식")
                            
                            # 방법 3: 단순 텍스트 응답
                            if not response_text and "text" in response_json:
                                response_text = response_json["text"]
                                logger.debug("✅ 방법 3 성공: 단순 텍스트")
                            
                            # 방법 4: content 직접 접근
                            if not response_text and "content" in response_json:
                                response_text = response_json["content"]
                                logger.debug("✅ 방법 4 성공: content 직접")
                            
                            if response_text and response_text.strip():
                                logger.info(f"✅ HyperCLOVA API 호출 성공: {len(response_text)}자 응답")
                                logger.debug(f"📝 응답 내용: {response_text[:200]}...")
                                return response_text.strip()
                            else:
                                logger.warning("⚠️ 모델이 빈 응답을 반환했습니다.")
                                logger.debug(f"🔍 전체 응답 JSON: {response_json}")
                                return self._generate_keyword_based_summary(prompt)
                                
                        except json.JSONDecodeError as json_error:
                            logger.warning(f"⚠️ JSON 파싱 실패: {json_error}")
                            logger.debug(f"🔍 원본 응답: {response_text_raw}")
                            return self._generate_keyword_based_summary(prompt)
                            
                    elif resp.status == 429:
                        logger.warning("⚠️ API 요청 제한 (429) - 키워드 기반 요약으로 대체")
                        return self._generate_keyword_based_summary(prompt)
                    else:
                        error_text = await resp.text()
                        logger.warning(f"⚠️ API 호출 실패 (상태코드: {resp.status})")
                        logger.debug(f"🔍 에러 응답: {error_text}")
                        return self._generate_keyword_based_summary(prompt)
                        
            except aiohttp.ClientError as client_error:
                logger.warning(f"⚠️ 네트워크 오류: {client_error}")
                return self._generate_keyword_based_summary(prompt)
            except Exception as api_error:
                logger.warning(f"⚠️ API 호출 중 오류: {api_error}")
                return self._generate_keyword_based_summary(prompt)
                
        except Exception as e:
            logger.error(f"❌ 텍스트 생성 실패: {e}")
            return self._generate_keyword_based_summary(prompt)

    async def generate_response(self, prompt: str) -> str:
        """generate_text의 별칭 (main.py 호환성)"""
        return await self.generate_text(prompt)

    def _generate_keyword_based_summary(self, prompt: str) -> str:
        """키워드 기반 요약 생성 (API 키 없을 때 fallback)"""
        try:
            logger.info("🔍 키워드 기반 요약 생성 중...")
            
            # 프롬프트에서 키워드 추출
            keywords = self._extract_keywords(prompt)
            
            if not keywords:
                return "뉴스 정보 추출 실패"
            
            # 키워드 기반 간단한 요약 생성
            summary = f"{', '.join(keywords[:3])} 관련 뉴스"
            
            logger.info(f"✅ 키워드 기반 요약 생성 완료: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ 키워드 기반 요약 생성 실패: {e}")
            return "뉴스 정보 추출 실패"

    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 전역 클라이언트 인스턴스
hyperclova_client = HyperCLOVAClient()


async def get_hyperclova_client() -> HyperCLOVAClient:
    """HyperCLOVA 클라이언트 반환"""
    return hyperclova_client
