"""
데이터베이스 스키마 업데이트 유틸리티
누락된 컬럼들을 추가합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.mysql_client import get_mysql_client
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_schema():
    """데이터베이스 스키마 업데이트"""
    try:
        mysql_client = get_mysql_client()
        
        logger.info("🔧 데이터베이스 스키마 업데이트 시작...")
        
        # 1. 현재 테이블 구조 확인
        logger.info("📊 현재 news 테이블 구조 확인...")
        columns_query = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'HyperAsset' 
              AND TABLE_NAME = 'news'
            ORDER BY ORDINAL_POSITION
        """
        
        current_columns = mysql_client.execute_query(columns_query)
        if not current_columns:
            logger.error("❌ 테이블 구조 조회 실패")
            return False
        logger.info(f"현재 컬럼 수: {len(current_columns)}개")
        
        # 2. 누락된 컬럼 확인
        existing_column_names = [col['COLUMN_NAME'] for col in current_columns]
        required_columns = ['relevance_score', 'similarity_checked']
        missing_columns = [col for col in required_columns if col not in existing_column_names]
        
        if missing_columns:
            logger.info(f"⚠️ 누락된 컬럼들: {missing_columns}")
            
            # 3. 컬럼 추가
            if 'relevance_score' in missing_columns:
                logger.info("➕ relevance_score 컬럼 추가 중...")
                mysql_client.execute_query("""
                    ALTER TABLE news 
                    ADD COLUMN relevance_score DECIMAL(3,2) DEFAULT 1.00 COMMENT '종목 관련성 점수 (0.0-1.0)'
                """)
                logger.info("✅ relevance_score 컬럼 추가 완료")
            
            if 'similarity_checked' in missing_columns:
                logger.info("➕ similarity_checked 컬럼 추가 중...")
                mysql_client.execute_query("""
                    ALTER TABLE news 
                    ADD COLUMN similarity_checked BOOLEAN DEFAULT TRUE COMMENT '유사도 검사 완료 여부'
                """)
                logger.info("✅ similarity_checked 컬럼 추가 완료")
            
            # 4. 인덱스 추가
            logger.info("📊 인덱스 추가 중...")
            try:
                mysql_client.execute_query("CREATE INDEX idx_relevance_score ON news(relevance_score)")
            except Exception as e:
                if "Duplicate key name" in str(e):
                    logger.info("인덱스 이미 존재: idx_relevance_score")
                else:
                    logger.warning(f"인덱스 생성 실패: {e}")
            
            try:
                mysql_client.execute_query("CREATE INDEX idx_similarity_checked ON news(similarity_checked)")
            except Exception as e:
                if "Duplicate key name" in str(e):
                    logger.info("인덱스 이미 존재: idx_similarity_checked")
                else:
                    logger.warning(f"인덱스 생성 실패: {e}")
        
        else:
            logger.info("✅ 모든 필수 컬럼이 이미 존재합니다")
        
        # 5. 최종 확인
        logger.info("🔍 업데이트 후 테이블 구조 확인...")
        final_columns = mysql_client.execute_query(columns_query)
        if final_columns:
            logger.info(f"최종 컬럼 수: {len(final_columns)}개")
        else:
            logger.warning("⚠️ 최종 테이블 구조 조회 실패")
        
        # 6. 특정 컬럼 확인
        check_query = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'HyperAsset' 
              AND TABLE_NAME = 'news' 
              AND COLUMN_NAME IN ('relevance_score', 'similarity_checked')
        """
        
        check_result = mysql_client.execute_query(check_query)
        if check_result:
            logger.info("✅ 필수 컬럼 확인 완료:")
            for col in check_result:
                logger.info(f"   • {col['COLUMN_NAME']}: {col['DATA_TYPE']} (기본값: {col['COLUMN_DEFAULT']})")
        
        logger.info("🎉 데이터베이스 스키마 업데이트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 스키마 업데이트 실패: {e}")
        return False

if __name__ == "__main__":
    success = update_database_schema()
    if success:
        print("✅ 스키마 업데이트 성공!")
    else:
        print("❌ 스키마 업데이트 실패!")
        sys.exit(1) 