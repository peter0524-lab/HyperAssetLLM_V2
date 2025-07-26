import asyncio
import pytest
import logging
from unittest.mock import MagicMock, patch
from services.disclosure_service.disclosure_service import DisclosureService
from shared.apis.dart_api import DARTAPIClient
from shared.database.mysql_client import MySQLClient
from shared.llm.hyperclova_client import HyperCLOVAClient

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_disclosure_llm_analysis():
    """공시 LLM 분석 테스트"""
    # Mock 객체 생성
    mysql_client = MagicMock(spec=MySQLClient)
    dart_client = MagicMock(spec=DARTAPIClient)
    
    # 테스트용 공시 데이터
    test_disclosure = {
        "rcept_no": "20240101000001",
        "corp_code": "00000001",
        "corp_name": "테스트기업",
        "stock_code": "000001",
        "report_nm": "유상증자 결정",
        "rcept_dt": "20240101",
        "report_tp": "유상증자"
    }
    
    test_disclosure_detail = {
        "content": """
        1. 신주의 종류와 수: 보통주 1,000,000주
        2. 증자방식: 주주배정 유상증자
        3. 신주 발행가액: 10,000원
        4. 증자금액: 10,000,000,000원
        5. 자금사용 목적: 신규사업 투자
        """
    }
    
    # DART API 응답 설정
    dart_client.get_disclosure_detail.return_value = test_disclosure_detail
    
    # MySQL 응답 설정
    mysql_client.fetch_one_async.return_value = ("테스트기업",)
    mysql_client.execute_query_async.return_value = None
    
    # 서비스 인스턴스 생성
    service = DisclosureService()
    service.mysql_client = mysql_client
    service.dart_client = dart_client
    
    # LLM 분석 수행
    llm_analysis = await service.analyze_disclosure(test_disclosure_detail, "테스트기업")
    
    # 결과 검증
    assert llm_analysis is not None
    assert "impact_score" in llm_analysis
    assert "sentiment" in llm_analysis
    assert "keywords" in llm_analysis
    assert "expected_impact" in llm_analysis
    assert "full_analysis" in llm_analysis
    
    # 분석 결과 저장 테스트
    await service.save_disclosure_analysis(test_disclosure, test_disclosure_detail, llm_analysis)
    
    # DB 저장 호출 확인
    mysql_client.execute_query_async.assert_called_once()

@pytest.mark.asyncio
async def test_real_disclosure_analysis():
    """실제 공시 분석 테스트"""
    service = DisclosureService()
    
    # 삼성전자 공시 데이터 가져오기 (종목코드: 005930)
    disclosures = await service.fetch_disclosure_data("005930")
    assert disclosures is not None
    assert len(disclosures) > 0
    
    # 중요 공시 필터링
    important_disclosures = await service.filter_important_disclosures(disclosures)
    assert important_disclosures is not None
    
    if important_disclosures:
        # 첫 번째 중요 공시에 대해 상세 분석 수행
        disclosure = important_disclosures[0]
        rcept_no = disclosure.get("rcept_no")
        
        # 공시 상세 정보 가져오기
        disclosure_detail = service.dart_client.get_disclosure_detail(rcept_no)
        assert disclosure_detail is not None
        
        # LLM 분석 수행
        llm_analysis = await service.analyze_disclosure(disclosure_detail, "삼성전자")
        assert llm_analysis is not None
        
        # 분석 결과 출력
        print("\n=== 공시 분석 결과 ===")
        print(f"제목: {disclosure.get('report_nm')}")
        print(f"접수번호: {rcept_no}")
        print(f"영향도 점수: {llm_analysis.get('impact_score')}")
        print(f"감성 분석: {llm_analysis.get('sentiment')}")
        print(f"주요 키워드: {', '.join(llm_analysis.get('keywords', []))}")
        print(f"예상 주가 영향: {llm_analysis.get('expected_impact')}")
        print("\n전체 분석:")
        print(llm_analysis.get('full_analysis')) 