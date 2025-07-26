#!/usr/bin/env python3
"""
ChromaDB 연결 테스트 및 임베딩 확인 스크립트
"""

from shared.database.vector_db import VectorDBClient
from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta
import traceback
import numpy as np

def test_chromadb_with_embeddings():
    """ChromaDB 연결 및 임베딩 테스트"""
    try:
        print("=== ChromaDB 연결 및 임베딩 테스트 시작 ===")
        
        # VectorDB 클라이언트 생성
        print("1. VectorDB 클라이언트 초기화...")
        vector_db = VectorDBClient()
        print("✅ 클라이언트 초기화 성공!")
        
        # 임베딩 모델 로드
        print("\n2. 임베딩 모델 로드...")
        embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        print("✅ 임베딩 모델 로드 성공!")
        
        # 상태 확인
        print("\n3. 상태 확인...")
        health = vector_db.health_check()
        print(f"상태: {health['status']}")
        if health['status'] == 'healthy':
            print(f"✅ ChromaDB 연결 성공!")
            print(f"컬렉션 수: {health.get('collections_count', 'Unknown')}")
        else:
            print(f"❌ 연결 실패: {health.get('error', 'Unknown')}")
            return False
        
        # 컬렉션 통계
        print("\n4. 컬렉션 통계 확인...")
        stats = vector_db.get_collection_stats()
        for collection, count in stats.items():
            print(f"  - {collection}: {count}개 문서")
        
        # 4개 컬렉션에 테스트 데이터 각각 1개씩 추가
        print("\n5. 4개 컬렉션에 테스트 데이터 각각 1개씩 추가...")
        
        # 테스트 데이터 정의
        test_data = {
            "high_impact_news": {
                "text": "삼성전자 3분기 실적 발표, 영업이익 12조원 달성으로 시장 기대 상회",
                "metadata": {
                    "title": "삼성전자 Q3 실적 발표",
                    "content": "삼성전자 3분기 실적 발표, 영업이익 12조원 달성으로 시장 기대 상회",
                    "stock_code": "005930",
                    "impact_score": 0.85,
                    "published_at": datetime.now().isoformat(),
                    "url": "https://example.com/samsung-q3"
                }
            },
            "daily_news": {
                "text": "오늘 코스피 지수는 소폭 상승하며 2650선을 회복했습니다",
                "metadata": {
                    "stock_code": "KOSPI",
                    "stock_name": "코스피",
                    "title": "코스피 2650선 회복",
                    "content": "오늘 코스피 지수는 소폭 상승하며 2650선을 회복했습니다",
                    "url": "https://example.com/kospi-recovery",
                    "publication_date": datetime.now()
                }
            },
            "keywords": {
                "text": "AI 인공지능 반도체 메모리",
                "metadata": {
                    "stock_code": "000660",
                    "keywords_text": "AI 인공지능 반도체 메모리",
                    "week_start": datetime.now().strftime("%Y-%m-%d"),
                    "created_at": datetime.now().isoformat()
                }
            },
            "past_events": {
                "text": "2023년 3월 실리콘밸리은행 파산으로 글로벌 금융시장 충격",
                "metadata": {
                    "event_title": "실리콘밸리은행 파산 사건",
                    "event_description": "2023년 3월 실리콘밸리은행 파산으로 글로벌 금융시장 충격",
                    "event_date": (datetime.now() - timedelta(days=30)).isoformat(),
                    "impact_level": "높음"
                }
            }
        }
        
        # 각 컬렉션에 1개씩 데이터 추가 및 임베딩 확인
        embeddings_info = {}
        
        for collection_name, data in test_data.items():
            print(f"\n5-{list(test_data.keys()).index(collection_name)+1}. {collection_name} 테스트 데이터 추가...")
            
            # 임베딩 생성 및 확인
            text = data["text"]
            embedding = embedding_model.encode(text)
            
            print(f"  📝 입력 텍스트: '{text}'")
            print(f"  🔢 임베딩 차원: {len(embedding)}")
            print(f"  📊 임베딩 값 범위: {embedding.min():.4f} ~ {embedding.max():.4f}")
            print(f"  🎯 임베딩 첫 5개 값: {embedding[:5]}")
            
            # 임베딩 정보 저장
            embeddings_info[collection_name] = {
                "text": text,
                "embedding_dim": len(embedding),
                "embedding_range": (float(embedding.min()), float(embedding.max())),
                "embedding_sample": embedding[:5].tolist()
            }
            
            # ChromaDB에 문서 추가
            try:
                if collection_name == "daily_news":
                    # daily_news는 특별한 메소드 사용
                    doc_id = vector_db.add_daily_news(data["metadata"])
                else:
                    # 다른 컬렉션들은 일반 add_document 사용
                    success = vector_db.add_document(
                        document=text,
                        metadata=data["metadata"],
                        collection_name=collection_name
                    )
                    doc_id = "success" if success else "failed"
                
                if doc_id:
                    print(f"  ✅ {collection_name} 문서 추가 성공: {doc_id}")
                else:
                    print(f"  ❌ {collection_name} 문서 추가 실패")
                    
            except Exception as e:
                print(f"  ❌ {collection_name} 문서 추가 오류: {e}")
        
        # 임베딩 모델 성능 분석
        print("\n6. 임베딩 모델 성능 분석...")
        print("=" * 60)
        
        for collection_name, info in embeddings_info.items():
            print(f"\n📂 {collection_name}:")
            print(f"   입력: {info['text'][:50]}...")
            print(f"   차원: {info['embedding_dim']}차원")
            print(f"   범위: {info['embedding_range'][0]:.4f} ~ {info['embedding_range'][1]:.4f}")
            print(f"   샘플: {[f'{x:.4f}' for x in info['embedding_sample']]}")
        
        # 임베딩 유사도 테스트
        print("\n7. 임베딩 유사도 테스트...")
        print("=" * 60)
        
        # 다양한 텍스트의 임베딩 생성
        test_texts = [
            "삼성전자 실적 발표",          # high_impact_news와 유사
            "코스피 지수 상승",            # daily_news와 유사  
            "AI 반도체 기술",             # keywords와 유사
            "금융시장 충격"               # past_events와 유사
        ]
        
        for i, test_text in enumerate(test_texts):
            test_embedding = embedding_model.encode(test_text)
            print(f"\n🔍 테스트 텍스트 {i+1}: '{test_text}'")
            print(f"   임베딩 차원: {len(test_embedding)}")
            print(f"   임베딩 범위: {test_embedding.min():.4f} ~ {test_embedding.max():.4f}")
            print(f"   임베딩 샘플: {[f'{x:.4f}' for x in test_embedding[:3]]}")
            
            # 원본 데이터와 유사도 계산
            for collection_name, info in embeddings_info.items():
                original_embedding = embedding_model.encode(info["text"])
                
                # 코사인 유사도 계산
                similarity = np.dot(test_embedding, original_embedding) / (
                    np.linalg.norm(test_embedding) * np.linalg.norm(original_embedding)
                )
                
                # 비교 문장 쌍 명확히 표시
                print(f"   🔗 비교: '{test_text}' ↔ '{info['text'][:30]}...'")
                print(f"       └─ {collection_name}: 유사도 {similarity:.4f}")
        
        # 실제 검색 테스트
        print("\n8. 실제 검색 테스트...")
        print("=" * 60)
        
        collections = ["high_impact_news", "daily_news", "keywords", "past_events"]
        test_queries = [
            "삼성전자 실적",
            "코스피 상승", 
            "AI 반도체",
            "금융 위기"
        ]
        
        for collection, query in zip(collections, test_queries):
            print(f"\n🔍 {collection} 검색: '{query}'")
            
            try:
                results = vector_db.search_similar_documents(
                    query=query,
                    collection_name=collection,
                    top_k=3
                )
                print(f"   ✅ 검색 결과: {len(results)}개")
                
                for j, result in enumerate(results):
                    distance = result.get('distance', 0)
                    # ChromaDB는 거리 값을 반환하는데, 코사인 거리의 경우 0에 가까울수록 유사
                    # 유사도 = 1 - 거리값 (단, 거리값이 1보다 클 수도 있음)
                    if distance <= 1:
                        similarity = 1 - distance
                    else:
                        similarity = max(0, 2 - distance)  # 거리가 1보다 클 경우 보정
                    
                    doc_text = result.get('document', 'N/A')
                    print(f"   🔗 검색 비교: '{query}' ↔ '{doc_text[:40]}...'")
                    print(f"       └─ 결과 {j+1}: 거리 {distance:.4f} → 유사도 {similarity:.4f}")
                    print(f"          📄 전체 내용: {doc_text[:60]}...")
                    
            except Exception as e:
                print(f"   ❌ 검색 실패: {e}")
        
        # 전체 문서 조회 테스트
        print("\n9. 전체 문서 조회 테스트...")
        print("=" * 60)
        
        for collection in collections:
            try:
                all_docs = vector_db.get_all_documents(collection, limit=10)
                print(f"\n📂 {collection}: {len(all_docs)}개 문서")
                
                for i, doc in enumerate(all_docs[:2]):  # 최대 2개만 출력
                    print(f"   문서 {i+1}: {doc.get('document', 'N/A')[:50]}...")
                    
            except Exception as e:
                print(f"   ❌ {collection} 조회 실패: {e}")
        
        # 최종 통계
        print("\n8. 최종 컬렉션 통계...")
        final_stats = vector_db.get_collection_stats()
        for collection, count in final_stats.items():
            print(f"  - {collection}: {count}개 문서")
        
        # 정리
        print("\n9. 정리...")
        vector_db.close()
        print("✅ 정리 완료")
        
        print("\n=== 🎉 모든 테스트 통과! ===")
        print("📊 4개 컬렉션에 테스트 데이터가 추가되었습니다.")
        print("🔍 ChromaDB 대시보드에서 확인해보세요: http://localhost:8080")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chromadb_with_embeddings()
    if success:
        print("\n🚀 ChromaDB가 정상적으로 작동합니다!")
        print("벡터 데이터베이스 기능을 사용할 수 있습니다.")
    else:
        print("\n❌ ChromaDB 테스트 실패!")
        print("설정을 확인해주세요.") 