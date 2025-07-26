"""
벡터 데이터베이스 클라이언트 모듈
ChromaDB + FAISS를 활용한 뉴스, 키워드, 과거 사례 벡터 저장 및 검색 기능 제공
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, date, timedelta
import os
from sentence_transformers import SentenceTransformer
from config.env_local import get_env_var

# 로깅 설정
logger = logging.getLogger(__name__)


class VectorDBClient:
    """벡터 데이터베이스 클라이언트 클래스"""

    def __init__(self):
        """ChromaDB 클라이언트 및 임베딩 모델 초기화"""
        self.client: Optional[Any] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.embedding_function: Optional[Any] = None
        self.collections: Dict[str, Any] = {}
        self._initialize_client()
        self._initialize_embedding_model()
        self._initialize_collections()

    def _initialize_client(self) -> None:
        """ChromaDB 클라이언트 초기화"""
        try:
            persist_directory = get_env_var(
                "CHROMADB_PERSIST_DIRECTORY", "./data/chroma"
            )

            # 디렉토리 생성
            os.makedirs(persist_directory, exist_ok=True)

            # ChromaDB 클라이언트 생성
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            logger.info(f"ChromaDB 클라이언트 초기화 완료: {persist_directory}")

        except Exception as e:
            logger.error(f"ChromaDB 클라이언트 초기화 실패: {e}")
            raise

    def _initialize_embedding_model(self) -> None:
        """임베딩 모델 초기화"""
        try:
            model_name = get_env_var("EMBEDDING_MODEL_NAME", "jhgan/ko-sbert-nli")
            device = get_env_var("EMBEDDING_MODEL_DEVICE", "cpu")

            # SentenceTransformer 모델 로드
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_model.to(device)

            # ChromaDB 임베딩 함수 생성
            self.embedding_function = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name, device=device
                )
            )

            logger.info(f"임베딩 모델 초기화 완료: {model_name} ({device})")

        except Exception as e:
            logger.error(f"임베딩 모델 초기화 실패: {e}")
            raise

    def _initialize_collections(self) -> None:
        """벡터 컬렉션 초기화"""
        collection_configs = {
            "high_impact_news": {
                "name": get_env_var("VECTOR_DB_HIGH_IMPACT_NEWS", "high_impact_news"),
                "description": "고영향 뉴스 벡터 저장소 (영향력 0.7 이상)",
            },
            "past_events": {
                "name": get_env_var("VECTOR_DB_PAST_EVENTS", "past_events"),
                "description": "과거 중요 사건 벡터 저장소 (10% 등락 또는 1000만주 이상)",
            },
            "daily_news": {
                "name": get_env_var("VECTOR_DB_DAILY_NEWS", "daily_news"),
                "description": "일일 뉴스 임시 저장소 (매일 자정 삭제)",
            },
            "keywords": {
                "name": get_env_var("VECTOR_DB_KEYWORDS", "keywords"),
                "description": "주간 핵심 키워드 저장소",
            },
        }

        try:
            if not self.client:
                raise Exception("ChromaDB 클라이언트가 초기화되지 않았습니다.")
                
            for key, config in collection_configs.items():
                # 메타데이터 기본값 설정 (빈 메타데이터 방지)
                metadata = {
                    "description": config["description"],
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "type": key
                }
                
                collection = self.client.get_or_create_collection(
                    name=config["name"],
                    embedding_function=self.embedding_function,
                    metadata=metadata,
                )
                self.collections[key] = collection
                logger.info(f"컬렉션 초기화 완료: {config['name']}")

        except Exception as e:
            logger.error(f"컬렉션 초기화 실패: {e}")
            raise

    def add_high_impact_news(self, news_data: Dict) -> str:
        """고영향 뉴스 추가"""
        try:
            # 🔧 중복 체크: 같은 제목의 뉴스가 이미 저장되어 있는지 확인
            existing_news = self.collections["high_impact_news"].get(
                where={"title": news_data["title"]},
                limit=1
            )
            
            if existing_news and len(existing_news['ids']) > 0:
                logger.warning(f"중복 뉴스 발견 - 저장 건너뜀: {news_data['title'][:50]}...")
                return existing_news['ids'][0]  # 기존 ID 반환
            
            # 🔧 중복 ID 문제 해결: 마이크로초 + 뉴스 제목 해시값 추가
            import hashlib
            import time
            
            # 현재 시간 + 마이크로초 + 뉴스 제목 해시값으로 고유 ID 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            microseconds = int(time.time() * 1000000) % 1000000  # 마이크로초 6자리
            title_hash = hashlib.md5(news_data['title'].encode('utf-8')).hexdigest()[:8]
            
            news_id = f"news_{news_data['stock_code']}_{timestamp}_{microseconds:06d}_{title_hash}"

            # 임베딩할 텍스트 생성
            text = f"{news_data['title']} {news_data.get('summary', '')}"

            # 메타데이터 생성
            metadata = {
                "stock_code": news_data["stock_code"],
                "stock_name": news_data["stock_name"],
                "title": news_data["title"],
                "impact_score": news_data["impact_score"],
                "publication_date": (
                    news_data["publication_date"].isoformat()
                    if isinstance(news_data["publication_date"], date)
                    else str(news_data["publication_date"])
                ),
                "created_at": datetime.now().isoformat(),
                "type": "high_impact_news",
            }

            # 컬렉션에 추가
            self.collections["high_impact_news"].add(
                documents=[text], metadatas=[metadata], ids=[news_id]
            )

            logger.info(f"고영향 뉴스 추가 완료: {news_id}")
            return news_id

        except Exception as e:
            logger.error(f"고영향 뉴스 추가 실패: {e}")
            raise

    def add_past_event(self, event_data: Dict) -> str:
        """과거 중요 사건 추가"""
        try:
            # 🔧 중복 체크: 같은 제목의 이벤트가 이미 저장되어 있는지 확인
            title = event_data.get('title', event_data['event_type'])
            existing_event = self.collections["past_events"].get(
                where={"title": title},
                limit=1
            )
            
            if existing_event and len(existing_event['ids']) > 0:
                logger.warning(f"중복 과거 이벤트 발견 - 저장 건너뜀: {title[:50]}...")
                return existing_event['ids'][0]  # 기존 ID 반환
            
            # 🔧 고유 ID 생성 (중복 방지)
            import hashlib
            import time
            
            timestamp = event_data['event_date'].strftime('%Y%m%d_%H%M%S')
            microseconds = int(time.time() * 1000000) % 1000000
            title_hash = hashlib.md5(title[:50].encode('utf-8')).hexdigest()[:6]
            
            event_id = f"event_{event_data['stock_code']}_{timestamp}_{microseconds:06d}_{title_hash}"

            # 임베딩할 텍스트 생성 (제목과 본문 모두 포함)
            description = event_data.get('description', '')
            text = f"{title} {description}"

            # 메타데이터 생성 (제목 필드 추가)
            metadata = {
                "stock_code": event_data["stock_code"],
                "stock_name": event_data["stock_name"],
                "title": title,  # 제목 필드 추가
                "event_type": event_data["event_type"],
                "event_date": event_data["event_date"].isoformat(),
                "price_change": event_data["price_change"],
                "volume": event_data["volume"],
                "description": description,
                "created_at": datetime.now().isoformat(),
                "type": "past_event",
            }

            # 컬렉션에 추가
            self.collections["past_events"].add(
                documents=[text], metadatas=[metadata], ids=[event_id]
            )

            logger.info(f"과거 사건 추가 완료: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"과거 사건 추가 실패: {e}")
            raise

    def add_daily_news(self, news_data: Dict) -> str:
        """일일 뉴스 추가"""
        try:
            # 🔧 중복 체크: 같은 제목의 뉴스가 이미 저장되어 있는지 확인
            existing_news = self.collections["daily_news"].get(
                where={"title": news_data["title"]},
                limit=1
            )
            
            if existing_news and len(existing_news['ids']) > 0:
                logger.warning(f"중복 일일 뉴스 발견 - 저장 건너뜀: {news_data['title'][:50]}...")
                return existing_news['ids'][0]  # 기존 ID 반환
            
            # 🔧 중복 ID 문제 해결: 마이크로초 + 뉴스 제목 해시값 추가
            import hashlib
            import time
            
            # 현재 시간 + 마이크로초 + 뉴스 제목 해시값으로 고유 ID 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            microseconds = int(time.time() * 1000000) % 1000000  # 마이크로초 6자리
            title_hash = hashlib.md5(news_data['title'].encode('utf-8')).hexdigest()[:8]
            
            news_id = f"daily_{news_data['stock_code']}_{timestamp}_{microseconds:06d}_{title_hash}"

            # 임베딩할 텍스트 생성
            text = f"{news_data['title']} {news_data.get('content', '')[:500]}"

            # 메타데이터 생성
            metadata = {
                "stock_code": news_data["stock_code"],
                "stock_name": news_data["stock_name"],
                "title": news_data["title"],
                "url": news_data.get("url", ""),
                "publication_date": (
                    news_data["publication_date"].isoformat()
                    if isinstance(news_data["publication_date"], date)
                    else str(news_data["publication_date"])
                ),
                "created_at": datetime.now().isoformat(),
                "type": "daily_news",
            }

            # 컬렉션에 추가
            self.collections["daily_news"].add(
                documents=[text], metadatas=[metadata], ids=[news_id]
            )

            logger.info(f"일일 뉴스 추가 완료: {news_id}")
            return news_id

        except Exception as e:
            logger.error(f"일일 뉴스 추가 실패: {e}")
            raise

    def add_keywords(self, keyword_data: Dict) -> str:
        """핵심 키워드 추가"""
        try:
            import json
            import hashlib
            import time
            
            # 🔧 중복 체크: 같은 주차의 키워드가 이미 저장되어 있는지 확인
            week_start_str = keyword_data["week_start"].isoformat()
            
            # ChromaDB의 올바른 where 조건 문법 사용
            existing_keywords = self.collections["keywords"].get(
                where={
                    "$and": [
                        {"stock_code": {"$eq": keyword_data["stock_code"]}},
                        {"week_start": {"$eq": week_start_str}}
                    ]
                },
                limit=1
            )
            
            if existing_keywords and len(existing_keywords['ids']) > 0:
                logger.warning(f"중복 키워드 발견 - 저장 건너뜀: {keyword_data['stock_code']} {week_start_str}")
                return existing_keywords['ids'][0]  # 기존 ID 반환
            
            # 고유 ID 생성 (중복 방지)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            microseconds = int(time.time() * 1000000) % 1000000
            keywords_hash = hashlib.md5(",".join(keyword_data["keywords"]).encode('utf-8')).hexdigest()[:6]
            
            keyword_id = f"keyword_{keyword_data['stock_code']}_{timestamp}_{microseconds:06d}_{keywords_hash}"

            # 임베딩할 텍스트 생성
            text = " ".join(keyword_data["keywords"])

            # 메타데이터 생성 (리스트를 JSON 문자열로 변환)
            metadata = {
                "stock_code": keyword_data["stock_code"],
                "stock_name": keyword_data["stock_name"],
                "keywords_json": json.dumps(keyword_data["keywords"], ensure_ascii=False),  # JSON 문자열로 저장
                "keywords_text": ", ".join(keyword_data["keywords"]),  # 쉼표로 구분된 문자열로도 저장
                "keywords_count": len(keyword_data["keywords"]),  # 키워드 개수
                "week_start": week_start_str,
                "week_end": keyword_data["week_end"].isoformat(),
                "importance_scores_json": json.dumps(keyword_data.get("importance_scores", []), ensure_ascii=False),  # JSON 문자열로 저장
                "created_at": datetime.now().isoformat(),
                "type": "keywords",
            }

            # 컬렉션에 추가
            self.collections["keywords"].add(
                documents=[text], metadatas=[metadata], ids=[keyword_id]
            )

            logger.info(f"핵심 키워드 추가 완료: {keyword_id}")
            return keyword_id

        except Exception as e:
            logger.error(f"핵심 키워드 추가 실패: {e}")
            raise

    def search_similar_news(
        self, query_text: str, stock_code: str, top_k: int = 5, threshold: float = 0.7
    ) -> List[Dict]:
        """유사 뉴스 검색"""
        try:
            # 고영향 뉴스에서 검색
            results = self.collections["high_impact_news"].query(
                query_texts=[query_text],
                n_results=top_k,
                where={"stock_code": stock_code},
                include=["documents", "metadatas", "distances"],
            )

            # 결과 포맷팅
            similar_news = []
            if results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(
                    zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    )
                ):
                    # 유사도 계산 (거리를 유사도로 변환)
                    similarity = 1 - distance

                    if similarity >= threshold:
                        similar_news.append(
                            {
                                "document": doc,
                                "metadata": metadata,
                                "similarity": similarity,
                                "rank": i + 1,
                            }
                        )

            logger.info(f"유사 뉴스 검색 완료: {len(similar_news)}개 발견")
            return similar_news

        except Exception as e:
            logger.error(f"유사 뉴스 검색 실패: {e}")
            return []

    def search_past_events(
        self, query_text: str, stock_code: str, top_k: int = 3
    ) -> List[Dict]:
        """과거 유사 사건 검색"""
        try:
            results = self.collections["past_events"].query(
                query_texts=[query_text],
                n_results=top_k,
                where={"stock_code": stock_code},
                include=["documents", "metadatas", "distances"],
            )

            # 결과 포맷팅
            past_events = []
            if results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(
                    zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    )
                ):
                    similarity = 1 - distance
                    past_events.append(
                        {
                            "document": doc,
                            "metadata": metadata,
                            "similarity": similarity,
                            "rank": i + 1,
                        }
                    )

            logger.info(f"과거 사건 검색 완료: {len(past_events)}개 발견")
            return past_events

        except Exception as e:
            logger.error(f"과거 사건 검색 실패: {e}")
            return []

    def get_current_keywords(self, stock_code: str) -> List[str]:
        """현재 주간 핵심 키워드 조회"""
        try:
            import json
            
            # 최근 1주일 이내 키워드 검색 (단순 종목 코드로만 검색)
            results = self.collections["keywords"].query(
                query_texts=[""],
                n_results=5,  # 더 많은 결과 조회
                where={"stock_code": stock_code},
                include=["metadatas"],
            )

            # 결과가 있는지 확인
            if results["metadatas"] and results["metadatas"][0]:
                for metadata in results["metadatas"][0]:
                    try:
                        # JSON 형식으로 저장된 키워드 파싱
                        keywords_json = metadata.get("keywords_json", "[]")
                        keywords = json.loads(keywords_json)
                        
                        if keywords:  # 빈 리스트가 아닌 경우
                            logger.info(f"현재 키워드 조회 완료: {len(keywords)}개 - {keywords}")
                            return keywords
                            
                    except (json.JSONDecodeError, ValueError) as parse_error:
                        logger.warning(f"키워드 JSON 파싱 실패: {parse_error}")
                        # 백업: 텍스트 형식으로 저장된 키워드 사용
                        keywords_text = metadata.get("keywords_text", "")
                        if keywords_text:
                            keywords = [k.strip() for k in keywords_text.split(",")]
                            logger.info(f"백업 키워드 조회 완료: {len(keywords)}개 - {keywords}")
                            return keywords
                        continue

            logger.warning(f"종목 {stock_code}에 대한 키워드를 찾을 수 없습니다.")
            return []

        except Exception as e:
            logger.error(f"현재 키워드 조회 실패: {e}")
            return []

    def cleanup_daily_news(self) -> int:
        """일일 뉴스 정리 (매일 자정 실행)"""
        try:
            # 어제 이전 데이터 삭제
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()

            # 전체 데이터 조회 (삭제할 데이터 찾기)
            results = self.collections["daily_news"].get(
                where={"created_at": {"$lt": yesterday}}, include=["metadatas"]
            )

            if results["ids"]:
                # 일괄 삭제
                self.collections["daily_news"].delete(ids=results["ids"])
                deleted_count = len(results["ids"])
                logger.info(f"일일 뉴스 정리 완료: {deleted_count}개 삭제")
                return deleted_count

            return 0

        except Exception as e:
            logger.error(f"일일 뉴스 정리 실패: {e}")
            return 0

    def get_collection_stats(self) -> Dict:
        """컬렉션 통계 조회"""
        try:
            stats = {}
            for key, collection in self.collections.items():
                count = collection.count()
                stats[key] = {"count": count, "collection_name": collection.name}

            logger.info("컬렉션 통계 조회 완료")
            return stats

        except Exception as e:
            logger.error(f"컬렉션 통계 조회 실패: {e}")
            return {}

    def collection_exists(self, collection_name: str) -> bool:
        """컬렉션 존재 여부 확인"""
        try:
            if not self.client:
                return False
            collections = self.client.list_collections()
            return any(collection.name == collection_name for collection in collections)
        except Exception as e:
            logger.error(f"컬렉션 존재 여부 확인 실패: {e}")
            return False

    def create_collection(self, collection_name: str, description: Optional[str] = None) -> bool:
        """새로운 컬렉션 생성"""
        try:
            if not self.client:
                logger.error("ChromaDB 클라이언트가 초기화되지 않았습니다.")
                return False
                
            # 메타데이터 기본값 설정 (빈 메타데이터 방지)
            metadata = {
                "description": description or f"Collection for {collection_name}",
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }

            collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata=metadata,
            )

            logger.info(f"컬렉션 생성 완료: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"컬렉션 생성 실패 ({collection_name}): {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """컬렉션 삭제"""
        try:
            if not self.client:
                logger.error("ChromaDB 클라이언트가 초기화되지 않았습니다.")
                return False
            self.client.delete_collection(name=collection_name)
            logger.info(f"컬렉션 삭제 완료: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"컬렉션 삭제 실패 ({collection_name}): {e}")
            return False

    def health_check(self) -> Dict:
        """벡터 DB 상태 확인"""
        try:
            # 모든 컬렉션 상태 확인
            collections_status = {}
            for key, collection in self.collections.items():
                try:
                    count = collection.count()
                    collections_status[key] = {"status": "healthy", "count": count}
                except Exception as e:
                    collections_status[key] = {"status": "unhealthy", "error": str(e)}

            # 임베딩 모델 상태 확인
            embedding_status = "healthy"
            try:
                if self.embedding_model:
                    test_embedding = self.embedding_model.encode(["테스트"])
                    if len(test_embedding) == 0:
                        embedding_status = "unhealthy"
                else:
                    embedding_status = "unhealthy"
            except Exception:
                embedding_status = "unhealthy"

            return {
                "status": "healthy",
                "collections": collections_status,
                "embedding_model": embedding_status,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"벡터 DB 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


    def search_similar_documents(self, query: str, collection_name: str = "high_impact_news", top_k: int = 5) -> List[Dict]:
        """유사 문서 검색 (일반용)"""
        try:
            if collection_name in self.collections:
                collection = self.collections[collection_name]
                results = collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    include=['documents', 'metadatas', 'distances']
                )
                
                # 결과 포맷팅
                formatted_results = []
                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        formatted_results.append({
                            'document': doc,
                            'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                            'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0
                        })
                
                return formatted_results
            else:
                logger.warning(f"컬렉션 '{collection_name}'을 찾을 수 없습니다.")
                return []
                
        except Exception as e:
            logger.error(f"유사 문서 검색 실패: {e}")
            return []

    def add_documents(self, documents: List[str], metadatas: List[Dict], collection_name: str = "high_impact_news", ids: Optional[List[str]] = None) -> bool:
        """문서 추가 (일반용)"""
        try:
            if collection_name in self.collections:
                collection = self.collections[collection_name]
                
                # ID 생성 (제공되지 않은 경우)
                if ids is None:
                    ids = [f"doc_{collection_name}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}" for i in range(len(documents))]
                
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"문서 {len(documents)}개를 컬렉션 '{collection_name}'에 추가했습니다.")
                return True
            else:
                logger.error(f"컬렉션 '{collection_name}'을 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            logger.error(f"문서 추가 실패: {e}")
            return False

    def add_document(self, document: str, metadata: Dict, collection_name: str = "high_impact_news", doc_id: Optional[str] = None) -> bool:
        """단일 문서 추가"""
        try:
            if doc_id is None:
                doc_id = f"doc_{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return self.add_documents([document], [metadata], collection_name, [doc_id])
        except Exception as e:
            logger.error(f"단일 문서 추가 실패: {e}")
            return False
    
    def get_all_documents(self, collection_name: str, limit: int = 100) -> List[Dict]:
        """컬렉션의 모든 문서 조회"""
        try:
            # 컬렉션 이름 매핑
            collection_map = {
                "high_impact_news": "high_impact_news",
                "past_events": "past_events", 
                "daily_news": "daily_news",
                "weekly_keywords": "keywords",
                "keywords": "keywords"
            }
            
            mapped_name = collection_map.get(collection_name, collection_name)
            
            if mapped_name not in self.collections:
                logger.warning(f"컬렉션 '{collection_name}'을 찾을 수 없습니다.")
                return []
            
            collection = self.collections[mapped_name]
            
            # ChromaDB에서 전체 문서 조회 (get 메소드 사용)
            results = collection.get(
                limit=limit,
                include=['documents', 'metadatas']
            )
            
            documents = []
            for i in range(len(results['ids'])):
                doc_data = {
                    'id': results['ids'][i],
                    'document': results['documents'][i] if 'documents' in results and i < len(results['documents']) else '',
                    'metadata': results['metadatas'][i] if 'metadatas' in results and i < len(results['metadatas']) else {}
                }
                documents.append(doc_data)
            
            logger.info(f"컬렉션 '{collection_name}'에서 {len(documents)}개 문서 조회 완료")
            return documents
            
        except Exception as e:
            logger.error(f"전체 문서 조회 실패: {e}")
            return []

    def encode(self, texts: List[str]) -> List[List[float]]:
        """텍스트 인코딩 (임베딩 생성)"""
        try:
            if not self.embedding_model:
                logger.error("임베딩 모델이 초기화되지 않았습니다.")
                return []
                
            embeddings = self.embedding_model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"텍스트 인코딩 실패: {e}")
            return []

    def close(self) -> None:
        """Vector DB 클라이언트 정리"""
        try:
            if self.client:
                logger.info("Vector DB 클라이언트 정리 중...")
                self.client = None
                self.collections = {}
                logger.info("Vector DB 클라이언트 정리 완료")
        except Exception as e:
            logger.error(f"Vector DB 클라이언트 정리 중 오류: {e}")


# 전역 벡터 DB 클라이언트 인스턴스
vector_db_client = VectorDBClient()
