"""
OpenAI ChatGPT Client for stock analysis service
"""

import aiohttp
import json
import asyncio
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI ChatGPT 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1/chat/completions"
        self.model = model
        self.session = None
        
    async def _get_session(self):
        """HTTP 세션 생성"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def is_available(self) -> bool:
        """API 키 사용 가능 여부 확인"""
        return self.api_key is not None
    
    def get_client_info(self) -> Dict[str, Any]:
        """클라이언트 정보 반환"""
        return {
            "client_type": "OpenAIClient",
            "has_api_key": self.api_key is not None,
            "base_url": self.base_url,
            "model": self.model
        }
    
    async def generate_response(self, prompt: str, **kwargs) -> Optional[str]:
        """OpenAI API를 통한 텍스트 생성"""
        try:
            if not self.is_available():
                logger.warning("⚠️ OpenAI API 키가 없습니다.")
                return None
            
            session = await self._get_session()
            
            # OpenAI API 요청 형식
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 한국 주식 시장 전문 분석가입니다. 뉴스와 공시를 분석하여 투자자에게 유용한 정보를 제공합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "top_p": kwargs.get("top_p", 0.8),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
                "stop": kwargs.get("stop_sequences", None)
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.debug(f"🔗 OpenAI API 호출: {self.base_url}")
            
            async with session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status == 200:
                    raw_response = await response.json()
                    logger.debug("✅ OpenAI API 호출 성공")
                    
                    # OpenAI 응답 파싱
                    if "choices" in raw_response and raw_response["choices"]:
                        content = raw_response["choices"][0]["message"]["content"]
                        return content
                    else:
                        logger.warning("⚠️ OpenAI 응답에 choices가 없습니다.")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"❌ OpenAI API 오류 {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("❌ OpenAI API 타임아웃")
            return None
        except Exception as e:
            logger.error(f"❌ OpenAI API 호출 실패: {e}")
            return None
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        """호환성을 위한 텍스트 생성 메서드"""
        response = await self.generate_response(prompt, max_tokens=max_tokens)
        return response if response else "텍스트 생성 실패"
    
    async def analyze_news_impact(self, news_content: str, stock_name: str) -> Dict:
        """뉴스 영향도 분석 (OpenAI 전용 프롬프트)"""
        prompt = f"""
당신은 한국 증권시장 전문가입니다.
다음 뉴스가 {stock_name}에 미치는 영향을 분석해주세요.

뉴스 내용: {news_content}

분석 요청사항:
1. 영향도 점수 (0.0-1.0): 이 뉴스가 주가에 미치는 영향의 강도
2. 방향성 (1-5): 1=매우부정, 2=부정, 3=중립, 4=긍정, 5=매우긍정
3. 시장 영향 분석: 구체적인 영향 요인과 메커니즘
4. 투자자 알림 메시지: 텔레그램 발송용 간결한 메시지

응답 형식을 정확히 지켜주세요:
영향도점수: 0.XX
방향성점수: X
시장영향: (상세 분석 내용)
알림메시지: (텔레그램용 메시지)
"""
        
        response = await self.generate_response(prompt, max_tokens=800)
        if not response:
            return {
                "impact_score": 0.5,
                "direction_score": 3,
                "analysis": "분석 실패",
                "message": "뉴스 분석 실패"
            }
        
        # 응답 파싱
        try:
            # 영향도 점수 추출 (0.0-1.0)
            impact_match = re.search(r'영향도점수:\s*([0-9.]+)', response)
            impact_score = float(impact_match.group(1)) if impact_match else 0.5
            impact_score = max(0.0, min(1.0, impact_score))  # 범위 제한
            
            # 방향성 점수 추출 (1-5)
            direction_match = re.search(r'방향성점수:\s*([1-5])', response)
            direction_score = int(direction_match.group(1)) if direction_match else 3
            
            # 시장영향 추출
            market_match = re.search(r'시장영향:\s*(.+?)(?=\n|알림메시지:|$)', response, re.DOTALL)
            analysis = market_match.group(1).strip() if market_match else response[:200]
            
            # 알림메시지 추출
            message_match = re.search(r'알림메시지:\s*(.+?)(?=\n|$)', response)
            message = message_match.group(1).strip() if message_match else f"{stock_name} 뉴스 분석 완료"
            
            return {
                "impact_score": impact_score,
                "direction_score": direction_score,
                "analysis": analysis,
                "message": message
            }
        except Exception as e:
            logger.error(f"❌ 뉴스 분석 응답 파싱 실패: {e}")
            return {
                "impact_score": 0.5,
                "direction_score": 3,
                "analysis": response[:200],
                "message": f"{stock_name} 관련 뉴스 분석 완료"
            }
    
    async def analyze_disclosure_impact(self, disclosure_content: str, stock_name: str) -> Dict:
        """공시 영향도 분석 (OpenAI 전용 프롬프트)"""
        prompt = f"""
당신은 공시 분석 전문가입니다.
다음 공시가 {stock_name}에 미치는 영향을 분석해주세요.

공시 내용: {disclosure_content}

분석 요청사항:
1. 공시 요약 (3줄 이내): 핵심 내용만 간결하게
2. 영향도 점수 (0.0-1.0): 0=무영향, 0.5=중간영향, 1.0=매우높은영향
3. 감정 판단 (긍정/부정/중립): 투자 관점에서의 감정
4. 감정 판단 근거: 긍정/부정 판단 이유
5. 주요 키워드: 핵심 키워드 3개
6. 예상 주가 영향: 상승/하락/보합
7. 영향 지속 시간: 단기/중기/장기

응답을 다음 JSON 형식으로 정확히 제공해주세요:
{{
    "공시요약": "요약내용",
    "영향도점수": 0.XX,
    "sentiment": "긍정/부정/중립",
    "sentiment판단근거": "판단근거",
    "주요키워드": ["키워드1", "키워드2", "키워드3"],
    "예상주가영향": "상승/하락/보합",
    "영향지속시간": "단기/중기/장기"
}}
"""
        
        response = await self.generate_response(prompt, max_tokens=1000)
        if not response:
            return {
                "summary": "분석 실패",
                "impact_score": 0.5,
                "sentiment": "중립",
                "sentiment_reason": "분석 실패",
                "keywords": ["분석", "실패", "재시도"],
                "expected_impact": "보합",
                "impact_duration": "중기"
            }
        
        # JSON 파싱 시도
        try:
            # JSON 추출 및 파싱
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                return {
                    "summary": parsed.get("공시요약", "요약 없음"),
                    "impact_score": float(parsed.get("영향도점수", 0.5)),
                    "sentiment": parsed.get("sentiment", "중립"),
                    "sentiment_reason": parsed.get("sentiment판단근거", "판단 근거 없음"),
                    "keywords": parsed.get("주요키워드", ["공시", "분석", "영향"]),
                    "expected_impact": parsed.get("예상주가영향", "보합"),
                    "impact_duration": parsed.get("영향지속시간", "중기")
                }
            else:
                # JSON 파싱 실패시 텍스트 파싱
                return self._parse_disclosure_text(response, stock_name)
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"⚠️ JSON 파싱 실패, 텍스트 파싱으로 전환: {e}")
            return self._parse_disclosure_text(response, stock_name)
    
    def _parse_disclosure_text(self, response: str, stock_name: str) -> Dict:
        """공시 분석 텍스트 파싱 (JSON 실패시 fallback)"""
        try:
            # 영향도 점수 추출
            impact_match = re.search(r'영향도.*?([0-9.]+)', response)
            impact_score = float(impact_match.group(1)) if impact_match else 0.5
            
            # 감정 추출
            sentiment = "중립"
            if "긍정" in response:
                sentiment = "긍정"
            elif "부정" in response:
                sentiment = "부정"
            
            # 키워드 추출
            keywords_match = re.search(r'키워드.*?[:：]\s*(.+?)(?=\n|$)', response)
            if keywords_match:
                keywords_text = keywords_match.group(1)
                keywords = [k.strip().strip('"[]') for k in re.split(r'[,，]', keywords_text)]
                keywords = [k for k in keywords if k][:3]
            else:
                keywords = ["공시", "분석", "영향"]
            
            # 예상 영향 추출
            if "상승" in response:
                expected_impact = "상승"
            elif "하락" in response:
                expected_impact = "하락"
            else:
                expected_impact = "보합"
            
            # 지속 시간 추출
            if "장기" in response:
                duration = "장기"
            elif "단기" in response:
                duration = "단기"
            else:
                duration = "중기"
            
            return {
                "summary": response[:200] + "..." if len(response) > 200 else response,
                "impact_score": impact_score,
                "sentiment": sentiment,
                "sentiment_reason": "텍스트 분석 기반",
                "keywords": keywords,
                "expected_impact": expected_impact,
                "impact_duration": duration
            }
        except Exception as e:
            logger.error(f"❌ 공시 텍스트 파싱 실패: {e}")
            return {
                "summary": f"{stock_name} 공시 분석",
                "impact_score": 0.5,
                "sentiment": "중립",
                "sentiment_reason": "파싱 실패",
                "keywords": ["공시", "분석", "영향"],
                "expected_impact": "보합",
                "impact_duration": "중기"
            }
    
    async def generate_comprehensive_report_and_keywords(self, research_report: str, weekly_market_data: List[Dict]) -> Dict:
        """종합 보고서 및 키워드 생성 (OpenAI 전용)"""
        prompt = f"""
당신은 주식 시장 전문 분석가입니다.
최신 리서치 보고서와 일주일치 시장 데이터를 바탕으로 종합 주간 리포트와 핵심 키워드를 생성해주세요.

리서치 보고서:
{research_report}

일주일치 시장 데이터:
{weekly_market_data}

요청사항:
1. 종합 분석 보고서 (1500자 내외): 다음 항목을 순서대로 포함
   - 시장 전반 요약 및 주요 이슈
   - 특정 종목 분석 (긍정적/부정적 요인, 투자 의견)
   - 주요 뉴스 및 공시 내용 요약 (날짜별 구분)
   - 차트 데이터 분석 (가격 변동, 거래량 추이)
   - 향후 전망 및 투자 전략 제안

2. 핵심 키워드 10개: 중요도가 높은 순서로

응답을 다음 JSON 형식으로 정확히 제공해주세요:
{{
    "report": "리포트 내용 여기에",
    "keywords": ["키워드1", "키워드2", "키워드3", ...]
}}
"""
        
        response = await self.generate_response(prompt, max_tokens=3000)
        if not response:
            return {
                "report": "종합 보고서 생성에 실패했습니다.",
                "keywords": ["시장", "분석", "투자", "주식", "전망"]
            }
        
        # JSON 파싱 시도
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                return {
                    "report": parsed.get("report", response[:1500]),
                    "keywords": parsed.get("keywords", ["시장", "분석", "투자", "주식", "전망"])[:10]
                }
            else:
                # JSON이 없으면 텍스트 파싱
                return self._parse_report_text(response)
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"⚠️ 보고서 JSON 파싱 실패, 텍스트 파싱으로 전환: {e}")
            return self._parse_report_text(response)
    
    def _parse_report_text(self, response: str) -> Dict:
        """보고서 텍스트 파싱 (JSON 실패시 fallback)"""
        try:
            # 키워드 추출 시도
            keywords_match = re.search(r'키워드.*?[:：]\s*(.+?)(?=\n|$)', response, re.MULTILINE)
            if keywords_match:
                keywords_text = keywords_match.group(1)
                keywords = [k.strip().strip('"[]') for k in re.split(r'[,，]', keywords_text)]
                keywords = [k for k in keywords if k][:10]
            else:
                keywords = ["시장", "분석", "투자", "주식", "전망", "실적", "뉴스", "공시", "변동", "리포트"]
            
            return {
                "report": response,
                "keywords": keywords
            }
        except Exception as e:
            logger.error(f"❌ 보고서 텍스트 파싱 실패: {e}")
            return {
                "report": response[:1500],
                "keywords": ["시장", "분석", "투자", "주식", "전망"]
            }
    
    async def analyze_price_movement(self, stock_name: str, price_change: float, volume: int, news_data: List[Dict], disclosure_data: List[Dict]) -> Dict:
        """주가 변동 원인 분석"""
        prompt = f"""
{stock_name}의 주가가 {price_change}% 변동하고 거래량이 {volume:,}주를 기록했습니다.

관련 뉴스: {news_data}
관련 공시: {disclosure_data}

주가 변동의 주요 원인을 분석해주세요:

응답 형식:
주요원인: [주된 원인 설명]
영향순위: [원인1, 원인2, 원인3]
향후전망: [상승/하락/보합]
신뢰도: [0.0-1.0]
분석근거: [판단 근거]
"""
        
        response = await self.generate_response(prompt, max_tokens=800)
        if not response:
            return self._get_fallback_price_analysis(stock_name, price_change, volume, news_data, disclosure_data)
        
        # 응답 파싱
        try:
            # 주요원인 추출
            cause_match = re.search(r'주요원인:\s*(.+?)(?=\n|영향순위:|$)', response, re.DOTALL)
            main_cause = cause_match.group(1).strip() if cause_match else "시장 전체 흐름"
            
            # 영향순위 추출
            ranking_match = re.search(r'영향순위:\s*(.+?)(?=\n|향후전망:|$)', response)
            if ranking_match:
                ranking_text = ranking_match.group(1)
                all_causes = [c.strip() for c in re.split(r'[,，]', ranking_text)]
            else:
                all_causes = [main_cause]
            
            # 향후전망 추출
            outlook_match = re.search(r'향후전망:\s*(.+?)(?=\n|신뢰도:|$)', response)
            outlook = outlook_match.group(1).strip() if outlook_match else "보합"
            
            # 신뢰도 추출
            confidence_match = re.search(r'신뢰도:\s*([0-9.]+)', response)
            confidence = float(confidence_match.group(1)) if confidence_match else 0.7
            
            # 분석근거 추출
            reason_match = re.search(r'분석근거:\s*(.+?)(?=\n|$)', response, re.DOTALL)
            analysis_reason = reason_match.group(1).strip() if reason_match else "데이터 기반 분석"
            
            return {
                "main_cause": main_cause,
                "all_causes": all_causes[:5],
                "impact_ranking": all_causes[:3],
                "future_outlook": outlook,
                "confidence": min(1.0, max(0.0, confidence)),
                "analysis_reason": analysis_reason,
                "analysis_time": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 주가 변동 분석 응답 파싱 실패: {e}")
            return self._get_fallback_price_analysis(stock_name, price_change, volume, news_data, disclosure_data)
    
    def _get_fallback_price_analysis(self, stock_name: str, price_change: float, volume: int, news_data: List[Dict], disclosure_data: List[Dict]) -> Dict:
        """주가 변동 분석 실패 시 fallback"""
        causes = []
        if news_data and len(news_data) > 0:
            causes.append("뉴스 영향")
        if disclosure_data and len(disclosure_data) > 0:
            causes.append("공시 영향")
        if volume > 10000000:  # 1천만주 이상
            causes.append("대량 거래")
        if abs(price_change) > 5:
            causes.append("급격한 변동")
        if abs(price_change) > 10:
            causes.append("매우 급격한 변동")
        
        return {
            "main_cause": causes[0] if causes else "시장 전체 흐름",
            "all_causes": causes,
            "impact_ranking": causes[:3],
            "future_outlook": "상승" if price_change > 0 else "하락" if price_change < 0 else "보합",
            "confidence": 0.6,
            "analysis_reason": "기본 지표 기반 분석",
            "analysis_time": datetime.now().isoformat()
        }
    
    async def generate_weekly_report(self, stock_name: str, weekly_data: Dict) -> Dict:
        """주간 보고서 생성"""
        prompt = f"""
{stock_name}의 주간 데이터를 분석하여 투자자용 주간 보고서를 작성해주세요.

주간 데이터: {weekly_data}

보고서 형식:
주요이슈요약: [이번 주 핵심 이슈들]
주가변동분석: [주가 변동 원인과 패턴 분석]
다음주전망: [다음 주 예상 시나리오]
모니터링키워드: [주요 관찰 키워드 5개]
투자전략: [단기 투자 전략 제안]
"""
        
        response = await self.generate_response(prompt, max_tokens=1200)
        if not response:
            return self._get_fallback_weekly_report(stock_name, weekly_data)
        
        # 응답 파싱
        try:
            # 주요이슈요약 추출
            issues_match = re.search(r'주요이슈요약:\s*(.+?)(?=\n|주가변동분석:|$)', response, re.DOTALL)
            if issues_match:
                issues_text = issues_match.group(1).strip()
                key_issues = [issue.strip() for issue in issues_text.split('\n') if issue.strip()]
            else:
                key_issues = [f"{stock_name} 주간 주요 이슈"]
            
            # 주가변동분석 추출
            price_match = re.search(r'주가변동분석:\s*(.+?)(?=\n|다음주전망:|$)', response, re.DOTALL)
            price_analysis = price_match.group(1).strip() if price_match else f"{stock_name} 주가 분석"
            
            # 다음주전망 추출
            outlook_match = re.search(r'다음주전망:\s*(.+?)(?=\n|모니터링키워드:|$)', response, re.DOTALL)
            next_week_outlook = outlook_match.group(1).strip() if outlook_match else "보합 전망"
            
            # 모니터링키워드 추출
            keywords_match = re.search(r'모니터링키워드:\s*(.+?)(?=\n|투자전략:|$)', response)
            if keywords_match:
                keywords_text = keywords_match.group(1)
                keywords = [k.strip() for k in re.split(r'[,，]', keywords_text)]
                keywords = [k for k in keywords if k][:5]
            else:
                keywords = [stock_name, "주가", "분석", "시장", "투자"]
            
            # 투자전략 추출
            strategy_match = re.search(r'투자전략:\s*(.+?)(?=\n|$)', response, re.DOTALL)
            investment_strategy = strategy_match.group(1).strip() if strategy_match else "신중한 관망"
            
            return {
                "summary": f"{stock_name} 주간 분석 보고서",
                "key_issues": key_issues[:5],
                "price_analysis": price_analysis,
                "next_week_outlook": next_week_outlook,
                "monitoring_keywords": keywords,
                "investment_strategy": investment_strategy,
                "generated_time": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 주간 보고서 응답 파싱 실패: {e}")
            return self._get_fallback_weekly_report(stock_name, weekly_data)
    
    def _get_fallback_weekly_report(self, stock_name: str, weekly_data: Dict) -> Dict:
        """주간 보고서 생성 실패 시 fallback"""
        news_count = len(weekly_data.get('news', []))
        disclosure_count = len(weekly_data.get('disclosures', []))
        price_change = weekly_data.get('price_change', 0)
        
        return {
            "summary": f"{stock_name} 주간 분석 보고서",
            "key_issues": [
                f"이번 주 뉴스 {news_count}건 발생",
                f"공시 {disclosure_count}건 공개",
                f"주가 {price_change:+.2f}% 변동 기록"
            ],
            "price_analysis": f"주가가 전주 대비 {price_change:+.2f}% {'상승' if price_change > 0 else '하락' if price_change < 0 else '보합'}했습니다.",
            "next_week_outlook": "상승 기대" if price_change > 0 else "하락 우려" if price_change < 0 else "보합 전망",
            "monitoring_keywords": [stock_name, "주가", "시장", "분석", "투자"],
            "investment_strategy": "시장 상황을 지켜보며 신중한 투자 필요",
            "generated_time": datetime.now().isoformat()
        }
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 전역 클라이언트 인스턴스
openai_client = OpenAIClient()


async def get_openai_client() -> OpenAIClient:
    """OpenAI 클라이언트 반환"""
    return openai_client