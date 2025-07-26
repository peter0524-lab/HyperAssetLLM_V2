"""
news_service의 ChromaDB에 키워드와 과거 사건 데이터를 추가하는 스크립트
- 키워드는 주간별로 그룹화하여 저장
- news_service/data/chroma 경로에 저장
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.database.vector_db import VectorDBClient
from datetime import datetime, timedelta
import json

class NewsServiceVectorDB(VectorDBClient):
    """news_service 전용 VectorDB 클라이언트"""
    
    def __init__(self):
        """news_service 경로로 ChromaDB 초기화"""
        # 부모 클래스 초기화 전에 환경변수 설정
        self.news_service_path = os.path.join(os.path.dirname(__file__), "data", "chroma")
        os.makedirs(self.news_service_path, exist_ok=True)
        
        # 환경변수 임시 설정
        original_chroma_path = os.environ.get("CHROMADB_PERSIST_DIRECTORY", None)
        os.environ["CHROMADB_PERSIST_DIRECTORY"] = self.news_service_path
        
        try:
            # 부모 클래스 초기화
            super().__init__()
            print(f"✅ news_service ChromaDB 초기화 완료: {self.news_service_path}")
        finally:
            # 원래 환경변수 복원
            if original_chroma_path:
                os.environ["CHROMADB_PERSIST_DIRECTORY"] = original_chroma_path
            elif "CHROMADB_PERSIST_DIRECTORY" in os.environ:
                del os.environ["CHROMADB_PERSIST_DIRECTORY"]

def add_weekly_keywords():
    """주간별 키워드 그룹화하여 추가"""
    print("🔑 미래에셋증권 주간별 키워드 추가 중...")
    
    client = NewsServiceVectorDB()
    
    # 주간별 키워드 데이터 (증권사 리서치 전문가 관점에서 중요도 분석)
    weekly_keywords_data = [
        {
            "week_start": "2015-04-20",
            "week_end": "2015-04-26",
            "keywords": ["목표주가 상향", "리포트 효과", "주가 급등"],
            "importance_scores": [0.95, 0.90, 0.75],
            "description": "증권사 리서치 부문의 목표주가 상향으로 인한 주가 급등 효과"
        },
        {
            "week_start": "2015-05-04",
            "week_end": "2015-05-10",
            "keywords": ["차익실현", "거래량 증가", "단기 조정"],
            "importance_scores": [0.45, 0.70, 0.40],
            "description": "상승 후 이익실현 매도로 인한 단기 조정"
        },
        {
            "week_start": "2016-05-16",
            "week_end": "2016-05-22",
            "keywords": ["합병계약", "밸류에이션", "불확실성 해소"],
            "importance_scores": [0.95, 0.90, 0.80],
            "description": "대우증권과의 합병으로 인한 시너지 효과 기대"
        },
        {
            "week_start": "2017-02-06",
            "week_end": "2017-02-12",
            "keywords": ["규제완화", "금융주 강세", "심리 개선"],
            "importance_scores": [0.75, 0.70, 0.55],
            "description": "미국 금융규제 완화로 인한 글로벌 금융주 강세"
        },
        {
            "week_start": "2017-06-05",
            "week_end": "2017-06-11",
            "keywords": ["디지털채널", "성장전략", "투자심리"],
            "importance_scores": [0.80, 0.75, 0.60],
            "description": "디지털 전환을 통한 사업 모델 혁신"
        },
        {
            "week_start": "2017-06-26",
            "week_end": "2017-07-02",
            "keywords": ["자사주 교환", "핀테크 제휴", "KOSPI2400"],
            "importance_scores": [0.90, 0.85, 0.50],
            "description": "네이버와의 전략적 제휴를 통한 핀테크 생태계 구축"
        },
        {
            "week_start": "2017-11-20",
            "week_end": "2017-11-26",
            "keywords": ["개인순매수", "저변동성수익", "증권업 탄력"],
            "importance_scores": [0.70, 0.55, 0.75],
            "description": "개인 투자자들의 순매수로 인한 주가 상승"
        },
        {
            "week_start": "2017-12-18",
            "week_end": "2017-12-24",
            "keywords": ["해외IB비용", "실적부담", "주가급락"],
            "importance_scores": [0.80, 0.75, 0.85],
            "description": "해외 IB 사업의 비용 증가로 인한 실적 부담"
        },
        {
            "week_start": "2020-03-16",
            "week_end": "2020-03-22",
            "keywords": ["코로나공포", "자사주소각", "급락반등"],
            "importance_scores": [0.95, 0.90, 0.80],
            "description": "코로나19 팬데믹으로 인한 글로벌 금융시장 충격"
        },
        {
            "week_start": "2020-03-23",
            "week_end": "2020-03-29",
            "keywords": ["V자반등", "소각효과", "변동성확대"],
            "importance_scores": [0.75, 0.80, 0.60],
            "description": "급락 후 급격한 반등으로 인한 변동성 확대"
        },
        {
            "week_start": "2021-01-11",
            "week_end": "2021-01-17",
            "keywords": ["ETF호조", "가이던스상향", "수익다변화"],
            "importance_scores": [0.75, 0.80, 0.70],
            "description": "ELS·ETF 판매 호조로 인한 수익성 개선"
        },
        {
            "week_start": "2025-05-26",
            "week_end": "2025-06-01",
            "keywords": ["정책수혜", "ATS출범", "소각의무화"],
            "importance_scores": [0.90, 0.85, 0.75],
            "description": "ATS 출범 등 정책 수혜로 인한 증권주 강세"
        },
        {
            "week_start": "2025-06-02",
            "week_end": "2025-06-08",
            "keywords": ["기관매수", "연속상승", "모멘텀지속"],
            "importance_scores": [0.80, 0.75, 0.65],
            "description": "기관 투자자들의 대량 매수로 인한 주가 상승"
        },
        {
            "week_start": "2025-06-23",
            "week_end": "2025-06-29",
            "keywords": ["최고가경신", "대량거래", "수급개선"],
            "importance_scores": [0.75, 0.70, 0.75],
            "description": "연중 최고가 경신으로 인한 기술적 돌파"
        },
                {
            "week_start": "2025-07-14",
            "week_end": "2025-07-20",
            "keywords": ["분리과세", "상법개정", "증권업 탄력력"],
            "importance_scores": [0.75, 0.70, 0.75],
            "description": "분리과세 등 정책 수혜로 인한 증권주 강세"
        }
    ]
    
    added_keywords = []
    
    for i, week_data in enumerate(weekly_keywords_data, 1):
        try:
            # 주간별 키워드 데이터 생성
            keyword_data = {
                "stock_code": "006800",
                "stock_name": "미래에셋증권",
                "keywords": week_data["keywords"],
                "week_start": datetime.strptime(week_data["week_start"], "%Y-%m-%d"),
                "week_end": datetime.strptime(week_data["week_end"], "%Y-%m-%d"),
                "importance_scores": week_data["importance_scores"]
            }
            
            keyword_id = client.add_keywords(keyword_data)
            added_keywords.append(keyword_id)
            
            print(f"✅ 주간 키워드 {i}/{len(weekly_keywords_data)} 추가: {week_data['week_start']} ~ {week_data['week_end']}")
            print(f"   키워드: {', '.join(week_data['keywords'])}")
            print(f"   설명: {week_data['description']}")
            print(f"   ID: {keyword_id}")
            print()
            
        except Exception as e:
            print(f"❌ 주간 키워드 {i}/{len(weekly_keywords_data)} 추가 실패: {e}")
    
    print(f"🔑 주간 키워드 총 {len(added_keywords)}/{len(weekly_keywords_data)}개 추가 완료")
    return added_keywords

def add_past_events_to_news_service():
    """news_service의 ChromaDB에 과거 사건 추가"""
    print("📚 news_service ChromaDB에 과거 사건 추가 중...")
    
    client = NewsServiceVectorDB()
    
    # 실제 미래에셋증권 과거 사건 데이터
    past_events = [
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "한샘 목표주가 상향 리포트",
            "event_type": "투자의견 리포트",
            "event_date": datetime(2015, 4, 22),
            "price_change": "+7.67%",
            "volume": "12,758,209",
            "description": "미래에셋증권이 고객사 한샘의 건축자재 시장 진출 성공 가능성을 근거로 목표주가를 상향하며 주가가 급등했습니다.",
            "url": "https://www.yna.co.kr/view/AKR20150422030200008"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "대우증권 합병계약 체결",
            "event_type": "M&A",
            "event_date": datetime(2016, 5, 16),
            "price_change": "+6.78%",
            "volume": "20,726,358",
            "description": "미래에셋증권과 미래에셋대우가 합병계약을 체결하며 밸류에이션 불확실성이 해소됐다는 분석이 확산되었습니다.",
            "url": "https://www2.seoul.co.kr/news/economy/2016/05/16/20160516800108"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "미국 규제완화 기대에 금융주 강세",
            "event_type": "글로벌 정책 영향",
            "event_date": datetime(2017, 2, 6),
            "price_change": "+5.85%",
            "volume": "10,594,749",
            "description": "트럼프 행정부의 금융규제 완화 기대가 확산되며 국내 증권주 전반이 상승했고 미래에셋증권도 동반 강세를 기록했습니다.",
            "url": "https://www.businesspost.co.kr/BP?command=article_view&num=42107"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "리테일 플랫폼 확대 계획 공개",
            "event_type": "사업 전략",
            "event_date": datetime(2017, 6, 9),
            "price_change": "+5.86%",
            "volume": "11,849,953",
            "description": "전자신문 인터뷰에서 경영진이 디지털 채널 강화 방침을 밝히자 투자자들의 성장 기대가 주가에 반영됐습니다.",
            "url": "https://m.etnews.com/20170609000067"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "네이버-미래에셋 자사주 상호매입",
            "event_type": "전략적 제휴",
            "event_date": datetime(2017, 6, 27),
            "price_change": "+0.48%",
            "volume": "54,147,632",
            "description": "미래에셋증권과 네이버가 5,000억 원 규모 자사주를 교환하며 핀테크 협력 시너지가 부각되었습니다.",
            "url": "https://www.thevaluenews.co.kr/news/7269"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "코스피 2400 돌파 — 증권주 급등",
            "event_type": "시장 랠리",
            "event_date": datetime(2017, 6, 29),
            "price_change": "+5.64%",
            "volume": "12,223,296",
            "description": "지수 2,400p 첫 돌파와 함께 증권주가 동반 강세를 보였고 미래에셋증권이 상대적으로 큰 폭 상승했습니다.",
            "url": "https://www.etnews.com/20170629000279"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "한달간 8.9% 상승 — 거래주체 분석",
            "event_type": "수급 분석",
            "event_date": datetime(2017, 11, 22),
            "price_change": "+6.22%",
            "volume": "12,474,819",
            "description": "기관과 외국인이 매도 우위였지만 개인 순매수가 주가를 견인했다는 분석이 제시됐습니다.",
            "url": "https://www.etnews.com/20171122000185"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "해외 IB 투자 확대 우려",
            "event_type": "실적 경고",
            "event_date": datetime(2017, 12, 18),
            "price_change": "-13.47%",
            "volume": "18,243,412",
            "description": "연말 리포트에서 해외 IB 부문의 비용 부담 가능성이 지적되며 주가가 급락했습니다.",
            "url": "https://www.yna.co.kr/view/AKR20171218036000008"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "코로나19 공포 — 4일간 변동성 극심",
            "event_type": "팬데믹 충격·자사주 소각 발표",
            "event_date": datetime(2020, 3, 19),
            "price_change": "-20.53% ➜ +38.5% (4영업일)",
            "volume": "36,023,167(누적)",
            "description": "19일 급락 이후 20일 자사주 1,300만 주 소각 결정이 발표되면서 4거래일간 주가가 V자 반등했습니다.",
            "url": "https://www.mk.co.kr/economy/view.php?sc=50000001&year=2020&no=392063"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "EB · ETF 호조로 FY20 가이던스 상향",
            "event_type": "실적 가이던스",
            "event_date": datetime(2021, 1, 11),
            "price_change": "3.45%",
            "volume": "16,591,160.0",
            "description": "연초 투자설명회에서 ELS·ETF 판매 호조를 근거로 연간 순이익 가이던스를 상향했습니다.",
            "url": "https://www.yna.co.kr/view/AKR20210111036851002"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "미래에셋證, 해외주식 수수료 수익 업계 1위…AI 서비스 차별화",
            "event_type": "수수료 수익 업계 1위",
            "event_date": datetime(2024, 11, 14),
            "price_change": "10.97%",
            "volume": " 3046661.0",
            "description": "미래에셋증권이 해외주식 투자 열풍 속에서 업계 최대 규모의 해외주식 수수료 수익을 달성했다. 24일 금융감독원 자료에 따르면, 미래에셋증권의 올해 3분기까지 누적 해외주식 수수료 수익은 1802억원으로, 전년 동기 대비 80.7% 증가했다.",
            "url": "https://www.viva100.com/article/20241124500058"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "정책 수혜 기대 — 증권주 7% 급등",
            "event_type": "정책 모멘텀",
            "event_date": datetime(2025, 5, 29),
            "price_change": "+7.24%",
            "volume": "N/A",
            "description": "ATS 출범·자사주 소각 의무화 가능성 등 정책 기대감으로 증권주가 강세를 보였습니다.",
            "url": "https://www.g-enews.com/article/Securities/2025/05/202505121014404048288320b10e_1"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "정책 모멘텀 연속 랠리",
            "event_type": "정책 모멘텀",
            "event_date": datetime(2025, 6, 4),
            "price_change": "+13.25%",
            "volume": "12,638,701",
            "description": "5월 말 정책 기대의 연장선에서 주가가 추가 급등했습니다.",
            "url": "https://www.g-enews.com/article/Securities/2025/05/202505121014404048288320b10e_1"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "title": "기관 대량 매수 — 연중 최고가 경신",
            "event_type": "수급 모멘텀",
            "event_date": datetime(2025, 6, 23),
            "price_change": "+10.34%",
            "volume": "15,565,213",
            "description": "기관 자금유입이 확대되며 연중 최고가를 경신했습니다.",
            "url": "https://www.g-enews.com/article/Securities/2025/05/202505121014404048288320b10e_1"
        }
    ]
    
    # 과거 사건 추가
    added_events = []
    for i, event in enumerate(past_events, 1):
        try:
            event_id = client.add_past_event(event)
            added_events.append(event_id)
            print(f"✅ 과거 사건 {i}/{len(past_events)} 추가: {event['event_type']} - {event['event_date'].strftime('%Y-%m-%d')}")
            
        except Exception as e:
            print(f"❌ 과거 사건 {i}/{len(past_events)} 추가 실패: {e}")
            # ID 중복인 경우 대체 방법 시도
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                try:
                    import time
                    import hashlib
                    
                    # 고유 ID 생성
                    timestamp = event['event_date'].strftime('%Y%m%d_%H%M%S')
                    title_hash = hashlib.md5(event['description'][:50].encode('utf-8')).hexdigest()[:6]
                    microseconds = int(time.time() * 1000000) % 1000000
                    
                    unique_id = f"event_{event['stock_code']}_{timestamp}_{title_hash}_{microseconds:06d}"
                    
                    # 직접 컬렉션에 추가
                    text = f"{event['event_type']} {event['description']}"
                    metadata = {
                        "stock_code": event["stock_code"],
                        "stock_name": event["stock_name"],
                        "event_type": event["event_type"],
                        "event_date": event["event_date"].isoformat(),
                        "price_change": event["price_change"],
                        "volume": event["volume"],
                        "description": event["description"],
                        "created_at": datetime.now().isoformat(),
                        "type": "past_event",
                    }
                    
                    client.collections["past_events"].add(
                        documents=[text], 
                        metadatas=[metadata], 
                        ids=[unique_id]
                    )
                    
                    added_events.append(unique_id)
                    print(f"✅ 과거 사건 {i}/{len(past_events)} 추가 (대체 ID): {event['event_type']} - {event['event_date'].strftime('%Y-%m-%d')}")
                    
                except Exception as alt_e:
                    print(f"❌ 과거 사건 {i}/{len(past_events)} 대체 방법도 실패: {alt_e}")
                    continue
            else:
                continue
    
    print(f"📚 과거 사건 총 {len(added_events)}/{len(past_events)}개 추가 완료")
    return added_events

def check_news_service_collections():
    """news_service ChromaDB 컬렉션 상태 확인"""
    print("📊 news_service ChromaDB 상태 확인 중...")
    
    client = NewsServiceVectorDB()
    stats = client.get_collection_stats()
    
    print("news_service ChromaDB 상태:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    return stats

def verify_news_service_data():
    """news_service에 추가된 데이터 검증"""
    print("🔍 news_service 데이터 검증 중...")
    
    client = NewsServiceVectorDB()
    
    # 키워드 검증
    print("\n1. 주간별 키워드 데이터 검증:")
    try:
        # 주간별 키워드 조회 테스트
        test_weeks = ["2015-04-20", "2017-02-06", "2020-03-16", "2025-05-26"]
        for week_start in test_weeks:
            try:
                # 해당 주차 키워드 조회
                results = client.collections["keywords"].get(
                    where={
                        "$and": [
                            {"stock_code": {"$eq": "006800"}},
                            {"week_start": {"$eq": week_start}}
                        ]
                    },
                    limit=1
                )
                
                if results and len(results['ids']) > 0:
                    metadata = results['metadatas'][0]
                    keywords_json = metadata.get('keywords_json', '[]')
                    keywords = json.loads(keywords_json)
                    print(f"   ✅ {week_start} 주차 키워드: {keywords}")
                else:
                    print(f"   ❌ {week_start} 주차 키워드 없음")
                    
            except Exception as e:
                print(f"   ❌ {week_start} 주차 키워드 조회 실패: {e}")
                
    except Exception as e:
        print(f"   ❌ 키워드 검증 실패: {e}")
    
    # 과거 사건 검증
    print("\n2. 과거 사건 데이터 검증:")
    try:
        past_events = client.search_past_events("투자의견 리포트", "006800", top_k=3)
        if past_events:
            print(f"   ✅ 과거 사건 검색 성공: {len(past_events)}개 발견")
            for i, event in enumerate(past_events[:2], 1):
                event_type = event['metadata'].get('event_type', 'Unknown')
                event_date = event['metadata'].get('event_date', 'Unknown')
                similarity = event.get('similarity', 0.0)
                print(f"     {i}. {event_type} ({event_date[:10]}) - 유사도: {similarity:.3f}")
        else:
            print("   ❌ 과거 사건 검색 결과 없음")
    except Exception as e:
        print(f"   ❌ 과거 사건 검증 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 news_service ChromaDB 데이터 추가 시작")
    print("📍 저장 위치: services/news_service/data/chroma")
    print("🔑 키워드 저장 방식: 주간별 그룹화")
    print("📊 증권 전문가 관점에서 중요도 분석 적용")
    print("=" * 70)
    
    # 시작 전 상태 확인
    print("📋 시작 전 news_service ChromaDB 상태:")
    initial_stats = check_news_service_collections()
    print("\n" + "=" * 70)
    
    # 주간별 키워드 추가
    keyword_results = add_weekly_keywords()
    print()
    
    # 과거 사건 추가
    events_results = add_past_events_to_news_service()
    print()
    
    # 완료 후 상태 확인
    print("=" * 70)
    print("📋 완료 후 news_service ChromaDB 상태:")
    final_stats = check_news_service_collections()
    print()
    
    # 추가된 데이터 검증
    print("=" * 70)
    verify_news_service_data()
    print()
    
    # 결과 요약
    print("=" * 70)
    print("🎉 news_service ChromaDB 데이터 추가 완료!")
    print(f"   📊 주간별 키워드 추가: {len(keyword_results)}개")
    print(f"   📚 과거 사건 추가: {len(events_results) if events_results else 0}개")
    print()
    print("📈 컬렉션 변화:")
    initial_keywords = initial_stats.get('keywords', {}).get('count', 0)
    final_keywords = final_stats.get('keywords', {}).get('count', 0)
    initial_past_events = initial_stats.get('past_events', {}).get('count', 0)
    final_past_events = final_stats.get('past_events', {}).get('count', 0)
    
    print(f"   • keywords: {initial_keywords} → {final_keywords} (+{final_keywords - initial_keywords})")
    print(f"   • past_events: {initial_past_events} → {final_past_events} (+{final_past_events - initial_past_events})")
    print()
    print("✨ news_service에서 이제 이 데이터들을 사용할 수 있습니다!")
    print(f"📂 저장 경로: {os.path.join(os.path.dirname(__file__), 'data', 'chroma')}")

if __name__ == "__main__":
    main() 