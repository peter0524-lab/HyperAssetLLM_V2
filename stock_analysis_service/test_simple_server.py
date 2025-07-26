#!/usr/bin/env python3
"""
간단한 테스트용 FastAPI 서버
API Gateway 연결 테스트용
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Test Server", version="1.0.0")

# CORS 설정 (개발 모드)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Test Server is running!", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "test_server"}

@app.get("/api/test")
async def test_api():
    return {"message": "API test successful", "data": {"test": True}}

if __name__ == "__main__":
    print("🚀 테스트 서버 시작 (포트: 8080)")
    uvicorn.run(app, host="0.0.0.0", port=8080) 