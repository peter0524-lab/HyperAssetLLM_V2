#!/usr/bin/env python3
"""
ChromaDB 시각화 대시보드
MySQL Workbench와 같은 기능을 제공하는 웹 인터페이스
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from shared.database.vector_db import VectorDBClient
from typing import Dict, List, Optional
import logging
import json
from datetime import datetime
import uvicorn
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="ChromaDB Dashboard",
    description="ChromaDB 데이터 시각화 대시보드",
    version="1.0.0"
)

# 템플릿 및 정적 파일 설정
templates_dir = "templates"
static_dir = "static"

os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ChromaDB 클라이언트
vector_db = None

def get_vector_db():
    """VectorDB 클라이언트 인스턴스 반환"""
    global vector_db
    if vector_db is None:
        # 뉴스 서비스가 사용하는 크로마 DB 경로 설정
        news_service_chroma_path = os.path.join(os.getcwd(), "services", "news_service", "data", "chroma")
        os.environ["CHROMADB_PERSIST_DIRECTORY"] = news_service_chroma_path
        vector_db = VectorDBClient()
    return vector_db

@app.on_event("startup")
async def startup_event():
    """앱 시작시 ChromaDB 초기화"""
    try:
        get_vector_db()
        logger.info("ChromaDB 대시보드 시작 완료")
    except Exception as e:
        logger.error(f"ChromaDB 대시보드 시작 실패: {e}")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """대시보드 홈페이지"""
    try:
        db = get_vector_db()
        
        # 컬렉션 통계 가져오기
        stats = db.get_collection_stats()
        health = db.health_check()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "stats": stats,
            "health": health,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"대시보드 홈 로딩 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collections")
async def get_collections():
    """컬렉션 목록 API"""
    try:
        db = get_vector_db()
        stats = db.get_collection_stats()
        
        collections = []
        for name, stat in stats.items():
            if isinstance(stat, dict):
                collections.append({
                    "name": name,
                    "count": stat.get("count", 0),
                    "collection_name": stat.get("collection_name", name)
                })
            else:
                collections.append({
                    "name": name,
                    "count": stat,
                    "collection_name": name
                })
        
        return {"collections": collections}
    except Exception as e:
        logger.error(f"컬렉션 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collections/{collection_name}/documents")
async def get_collection_documents(collection_name: str, limit: int = 50, offset: int = 0):
    """컬렉션 문서 목록 API"""
    try:
        db = get_vector_db()
        
        # ChromaDB에서 전체 문서 조회 (get_all_documents 사용)
        results = db.get_all_documents(collection_name, limit=limit+offset)
        
        documents = []
        for i, result in enumerate(results):
            if i < offset:
                continue
            if len(documents) >= limit:
                break
                
            documents.append({
                "id": result.get("id", f"doc_{i}"),
                "metadata": result.get("metadata", {}),
                "document": result.get("document", ""),
                "distance": result.get("distance", 0.0)
            })
        
        return {
            "documents": documents,
            "total": len(results),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"문서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search_documents(
    collection_name: str = Form(...),
    query: str = Form(""),
    top_k: int = Form(10)
):
    """문서 검색 API"""
    try:
        db = get_vector_db()
        
        # 빈 검색어인 경우 전체 문서 조회
        if not query.strip():
            results = db.get_all_documents(collection_name, limit=top_k)
            # 결과 형태를 search_similar_documents와 동일하게 맞춤
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "id": doc["id"],
                    "document": doc["document"],
                    "metadata": doc["metadata"],
                    "distance": 0.0,  # 검색이 아니므로 거리는 0
                    "score": 1.0     # 유사도 점수 1.0
                })
            
            return {
                "query": "(전체 문서 조회)",
                "collection": collection_name,
                "results": formatted_results,
                "count": len(formatted_results),
                "is_full_list": True
            }
        
        # 일반 검색
        results = db.search_similar_documents(
            query=query,
            collection_name=collection_name,
            top_k=top_k
        )
        
        return {
            "query": query,
            "collection": collection_name,
            "results": results,
            "count": len(results),
            "is_full_list": False
        }
    except Exception as e:
        logger.error(f"문서 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """시스템 상태 확인 API"""
    try:
        db = get_vector_db()
        health = db.health_check()
        return health
    except Exception as e:
        logger.error(f"상태 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collection/{collection_name}", response_class=HTMLResponse)
async def collection_detail(request: Request, collection_name: str):
    """컬렉션 상세 페이지"""
    try:
        db = get_vector_db()
        stats = db.get_collection_stats()
        
        collection_info = stats.get(collection_name, {})
        
        return templates.TemplateResponse("collection.html", {
            "request": request,
            "collection_name": collection_name,
            "collection_info": collection_info,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"컬렉션 상세 페이지 로딩 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """검색 페이지"""
    try:
        db = get_vector_db()
        stats = db.get_collection_stats()
        
        collections = list(stats.keys())
        
        return templates.TemplateResponse("search.html", {
            "request": request,
            "collections": collections,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"검색 페이지 로딩 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """대시보드 실행"""
    print("🚀 ChromaDB 대시보드 시작")
    print("📊 대시보드 URL: http://localhost:8080")
    print("🔍 검색 페이지: http://localhost:8080/search")
    print("📈 컬렉션 상세: http://localhost:8080/collection/{collection_name}")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main() 