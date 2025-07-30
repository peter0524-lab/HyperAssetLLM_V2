"""
ChromaDB 설정 파일
프로덕션 환경에서 ChromaDB 사용을 위한 설정
"""

import chromadb
from chromadb.config import Settings
import os
from typing import Optional

def get_chromadb_client(persist_directory: Optional[str] = None):
    """
    환경에 따른 ChromaDB 클라이언트 반환
    
    Args:
        persist_directory: ChromaDB 데이터 저장 디렉토리
        
    Returns:
        chromadb.Client: ChromaDB 클라이언트 인스턴스
    """
    
    # 환경 확인
    env = os.getenv('ENV', 'development')
    
    if env == 'production':
        # 프로덕션 환경: 임시 디렉토리 사용
        persist_dir = persist_directory or "/tmp/chroma"
        
        # 임시 디렉토리 생성
        os.makedirs(persist_dir, exist_ok=True)
        
        return chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir,
            anonymized_telemetry=False  # 텔레메트리 비활성화
        ))
    else:
        # 개발 환경: 로컬 디렉토리 사용
        persist_dir = persist_directory or "./data/chroma"
        
        # 로컬 디렉토리 생성
        os.makedirs(persist_dir, exist_ok=True)
        
        return chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir,
            anonymized_telemetry=False
        ))

def get_collection_names():
    """
    ChromaDB 컬렉션 이름 목록 반환
    
    Returns:
        dict: 컬렉션 이름 매핑
    """
    return {
        "high_impact_news": "high_impact_news",
        "past_events": "past_events", 
        "daily_news": "daily_news",
        "keywords": "keywords",
        "disclosure": "disclosure",
        "report": "report"
    }

def initialize_collections(client):
    """
    ChromaDB 컬렉션 초기화
    
    Args:
        client: ChromaDB 클라이언트
    """
    collection_names = get_collection_names()
    
    for collection_name in collection_names.values():
        try:
            # 컬렉션이 없으면 생성
            client.get_or_create_collection(name=collection_name)
        except Exception as e:
            print(f"컬렉션 {collection_name} 초기화 실패: {e}")

def cleanup_temp_data():
    """
    프로덕션 환경에서 임시 ChromaDB 데이터 정리
    """
    if os.getenv('ENV') == 'production':
        import shutil
        temp_dir = "/tmp/chroma"
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print("임시 ChromaDB 데이터 정리 완료")
            except Exception as e:
                print(f"임시 데이터 정리 실패: {e}")

# 사용 예시
if __name__ == "__main__":
    # 클라이언트 생성
    client = get_chromadb_client()
    
    # 컬렉션 초기화
    initialize_collections(client)
    
    print("ChromaDB 설정 완료") 