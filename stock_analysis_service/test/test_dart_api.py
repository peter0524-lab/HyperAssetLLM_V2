"""
DART API 클라이언트 테스트
"""

import unittest
from datetime import datetime, timedelta
from shared.apis.dart_api import DARTAPIClient
import logging
import json
from pathlib import Path
import os

class TestDARTAPIClient(unittest.TestCase):
    """DART API 클라이언트 테스트 클래스"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        # 로깅 레벨 설정
        logging.basicConfig(level=logging.INFO)
        
        # 테스트 결과 저장 디렉토리 생성
        cls.output_dir = Path("./test_output/dart")
        cls.output_dir.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        """테스트 설정"""
        self.client = DARTAPIClient()
        self.test_stock_code = "005930"  # 삼성전자
        
        # API 키 확인
        if not self.client.api_key:
            self.skipTest("DART API 키가 설정되지 않았습니다.")

    def test_get_corp_code(self):
        """기업 고유번호 조회 테스트"""
        corp_code = self.client.get_corp_code(self.test_stock_code)
        self.assertIsNotNone(corp_code)
        self.assertTrue(len(corp_code) > 0)
        print(f"조회된 기업 고유번호: {corp_code}")

    def test_get_recent_disclosures(self):
        """최근 공시 정보 조회 테스트"""
        disclosures = self.client.get_recent_disclosures(self.test_stock_code, days=30)
        
        self.assertIsInstance(disclosures, list)
        print(f"조회된 공시 건수: {len(disclosures)}")
        
        if len(disclosures) > 0:
            disclosure = disclosures[0]
            required_fields = [
                'stock_code', 'corp_code', 'corp_name', 'rcept_no',
                'report_nm', 'rcept_dt', 'flr_nm', 'content'
            ]
            for field in required_fields:
                self.assertIn(field, disclosure)
            print(f"첫 번째 공시 제목: {disclosure['report_nm']}")

    def test_get_disclosure_detail(self):
        """공시 상세 내용 조회 테스트"""
        # 먼저 최근 공시 목록을 가져와서 하나의 rcept_no를 얻습니다
        disclosures = self.client.get_recent_disclosures(self.test_stock_code, days=30)
        if len(disclosures) > 0:
            rcept_no = disclosures[0]['rcept_no']
            detail = self.client.get_disclosure_detail(rcept_no)
            
            self.assertIsNotNone(detail)
            self.assertIn('content', detail)
            self.assertIn('attach_files', detail)
            print(f"공시 상세 내용 길이: {len(detail['content'])}")

    def test_duplicate_disclosure_handling(self):
        """중복 공시 처리 테스트"""
        # 중복 제외 옵션으로 공시 조회
        disclosures_filtered = self.client.get_recent_disclosures(
            self.test_stock_code, 
            days=30, 
            exclude_duplicates=True
        )
        
        # 중복 포함 옵션으로 공시 조회
        disclosures_all = self.client.get_recent_disclosures(
            self.test_stock_code, 
            days=30, 
            exclude_duplicates=False
        )
        
        print(f"전체 공시 수: {len(disclosures_all)}")
        print(f"중복 제외 공시 수: {len(disclosures_filtered)}")
        
        if len(disclosures_all) > 0:
            # 중복 제외된 결과가 전체 결과보다 적거나 같아야 함
            self.assertLessEqual(len(disclosures_filtered), len(disclosures_all))
            
            # 중복 검사
            seen_reports = set()
            for disclosure in disclosures_filtered:
                report_key = f"{disclosure['report_nm']}_{disclosure['rcept_dt']}"
                # 중복 제외된 결과에는 중복이 없어야 함
                self.assertNotIn(report_key, seen_reports)
                seen_reports.add(report_key)

    def test_correction_disclosure_handling(self):
        """정정공시 처리 테스트"""
        disclosures = self.client.get_recent_disclosures(
            self.test_stock_code, 
            days=90  # 정정공시를 찾기 위해 기간을 늘림
        )
        
        # 정정공시가 있는 경우 테스트
        corrections = [d for d in disclosures if "정정" in d['report_nm']]
        print(f"정정공시 수: {len(corrections)}")
        
        if corrections:
            for correction in corrections:
                # 정정공시는 is_correction 플래그가 True여야 함
                self.assertTrue(correction.get('is_correction', False))
                print(f"정정공시 제목: {correction['report_nm']}")
                
                # 원본 공시가 리스트에 없어야 함
                original_report = correction['report_nm'].replace("정정", "").strip()
                originals = [d for d in disclosures if d['report_nm'] == original_report and 
                           d['rcept_dt'] == correction['rcept_dt']]
                self.assertEqual(len(originals), 0)

    def test_invalid_stock_code(self):
        """잘못된 종목코드 테스트"""
        invalid_stock_code = "000000"
        disclosures = self.client.get_recent_disclosures(invalid_stock_code)
        self.assertEqual(len(disclosures), 0)
        print("잘못된 종목코드 테스트 완료")

    def test_api_error_handling(self):
        """API 에러 처리 테스트"""
        # API 키를 임시로 잘못된 값으로 설정
        original_api_key = self.client.api_key
        self.client.api_key = "invalid_key"
        
        result = self.client.get_recent_disclosures(self.test_stock_code)
        self.assertEqual(len(result), 0)
        print("API 에러 처리 테스트 완료")
        
        # API 키 복구
        self.client.api_key = original_api_key

    def test_detailed_disclosure_check(self):
        """공시 데이터 상세 확인 테스트"""
        print("\n=== 공시 데이터 상세 확인 ===")
        
        # 최근 공시 조회 (기간을 30일로 늘림)
        disclosures = self.client.get_recent_disclosures(self.test_stock_code, days=30)
        
        if not disclosures:
            print("조회된 공시가 없습니다.")
            return
            
        print(f"\n총 {len(disclosures)}개의 공시가 조회되었습니다.")
        
        # 결과 저장할 파일 경로
        output_file = self.output_dir / f"disclosure_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(output_file, "w", encoding="utf-8") as f:
            # 파일에 기본 정보 작성
            f.write(f"테스트 실행 시간: {datetime.now()}\n")
            f.write(f"대상 기업: {self.test_stock_code}\n")
            f.write(f"조회된 공시 수: {len(disclosures)}\n\n")
            
            # 각 공시 정보 출력 및 저장
            for idx, disclosure in enumerate(disclosures, 1):
                print(f"\n[공시 {idx}/{len(disclosures)}]")
                print(f"제목: {disclosure['report_nm'].strip()}")
                print(f"접수번호: {disclosure['rcept_no']}")
                print(f"접수일자: {disclosure['rcept_dt']}")
                print(f"제출인: {disclosure['flr_nm']}")
                
                # 상세 내용 조회
                detail = self.client.get_disclosure_detail(disclosure['rcept_no'])
                if detail:
                    content_preview = detail['content'][:200] + "..." if len(detail['content']) > 200 else detail['content']
                    print(f"내용 미리보기: {content_preview}")
                
                # 파일에 상세 정보 저장
                f.write(f"\n{'='*50}\n")
                f.write(f"공시 {idx}/{len(disclosures)}\n")
                f.write(f"제목: {disclosure['report_nm'].strip()}\n")
                f.write(f"접수번호: {disclosure['rcept_no']}\n")
                f.write(f"접수일자: {disclosure['rcept_dt']}\n")
                f.write(f"제출인: {disclosure['flr_nm']}\n")
                
                if detail:
                    f.write("\n[상세 내용]\n")
                    f.write(detail['content'])
                    f.write("\n")
                
                f.write(f"\n전체 데이터(JSON):\n")
                f.write(json.dumps(disclosure, ensure_ascii=False, indent=2, default=str))
                f.write("\n")
        
        print(f"\n상세 결과가 다음 파일에 저장되었습니다: {output_file}")
        
        # 최소한 하나의 공시는 있어야 함
        self.assertGreater(len(disclosures), 0)
        # 각 공시는 필수 필드를 가져야 함
        self.assertTrue(all(
            all(key in d for key in ['report_nm', 'rcept_no', 'rcept_dt', 'flr_nm'])
            for d in disclosures
        ))

if __name__ == '__main__':
    unittest.main() 