#!/usr/bin/env python3
"""
뉴스 시스템 및 대시보드 테스트 스크립트
데이터베이스 연결, 뉴스 처리 파이프라인, 대시보드 API 등을 테스트합니다.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 프로젝트 경로 설정
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from shared.database.mysql_client import get_mysql_client
from shared.database.vector_db import VectorDBClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsSystemTester:
    """뉴스 시스템 테스터"""
    
    def __init__(self):
        self.mysql_client = None
        self.vector_db = None
        self.test_results = []
        
    def add_test_result(self, test_name: str, success: bool, message: str):
        """테스트 결과 추가"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        status = "✅ 성공" if success else "❌ 실패"
        logger.info(f"{status}: {test_name} - {message}")
        
    async def test_mysql_connection(self):
        """MySQL 연결 테스트"""
        try:
            self.mysql_client = get_mysql_client()
            
            # 기본 연결 테스트
            result = self.mysql_client.execute_query("SELECT 1 as test")
            if result and result[0]["test"] == 1:
                self.add_test_result("MySQL 연결", True, "데이터베이스 연결 성공")
            else:
                self.add_test_result("MySQL 연결", False, "쿼리 결과 이상")
                
            # 뉴스 테이블 존재 확인
            table_check = self.mysql_client.execute_query(
                "SHOW TABLES LIKE 'news'"
            )
            if table_check:
                self.add_test_result("뉴스 테이블 확인", True, "뉴스 테이블 존재")
            else:
                self.add_test_result("뉴스 테이블 확인", False, "뉴스 테이블 없음")
                
        except Exception as e:
            self.add_test_result("MySQL 연결", False, f"연결 실패: {e}")
            
    async def test_vector_db_connection(self):
        """벡터 DB 연결 테스트"""
        try:
            self.vector_db = VectorDBClient()
            
            # 헬스 체크
            health = self.vector_db.health_check()
            if health["status"] == "healthy":
                self.add_test_result("벡터 DB 연결", True, "벡터 DB 연결 성공")
            else:
                self.add_test_result("벡터 DB 연결", False, f"상태 이상: {health}")
                
            # 컬렉션 통계 확인
            stats = self.vector_db.get_collection_stats()
            if stats:
                self.add_test_result("벡터 DB 컬렉션", True, f"{len(stats)}개 컬렉션 확인")
            else:
                self.add_test_result("벡터 DB 컬렉션", False, "컬렉션 정보 없음")
                
        except Exception as e:
            self.add_test_result("벡터 DB 연결", False, f"연결 실패: {e}")
            
    async def test_news_data_write(self):
        """뉴스 데이터 쓰기 테스트"""
        try:
            if not self.vector_db:
                self.add_test_result("뉴스 데이터 쓰기", False, "벡터 DB 없음")
                return
                
            # 테스트 데이터 생성
            test_data = {
                "stock_code": "000000",
                "stock_name": "테스트 종목",
                "title": f"테스트 뉴스 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "summary": "이것은 시스템 테스트용 뉴스입니다.",
                "impact_score": 0.8,
                "publication_date": datetime.now()
            }
            
            # 고영향 뉴스 저장
            doc_id = self.vector_db.add_high_impact_news(test_data)
            if doc_id:
                self.add_test_result("고영향 뉴스 저장", True, f"저장 성공: {doc_id}")
            else:
                self.add_test_result("고영향 뉴스 저장", False, "저장 실패")
                
            # 일일 뉴스 저장
            daily_data = {
                "stock_code": "000000",
                "stock_name": "테스트 종목",
                "title": f"일일 테스트 뉴스 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "content": "이것은 일일 뉴스 테스트입니다.",
                "url": "https://test.com/news/1",
                "publication_date": datetime.now()
            }
            
            daily_doc_id = self.vector_db.add_daily_news(daily_data)
            if daily_doc_id:
                self.add_test_result("일일 뉴스 저장", True, f"저장 성공: {daily_doc_id}")
            else:
                self.add_test_result("일일 뉴스 저장", False, "저장 실패")
                
        except Exception as e:
            self.add_test_result("뉴스 데이터 쓰기", False, f"쓰기 실패: {e}")
            
    async def test_news_data_read(self):
        """뉴스 데이터 읽기 테스트"""
        try:
            if not self.vector_db:
                self.add_test_result("뉴스 데이터 읽기", False, "벡터 DB 없음")
                return
                
            # 고영향 뉴스 읽기
            high_impact_docs = self.vector_db.get_all_documents("high_impact_news", limit=5)
            if high_impact_docs:
                self.add_test_result("고영향 뉴스 읽기", True, f"{len(high_impact_docs)}개 문서 조회")
            else:
                self.add_test_result("고영향 뉴스 읽기", False, "문서 없음")
                
            # 일일 뉴스 읽기
            daily_docs = self.vector_db.get_all_documents("daily_news", limit=5)
            if daily_docs:
                self.add_test_result("일일 뉴스 읽기", True, f"{len(daily_docs)}개 문서 조회")
            else:
                self.add_test_result("일일 뉴스 읽기", False, "문서 없음")
                
        except Exception as e:
            self.add_test_result("뉴스 데이터 읽기", False, f"읽기 실패: {e}")
            
    async def test_news_search(self):
        """뉴스 검색 테스트"""
        try:
            if not self.vector_db:
                self.add_test_result("뉴스 검색", False, "벡터 DB 없음")
                return
                
            # 검색 테스트
            search_results = self.vector_db.search_similar_documents(
                query="테스트 뉴스",
                collection_name="high_impact_news",
                top_k=3
            )
            
            if search_results:
                self.add_test_result("뉴스 검색", True, f"{len(search_results)}개 검색 결과")
            else:
                self.add_test_result("뉴스 검색", False, "검색 결과 없음")
                
        except Exception as e:
            self.add_test_result("뉴스 검색", False, f"검색 실패: {e}")
            
    async def test_mysql_news_operations(self):
        """MySQL 뉴스 운영 테스트"""
        try:
            if not self.mysql_client:
                self.add_test_result("MySQL 뉴스 운영", False, "MySQL 클라이언트 없음")
                return
                
            # 뉴스 수 조회
            count_result = self.mysql_client.execute_query(
                "SELECT COUNT(*) as count FROM news"
            )
            if count_result:
                count = count_result[0]["count"]
                self.add_test_result("뉴스 수 조회", True, f"총 {count}개 뉴스")
            else:
                self.add_test_result("뉴스 수 조회", False, "조회 실패")
                
            # 고영향 뉴스 수 조회
            high_impact_result = self.mysql_client.execute_query(
                "SELECT COUNT(*) as count FROM news WHERE impact_score >= 0.7"
            )
            if high_impact_result:
                high_count = high_impact_result[0]["count"]
                self.add_test_result("고영향 뉴스 수", True, f"총 {high_count}개 고영향 뉴스")
            else:
                self.add_test_result("고영향 뉴스 수", False, "조회 실패")
                
        except Exception as e:
            self.add_test_result("MySQL 뉴스 운영", False, f"운영 테스트 실패: {e}")
            
    async def test_data_consistency(self):
        """데이터 일관성 테스트"""
        try:
            if not self.mysql_client or not self.vector_db:
                self.add_test_result("데이터 일관성", False, "클라이언트 없음")
                return
                
            # MySQL 고영향 뉴스 수
            mysql_high = self.mysql_client.execute_query(
                "SELECT COUNT(*) as count FROM news WHERE impact_score >= 0.7"
            )
            mysql_count = mysql_high[0]["count"] if mysql_high else 0
            
            # 벡터 DB 고영향 뉴스 수
            vector_docs = self.vector_db.get_all_documents("high_impact_news", limit=10000)
            vector_count = len(vector_docs)
            
            # 일관성 체크
            if mysql_count == 0 and vector_count == 0:
                self.add_test_result("데이터 일관성", True, "둘 다 데이터 없음 (일관성 유지)")
            elif mysql_count > 0 and vector_count > 0:
                ratio = vector_count / mysql_count
                if ratio >= 0.8:  # 80% 이상이면 일관성 유지
                    self.add_test_result("데이터 일관성", True, f"일관성 유지 (MySQL: {mysql_count}, 벡터: {vector_count})")
                else:
                    self.add_test_result("데이터 일관성", False, f"일관성 문제 (MySQL: {mysql_count}, 벡터: {vector_count})")
            else:
                self.add_test_result("데이터 일관성", False, f"불일치 (MySQL: {mysql_count}, 벡터: {vector_count})")
                
        except Exception as e:
            self.add_test_result("데이터 일관성", False, f"일관성 테스트 실패: {e}")
            
    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("🚀 뉴스 시스템 테스트 시작")
        
        # 테스트 실행 순서
        test_methods = [
            self.test_mysql_connection,
            self.test_vector_db_connection,
            self.test_news_data_write,
            self.test_news_data_read,
            self.test_news_search,
            self.test_mysql_news_operations,
            self.test_data_consistency
        ]
        
        for test_method in test_methods:
            await test_method()
            
        # 결과 출력
        self.print_test_summary()
        
    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        logger.info("📊 테스트 결과 요약")
        print("\n" + "="*80)
        print("🧪 뉴스 시스템 테스트 결과")
        print("="*80)
        
        success_count = 0
        total_count = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ 성공" if result["success"] else "❌ 실패"
            print(f"{status} | {result['test_name']}: {result['message']}")
            if result["success"]:
                success_count += 1
                
        print("="*80)
        print(f"📈 총 {total_count}개 테스트 중 {success_count}개 성공 ({success_count/total_count*100:.1f}%)")
        
        if success_count == total_count:
            print("🎉 모든 테스트 통과! 시스템이 정상적으로 동작합니다.")
        else:
            print("⚠️  일부 테스트 실패. 문제를 확인하고 수정하세요.")
            
        print("="*80)
        
    def get_test_results(self) -> List[Dict[str, Any]]:
        """테스트 결과 반환"""
        return self.test_results.copy()

async def main():
    """메인 함수"""
    try:
        tester = NewsSystemTester()
        await tester.run_all_tests()
        
        # 테스트 결과에 따라 종료 코드 설정
        results = tester.get_test_results()
        failed_tests = [r for r in results if not r["success"]]
        
        if failed_tests:
            logger.error(f"💥 {len(failed_tests)}개 테스트 실패")
            return 1
        else:
            logger.info("🎉 모든 테스트 통과")
            return 0
            
    except Exception as e:
        logger.error(f"❌ 테스트 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 