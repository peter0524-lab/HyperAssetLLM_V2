"""
사용자 설정 API 서비스
프론트엔드에서 사용자 설정을 받아서 MySQL에 저장하는 API
"""

import logging
import sys
import os
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import MySQLClient
from shared.user_config.user_config_manager import user_config_manager
from user_models import (
    UserProfileCreate, UserProfileUpdate, UserStockCreate, UserStockUpdate,
    UserModelCreate, UserConfigResponse, ApiResponse, ModelType
)

# FastAPI 앱 생성
app = FastAPI(
    title="User Configuration Service",
    description="사용자 설정 관리 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

# MySQL 클라이언트
mysql_client = MySQLClient()

async def get_mysql_client():
    """MySQL 클라이언트 의존성"""
    return mysql_client

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 초기화"""
    try:
        # 사용자 설정 테이블 초기화
        await user_config_manager.initialize_tables()
        logger.info("✅ User Service 시작 완료")
    except Exception as e:
        logger.error(f"❌ User Service 시작 실패: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """서비스 종료 시 정리"""
    try:
        await user_config_manager.close()
        await mysql_client.close()
        logger.info("✅ User Service 종료 완료")
    except Exception as e:
        logger.error(f"❌ User Service 종료 실패: {e}")

# === 사용자 프로필 API ===

@app.post("/users/profile", response_model=ApiResponse)
async def create_user_profile(
    profile: UserProfileCreate,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 프로필 생성"""
    try:
        # 전화번호 중복 체크
        check_query = "SELECT user_id FROM user_profiles WHERE phone_number = %s"
        existing = await db.execute_query_async(check_query, (profile.phone_number,), fetch=True)
        
        if existing:
            raise HTTPException(status_code=400, detail="이미 등록된 전화번호입니다")
        
        # user_id 생성 (전화번호 기반으로 고유 ID 생성)
        import hashlib
        import time
        user_id = hashlib.md5(f"{profile.phone_number}_{int(time.time())}".encode()).hexdigest()[:20]
        
        # 프로필 생성
        insert_query = """
        INSERT INTO user_profiles (user_id, username, phone_number, news_similarity_threshold, news_impact_threshold)
        VALUES (%s, %s, %s, %s, %s)
        """
        await db.execute_query_async(
            insert_query,
            (user_id, profile.username, profile.phone_number, profile.news_similarity_threshold, profile.news_impact_threshold)
        )
        
        # 기본 모델 설정 생성
        model_query = "INSERT INTO user_model (user_id, model_type) VALUES (%s, %s)"
        await db.execute_query_async(model_query, (user_id, "hyperclova"))
        
        logger.info(f"✅ 사용자 프로필 생성 완료: {user_id}")
        
        return ApiResponse(
            success=True,
            message="사용자 프로필이 성공적으로 생성되었습니다",
            data={"user_id": user_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 프로필 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 프로필 생성에 실패했습니다")

@app.get("/users/{user_id}/profile", response_model=ApiResponse)
async def get_user_profile(
    user_id: str,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 프로필 조회"""
    try:
        query = """
        SELECT user_id, username, phone_number, news_similarity_threshold, news_impact_threshold
        FROM user_profiles WHERE user_id = %s
        """
        result = await db.execute_query_async(query, (user_id,), fetch=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        profile = result[0]
        return ApiResponse(
            success=True,
            message="사용자 프로필 조회 완료",
            data=profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 프로필 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 프로필 조회에 실패했습니다")

@app.put("/users/{user_id}/profile", response_model=ApiResponse)
async def update_user_profile(
    user_id: str,
    profile: UserProfileUpdate,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 프로필 수정"""
    try:
        # 기존 프로필 확인
        check_query = "SELECT user_id FROM user_profiles WHERE user_id = %s"
        existing = await db.execute_query_async(check_query, (user_id,), fetch=True)
        
        if not existing:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 전화번호 중복 체크 (다른 사용자와)
        if profile.phone_number:
            phone_check = "SELECT user_id FROM user_profiles WHERE phone_number = %s AND user_id != %s"
            phone_result = await db.execute_query_async(phone_check, (profile.phone_number, user_id), fetch=True)
            if phone_result:
                raise HTTPException(status_code=400, detail="이미 등록된 전화번호입니다")
        
        # 업데이트할 필드 구성
        update_fields = []
        update_values = []
        
        if profile.username is not None:
            update_fields.append("username = %s")
            update_values.append(profile.username)
        
        if profile.phone_number is not None:
            update_fields.append("phone_number = %s")
            update_values.append(profile.phone_number)
        
        if profile.news_similarity_threshold is not None:
            update_fields.append("news_similarity_threshold = %s")
            update_values.append(profile.news_similarity_threshold)
        
        if profile.news_impact_threshold is not None:
            update_fields.append("news_impact_threshold = %s")
            update_values.append(profile.news_impact_threshold)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")
        
        # 업데이트 실행
        update_query = f"UPDATE user_profiles SET {', '.join(update_fields)} WHERE user_id = %s"
        update_values.append(user_id)
        await db.execute_query_async(update_query, tuple(update_values))
        
        # 캐시 갱신
        await user_config_manager.update_user_cache(user_id)
        
        logger.info(f"✅ 사용자 프로필 수정 완료: {user_id}")
        
        return ApiResponse(
            success=True,
            message="사용자 프로필이 성공적으로 수정되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 프로필 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 프로필 수정에 실패했습니다")

# === 사용자 종목 API ===

@app.post("/users/{user_id}/stocks", response_model=ApiResponse)
async def add_user_stock(
    user_id: str,
    stock: UserStockCreate,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 종목 추가"""
    try:
        # 사용자 존재 확인
        user_check = "SELECT user_id FROM user_profiles WHERE user_id = %s"
        user_result = await db.execute_query_async(user_check, (user_id,), fetch=True)
        
        if not user_result:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 종목 중복 체크
        stock_check = "SELECT stock_code FROM user_stocks WHERE user_id = %s AND stock_code = %s"
        stock_result = await db.execute_query_async(stock_check, (user_id, stock.stock_code), fetch=True)
        
        if stock_result:
            raise HTTPException(status_code=400, detail="이미 등록된 종목입니다")
        
        # 종목 추가
        insert_query = """
        INSERT INTO user_stocks (user_id, stock_code, stock_name, enabled)
        VALUES (%s, %s, %s, %s)
        """
        await db.execute_query_async(
            insert_query,
            (user_id, stock.stock_code, stock.stock_name, stock.enabled)
        )
        
        # 캐시 갱신
        await user_config_manager.update_user_cache(user_id)
        
        logger.info(f"✅ 사용자 종목 추가 완료: {user_id} - {stock.stock_code}")
        
        return ApiResponse(
            success=True,
            message="종목이 성공적으로 추가되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 종목 추가 실패: {e}")
        raise HTTPException(status_code=500, detail="종목 추가에 실패했습니다")

@app.get("/users/{user_id}/stocks", response_model=ApiResponse)
async def get_user_stocks(
    user_id: str,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 종목 목록 조회"""
    try:
        query = """
        SELECT stock_code, stock_name, enabled
        FROM user_stocks 
        WHERE user_id = %s
        ORDER BY stock_code
        """
        result = await db.execute_query_async(query, (user_id,), fetch=True)
        
        return ApiResponse(
            success=True,
            message="사용자 종목 목록 조회 완료",
            data={"stocks": result}
        )
        
    except Exception as e:
        logger.error(f"❌ 사용자 종목 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="종목 목록 조회에 실패했습니다")

@app.put("/users/{user_id}/stocks/{stock_code}", response_model=ApiResponse)
async def update_user_stock(
    user_id: str,
    stock_code: str,
    stock: UserStockUpdate,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 종목 수정"""
    try:
        # 종목 존재 확인
        check_query = "SELECT stock_code FROM user_stocks WHERE user_id = %s AND stock_code = %s"
        existing = await db.execute_query_async(check_query, (user_id, stock_code), fetch=True)
        
        if not existing:
            raise HTTPException(status_code=404, detail="등록되지 않은 종목입니다")
        
        # 업데이트할 필드 구성
        update_fields = []
        update_values = []
        
        if stock.stock_name is not None:
            update_fields.append("stock_name = %s")
            update_values.append(stock.stock_name)
        
        if stock.enabled is not None:
            update_fields.append("enabled = %s")
            update_values.append(stock.enabled)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")
        
        # 업데이트 실행
        update_query = f"UPDATE user_stocks SET {', '.join(update_fields)} WHERE user_id = %s AND stock_code = %s"
        update_values.extend([user_id, stock_code])
        await db.execute_query_async(update_query, tuple(update_values))
        
        # 캐시 갱신
        await user_config_manager.update_user_cache(user_id)
        
        logger.info(f"✅ 사용자 종목 수정 완료: {user_id} - {stock_code}")
        
        return ApiResponse(
            success=True,
            message="종목이 성공적으로 수정되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 종목 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="종목 수정에 실패했습니다")

@app.delete("/users/{user_id}/stocks/{stock_code}", response_model=ApiResponse)
async def delete_user_stock(
    user_id: str,
    stock_code: str,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 종목 삭제"""
    try:
        # 종목 존재 확인
        check_query = "SELECT stock_code FROM user_stocks WHERE user_id = %s AND stock_code = %s"
        existing = await db.execute_query_async(check_query, (user_id, stock_code), fetch=True)
        
        if not existing:
            raise HTTPException(status_code=404, detail="등록되지 않은 종목입니다")
        
        # 종목 삭제
        delete_query = "DELETE FROM user_stocks WHERE user_id = %s AND stock_code = %s"
        await db.execute_query_async(delete_query, (user_id, stock_code))
        
        # 캐시 갱신
        await user_config_manager.update_user_cache(user_id)
        
        logger.info(f"✅ 사용자 종목 삭제 완료: {user_id} - {stock_code}")
        
        return ApiResponse(
            success=True,
            message="종목이 성공적으로 삭제되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 종목 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="종목 삭제에 실패했습니다")

# === 사용자 모델 API ===

@app.post("/users/{user_id}/model", response_model=ApiResponse)
async def set_user_model(
    user_id: str,
    model: UserModelCreate,
    db: MySQLClient = Depends(get_mysql_client)
):
    """사용자 모델 설정"""
    try:
        # 사용자 존재 확인
        user_check = "SELECT user_id FROM user_profiles WHERE user_id = %s"
        user_result = await db.execute_query_async(user_check, (user_id,), fetch=True)
        
        if not user_result:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 기존 모델 설정 확인
        model_check = "SELECT user_id FROM user_model WHERE user_id = %s"
        model_result = await db.execute_query_async(model_check, (user_id,), fetch=True)
        
        if model_result:
            # 기존 설정 업데이트
            update_query = "UPDATE user_model SET model_type = %s WHERE user_id = %s"
            await db.execute_query_async(update_query, (model.model_type.value, user_id))
        else:
            # 새 설정 생성
            insert_query = "INSERT INTO user_model (user_id, model_type) VALUES (%s, %s)"
            await db.execute_query_async(insert_query, (user_id, model.model_type.value))
        
        # 캐시 갱신
        await user_config_manager.update_user_cache(user_id)
        
        logger.info(f"✅ 사용자 모델 설정 완료: {user_id} - {model.model_type.value}")
        
        return ApiResponse(
            success=True,
            message="모델 설정이 성공적으로 저장되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 모델 설정 실패: {e}")
        raise HTTPException(status_code=500, detail="모델 설정에 실패했습니다")

# === 통합 설정 API ===

@app.get("/users/{user_id}/config", response_model=ApiResponse)
async def get_user_config(user_id: str):
    """사용자 전체 설정 조회"""
    try:
        config = await user_config_manager.get_user_config(user_id)
        
        return ApiResponse(
            success=True,
            message="사용자 설정 조회 완료",
            data=config
        )
        
    except Exception as e:
        logger.error(f"❌ 사용자 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 설정 조회에 실패했습니다")

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "service": "user_service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006) 