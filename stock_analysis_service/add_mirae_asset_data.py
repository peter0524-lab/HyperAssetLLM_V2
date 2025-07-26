"""
미래에셋증권 키워드와 과거 사건 데이터를 크로마 DB에 추가하는 스크립트
"""

from shared.database.vector_db import VectorDBClient
from datetime import datetime, timedelta
import json

def add_mirae_asset_keywords():
    """미래에셋증권 핵심 키워드 추가"""
    print("🔑 미래에셋증권 핵심 키워드 추가 중...")
    
    client = VectorDBClient()
    
    # 키워드 데이터
    keyword_data = {
        "stock_code": "006800",
        "stock_name": "미래에셋증권",
        "keywords": ["상법개정안", "분리과세", "실적호조"],
        "week_start": datetime(2024, 7, 4),
        "week_end": datetime(2024, 7, 11),
        "importance_scores": [5, 4, 4]  # 각 키워드의 중요도 점수
    }
    
    try:
        keyword_id = client.add_keywords(keyword_data)
        print(f"✅ 키워드 추가 성공: {keyword_id}")
        print(f"   키워드: {', '.join(keyword_data['keywords'])}")
        print(f"   기간: {keyword_data['week_start'].strftime('%Y-%m-%d')} ~ {keyword_data['week_end'].strftime('%Y-%m-%d')}")
        return keyword_id
    except Exception as e:
        print(f"❌ 키워드 추가 실패: {e}")
        return None

def add_mirae_asset_past_events():
    """미래에셋증권 과거 사건 데이터 추가"""
    print("📚 미래에셋증권 과거 사건 데이터 추가 중...")
    
    client = VectorDBClient()
    
    # 과거 사건 데이터 (뉴스 데이터를 과거 사건으로 변환)
    past_events = [
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "대선후보 공약 수혜",
            "event_date": datetime(2025, 5, 29, 10, 5),
            "price_change": "+14.43%",
            "volume": 20000000,  # 추정치
            "description": "[특징주] 미래에셋증권, '오천피 시대' 수혜 덕 52주 신고가 경신. 이재명 후보의 '코스피 5000' 공언에 수혜를 입어 상한가까지 오른 1만7470원을 터치하며 52주 신고가 경신"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "자사주 소각 의무화 기대",
            "event_date": datetime(2025, 7, 9, 15, 9),
            "price_change": "+5.92%",
            "volume": 15000000,  # 추정치
            "description": "'자사주 소각 의무화' 현실화 기대에 관련주 '랠리'. 정부·여당이 상법 개정에 이어 자사주 소각 의무화 법제화에 속도를 내면서 자사주 비중 22.98%인 미래에셋증권이 강세"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "코스피 3000 돌파 수혜",
            "event_date": datetime(2025, 6, 24, 14, 16),
            "price_change": "+4.87%",
            "volume": 18000000,  # 추정치
            "description": "[특징주] 증권주, 거래대금 급증·코스피 3000 돌파에 탄력. 장초 10% 넘게 급등 후 일부 반납. 새 정부의 자본시장 육성 정책과 밸류에이션 확장 기대감으로 강세"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "호실적 및 자사주 매입소각 기대",
            "event_date": datetime(2025, 5, 20, 9, 50),
            "price_change": "+1.64%",
            "volume": 12000000,  # 추정치
            "description": "[특징주] 미래에셋증권, 호실적에 자사주 매입·소각 기대감 '신고가'. 1분기 지배주주순이익 2587억원으로 컨센서스 5.9% 상회. 장중 1만 3300원까지 치솟아 52주 신고가 경신"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "호실적 및 정책 수혜",
            "event_date": datetime(2025, 5, 12, 11, 12),
            "price_change": "+7.15%",
            "volume": 16000000,  # 추정치
            "description": "[특징주] 미래에셋증권, 호실적·정책 수혜 기대에 7% 급등. 1분기 당기순이익 2582억원으로 전년 동기 대비 53% 증가. 종투사 기능 강화 및 코리아 디스카운트 해소 정책 기대감"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "국내 시장 활기 및 금리 인하",
            "event_date": datetime(2025, 3, 6, 16, 8),
            "price_change": "+7.55%",
            "volume": 14000000,  # 추정치
            "description": "[특징주] 미래에셋증권, 7% 상승 마감… 국내 시장 활기·금리 인하 영향. 국내 주식 시장 거래대금 31% 증가(21조2800억원). 채권평가이익 개선 전망으로 투심 상승"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "밸류업 계획 발표",
            "event_date": datetime(2024, 8, 23, 9, 37),
            "price_change": "+3.5%",  # 추정치
            "volume": 10000000,  # 추정치
            "description": "미래에셋증권, 밸류업 계획 발표에 '상승세'. 자사주 1억주 소각 등 기업가치 제고 계획 발표. ROE 10% 이상, 주주환원 성향 35% 이상 달성 목표. 2030년까지 자기주식 1억주 이상 소각 계획"
        },
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "event_type": "자사주 매입소각 결정",
            "event_date": datetime(2024, 8, 7, 10, 18),
            "price_change": "+5.09%",
            "volume": 8000000,  # 추정치
            "description": "미래에셋증권, 5%대 상승...'자사주 매입·소각' 호재로. 보통주 1000만주를 3개월에 걸쳐 매입·소각 발표. 유통 주식 수의 약 2.2%에 해당하는 규모로 주주가치 제고 효과 기대"
        }
    ]
    
    # 과거 사건 추가
    added_events = []
    for i, event in enumerate(past_events, 1):
        try:
            # ID 중복 방지를 위해 고유 ID 생성
            import hashlib
            import time
            
            # 타임스탬프와 제목으로 고유 ID 생성
            timestamp = event['event_date'].strftime('%Y%m%d_%H%M%S')
            title_hash = hashlib.md5(event['description'][:50].encode('utf-8')).hexdigest()[:6]
            
            # 기존 ID 포맷을 유지하되 고유성 보장
            original_id = f"event_{event['stock_code']}_{event['event_date'].strftime('%Y%m%d')}"
            unique_id = f"{original_id}_{title_hash}"
            
            # 임시로 event_id를 수정하여 add_past_event 호출
            event_data_copy = event.copy()
            
            # 컬렉션에 직접 추가 (ID 중복 방지)
            try:
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
                
                # 컬렉션에 추가
                client.collections["past_events"].add(
                    documents=[text], 
                    metadatas=[metadata], 
                    ids=[unique_id]
                )
                
                added_events.append(unique_id)
                print(f"✅ 과거 사건 {i}/8 추가: {event['event_type']} - {event['event_date'].strftime('%Y-%m-%d')}")
                
            except Exception as inner_e:
                print(f"❌ 과거 사건 {i}/8 추가 실패: {inner_e}")
                # ID 중복 에러인 경우 다른 ID로 시도
                if "already exists" in str(inner_e) or "duplicate" in str(inner_e).lower():
                    try:
                        microseconds = int(time.time() * 1000000) % 1000000
                        alternative_id = f"{unique_id}_{microseconds:06d}"
                        
                        client.collections["past_events"].add(
                            documents=[text], 
                            metadatas=[metadata], 
                            ids=[alternative_id]
                        )
                        
                        added_events.append(alternative_id)
                        print(f"✅ 과거 사건 {i}/8 추가 (대체 ID): {event['event_type']} - {event['event_date'].strftime('%Y-%m-%d')}")
                    except Exception as alt_e:
                        print(f"❌ 과거 사건 {i}/8 대체 ID로도 실패: {alt_e}")
                        continue
                else:
                    continue
                    
        except Exception as e:
            print(f"❌ 과거 사건 {i}/8 처리 실패: {e}")
            continue
    
    print(f"📚 과거 사건 총 {len(added_events)}/8개 추가 완료")
    return added_events

def check_collections_status():
    """컬렉션 상태 확인"""
    print("📊 컬렉션 상태 확인 중...")
    
    client = VectorDBClient()
    stats = client.get_collection_stats()
    
    print("현재 컬렉션 상태:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    return stats

def verify_added_data():
    """추가된 데이터 검증"""
    print("🔍 추가된 데이터 검증 중...")
    
    client = VectorDBClient()
    
    # 키워드 검증
    print("\n1. 키워드 데이터 검증:")
    try:
        keywords = client.get_current_keywords("006800")
        if keywords:
            print(f"   ✅ 키워드 조회 성공: {keywords}")
        else:
            print("   ❌ 키워드 조회 결과 없음")
    except Exception as e:
        print(f"   ❌ 키워드 조회 실패: {e}")
    
    # 과거 사건 검증
    print("\n2. 과거 사건 데이터 검증:")
    try:
        past_events = client.search_past_events("실적 발표", "006800", top_k=3)
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
        print(f"   ❌ 과거 사건 검색 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 미래에셋증권 크로마 DB 데이터 추가 시작")
    print("=" * 60)
    
    # 시작 전 상태 확인
    print("📋 시작 전 상태:")
    initial_stats = check_collections_status()
    print("\n" + "=" * 60)
    
    # 키워드 추가
    keyword_result = add_mirae_asset_keywords()
    print()
    
    # 과거 사건 추가
    events_result = add_mirae_asset_past_events()
    print()
    
    # 완료 후 상태 확인
    print("=" * 60)
    print("📋 완료 후 상태:")
    final_stats = check_collections_status()
    print()
    
    # 추가된 데이터 검증
    print("=" * 60)
    verify_added_data()
    print()
    
    # 결과 요약
    print("=" * 60)
    print("🎉 미래에셋증권 데이터 추가 완료!")
    print(f"   📊 키워드 추가: {'성공' if keyword_result else '실패'}")
    print(f"   📚 과거 사건 추가: {len(events_result) if events_result else 0}/8개")
    print()
    print("📈 컬렉션 변화:")
    initial_keywords = initial_stats.get('keywords', {}).get('count', 0)
    final_keywords = final_stats.get('keywords', {}).get('count', 0)
    initial_past_events = initial_stats.get('past_events', {}).get('count', 0)
    final_past_events = final_stats.get('past_events', {}).get('count', 0)
    
    print(f"   • keywords: {initial_keywords} → {final_keywords} (+{final_keywords - initial_keywords})")
    print(f"   • past_events: {initial_past_events} → {final_past_events} (+{final_past_events - initial_past_events})")
    print()
    print("✨ 데이터가 성공적으로 추가되었습니다!")

if __name__ == "__main__":
    main() 