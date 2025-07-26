"""
DART API 클라이언트 모듈
금융감독원 전자공시시스템 DART API를 활용한 공시 정보 수집 기능 제공
"""
import re
import aiohttp
import requests
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config.env_local import get_env_var, get_int_env_var, get_list_env_var
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import time
import zipfile
import io
from bs4 import BeautifulSoup

# 로깅 설정
logger = logging.getLogger(__name__)


class DARTAPIClient:
    """DART API 클라이언트 클래스"""

    def __init__(self):
        """DART API 클라이언트 초기화"""
        self.api_key = get_env_var("DART_API_KEY", "")
        self.api_url = get_env_var("DART_API_URL", "https://opendart.fss.or.kr/api")
        self.timeout = get_int_env_var("API_TIMEOUT", 30)
        
        # 기업 코드 데이터 저장 경로
        self.data_path = Path("./data/dart")
        self.corp_code_file = self.data_path / "CORPCODE.xml"
        self.corp_code_map = {}  # 종목코드 -> 기업코드 매핑
        
        # 데이터 디렉토리 생성
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # 기업 코드 데이터 로드
        self._load_corp_codes()

        # 필터링 키워드
        self.important_keywords = [
            # 자본/증자 관련
            "자기주식취득", "자기주식소각", "자기주식처분", 
            "유상증자", "무상증자", "유상감자", "무상감자", 
            "전환사채", "신주인수권부사채", "교환사채",
            
            # 금융업 특화
            "파생결합증권", 
            "ELS", "DLS", "신용공여", 
            "펀드설정", "투자일임", "신탁계약", "자기자본비율", 
            "유동성공급", "자산유동화", "PF대출", "유동화증권",

            # 배당/실적
            "현금배당", "주식배당", "결산실적", "잠정실적", "영업실적",

            # 지배구조/합병
            "최대주주변경", "경영권변동", "대표이사변경", "임원변경",
            "주식양수도", "합병", "분할", "자회사설립", "지분취득", "지분매각",

            # 리스크
            "감사의견", "의견거절", "한정", "소송", "제재", "상장폐지", "관리종목"
        ]

        # API 키 유효성 검사
        if not self.api_key:
            logger.error("DART API 키가 설정되지 않음")
            raise ValueError("DART API 키가 필요합니다.")

    def _load_corp_codes(self):
        """기업 코드 데이터 로드"""
        try:
            # 파일이 없거나 1일 이상 지났으면 다시 다운로드
            if not self.corp_code_file.exists() or \
               (datetime.now().timestamp() - self.corp_code_file.stat().st_mtime) > 86400:
                self._download_corp_codes()
            
            # XML 파싱
            tree = ET.parse(self.corp_code_file)
            root = tree.getroot()
            
            # 종목코드 -> 기업코드 매핑 생성
            for list_element in root.findall(".//list"):
                stock_code = list_element.findtext("stock_code", "").strip()
                corp_code = list_element.findtext("corp_code", "").strip()
                if stock_code and corp_code:
                    self.corp_code_map[stock_code] = corp_code
            
            if not self.corp_code_map:
                raise ValueError("기업 코드 데이터가 비어있습니다.")
            
            logger.info(f"기업 코드 데이터 로드 완료: {len(self.corp_code_map)}개")
            
        except Exception as e:
            logger.error(f"기업 코드 데이터 로드 실패: {e}")
            raise

    def _download_corp_codes(self):
        """기업 코드 데이터 다운로드"""
        try:
            url = f"{self.api_url}/corpCode.xml"
            params = {"crtfc_key": self.api_key}
            
            # 최대 3번 재시도
            for attempt in range(3):
                try:
                    response = requests.get(url, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == 2:  # 마지막 시도였다면
                        raise
                    logger.warning(f"기업 코드 다운로드 재시도 {attempt + 1}/3: {e}")
                    time.sleep(1)  # 1초 대기 후 재시도
            
            # ZIP 파일 저장
            zip_path = self.data_path / "CORPCODE.zip"
            with open(zip_path, "wb") as f:
                f.write(response.content)
            
            # ZIP 파일 압축 해제
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(self.data_path)
            
            # ZIP 파일 삭제
            zip_path.unlink()
            
            logger.info("기업 코드 데이터 다운로드 완료")
            
        except Exception as e:
            logger.error(f"기업 코드 데이터 다운로드 실패: {e}")
            raise

    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목코드로 기업 고유번호 조회"""
        return self.corp_code_map.get(stock_code)
    
    def get_recent_disclosures_test(self, stock_code: str, days: int = 2) -> List[Dict]:
        """최근 1년치 공시 정보 조회 db 저장용 1년치"""
        try:
            logger.info(f"공시 정보 조회 시작: {stock_code}")
            
            corp_code = self.get_corp_code(stock_code)
            logger.info(f"기업 고유번호: {corp_code}")
            
            if not corp_code:
                logger.error(f"기업 고유번호 조회 실패: {stock_code}")
                return []

            # 조회 시작일 계산 (1년 전)
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")
            logger.info(f"조회 기간: {start_date} ~ {end_date}")
            disclosures=[]
            
            page_no=1

            while True:
                params = {
                    "corp_code": corp_code,
                    "bgn_de": start_date,
                    "end_de": end_date,
                    "page_no": str(page_no),
                    "page_count": "100",
                }

                result = self._make_request("list", params)
                if not result or not result.get("list"):
                    break

                for item in result["list"]:
                    if self._is_important_disclosure(item):
                        disclosure={
                            "stock_code": stock_code,
                            "corp_code": corp_code,
                            "corp_name": item.get("corp_name", ""),
                            "rcept_no": item.get("rcept_no", ""),
                            "report_nm": item.get("report_nm", ""),
                            "rcept_dt": item.get("rcept_dt", ""),
                            "flr_nm": item.get("flr_nm", ""),
                            "rm": item.get("rm", ""),
                            "created_at": datetime.now().isoformat(),
                        }
                        report_nm = disclosure["report_nm"]
                    
                        def remove_correction_brackets(text: str) -> str:
                            """report_nm에서 '정정'이 포함된 [ ... ] 블록만 제거"""
                            return re.sub(r"\[[^\[\]]*정정[^\[\]]*\]", "", text).strip()
                        
                        

                        if "정정" in report_nm:
                            cleaned_title = remove_correction_brackets(report_nm)

                            disclosures = [
                                d for d in disclosures
                                if remove_correction_brackets(d["report_nm"]) != cleaned_title
                            ]
                            
                        disclosures.append(disclosure)

                # 100건 미만이면 마지막 페이지로 간주
                if len(result["list"]) < 100:
                    break

                page_no += 1
            logger.info(f"최근 공시 조회 완료: {stock_code}, {len(disclosures)}건")
            return disclosures 

        except Exception as e:
            logger.error(f"공시 조회 중 오류 발생: {e}")
            return []
    
    
    def get_recent_disclosures(self, stock_code: str, days: int = 7, exclude_duplicates: bool = True) -> List[Dict]:
        """최근 공시 정보 조회"""
        try:
            logger.info(f"공시 정보 조회 시작: {stock_code}")
            
            corp_code = self.get_corp_code(stock_code)
            logger.info(f"기업 고유번호: {corp_code}") #종목코드로 list 조회 불가능해서 기업코드로 조회해야함
            
            if not corp_code:
                logger.error(f"기업 고유번호 조회 실패: {stock_code}")
                return []

            # 조회 시작일 계산
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")
            logger.info(f"조회 기간: {start_date} ~ {end_date}")

            params = {
                "corp_code": corp_code,
                "bgn_de": start_date,
                "end_de": end_date,
                "page_no": "1",
                "page_count": "100",
            }

            result = self._make_request("list", params)
            if not result or not result.get("list"):
                logger.info("공시 데이터 없음")
                return []

            disclosures = []

            for item in result["list"]: # list : 이후 dict 로 여러개 공시정보 저장되어있음 -> 여기서 item 은 각 공시정보 dict 들이 차례대로 들어감
                # 필터링: 중요한 공시만 선별
                
                if self._is_important_disclosure(item): #true 면 
                    disclosure = {
                        "stock_code": stock_code,
                        "corp_code": corp_code,
                        "corp_name": item.get("corp_name", ""),
                        "rcept_no": item.get("rcept_no", ""),
                        "report_nm": item.get("report_nm", ""),
                        "rcept_dt": item.get("rcept_dt", ""),
                        "flr_nm": item.get("flr_nm", ""),
                        "rm": item.get("rm", ""),
                        "created_at": datetime.now().isoformat(), #현재날짜 시간 반환
                    }
                    report_nm = disclosure["report_nm"]
                    
                    def remove_correction_brackets(text: str) -> str:
                        """report_nm에서 '정정'이 포함된 [ ... ] 블록만 제거"""
                        return re.sub(r"\[[^\[\]]*정정[^\[\]]*\]", "", text).strip()
                    
                    

                    if "정정" in report_nm:
                        cleaned_title = remove_correction_brackets(report_nm)

                        disclosures = [
                            d for d in disclosures
                            if remove_correction_brackets(d["report_nm"]) != cleaned_title
                        ]
                        
                    # 중복 체크
                    disclosures.append(disclosure)
                
            disclosures = [result["list"][0]]

            logger.info(f"최근 공시 조회 완료: {stock_code}, {len(disclosures)}건")
            return disclosures

        except Exception as e:
            logger.error(f"공시 조회 중 오류 발생: {e}")
            return []
        
    async def get_disclosure_detail(self, rcept_no: str) -> Optional[Dict]: #공시 document 원문 가져와서 xml 파싱 후 text 반환
        """DART document.xml API에서 공시 텍스트 추출 (ZIP → XML → Text)"""
        try:
            # 1. ZIP 요청
            url = f"{self.api_url}/document.xml"
            params = {"rcept_no": rcept_no, "crtfc_key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"[공시 다운로드 실패] {response.status}")
                        return None
                    zip_bytes = await response.read()

            # 2. ZIP 해제 후 XML 추출
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                xml_name = next((f for f in zf.namelist() if f"{rcept_no}.xml" in f), None)
                if not xml_name:
                    raise FileNotFoundError(f"{rcept_no}.xml 파일을 찾을 수 없습니다.")
                xml_bytes = zf.read(xml_name)
                xml_html = xml_bytes.decode("utf-8", errors="replace")

            # 3. HTML → 텍스트 추출
            soup = BeautifulSoup(xml_html, 'lxml-xml')
            for tag in soup(['script', 'style']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = '\n'.join(lines)

            # 4. 최종 반환
            return {
                "rcept_no": rcept_no,
                "content": clean_text,
                "attach_files": []  # 필요시 확장
            }

        except Exception as e:
            logger.error(f"[공시 파싱 오류] {e}")
            return None

    def _is_important_disclosure(self, disclosure: Dict) -> bool:
        """공시의 중요도 판단 (키워드 필터 안전 처리 포함)"""
        try:
            report_name = disclosure.get("report_nm", "").lower()
            report_content = disclosure.get("rm", "").lower()

            for keyword in self.important_keywords:
                try:
                    if keyword.lower() in report_name or keyword.lower() in report_content:
                        return True
                except Exception:
                    continue  # 리스트나 숫자 들어있으면 무시

            return False

        except Exception as e:
            logger.error(f"공시 중요도 판단 중 오류 발생: {e}")
            return False


    def get_financial_statements(self, stock_code: str, year: int = None) -> Dict:
        """재무제표 조회"""
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            logger.error(f"기업 고유번호 조회 실패: {stock_code}")
            return {}

        if not year:
            year = datetime.now().year

        # 손익계산서 조회
        params = {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11013",  # 1분기보고서
            "fs_div": "CFS",  # 연결재무제표
        }

        result = self._make_request("fnlttSinglAcntAll", params)
        if not result or not result.get("list"):
            return {}

        financial_data = {
            "stock_code": stock_code,
            "corp_code": corp_code,
            "year": year,
            "revenue": 0,
            "operating_profit": 0,
            "net_profit": 0,
            "total_assets": 0,
            "total_equity": 0,
            "created_at": datetime.now().isoformat(),
        }

        # 주요 재무 항목 추출
        for item in result["list"]:
            account_nm = item.get("account_nm", "")
            thstrm_amount = item.get("thstrm_amount", "0").replace(",", "")

            try:
                amount = int(thstrm_amount) if thstrm_amount.isdigit() else 0

                if "매출액" in account_nm or "수익" in account_nm:
                    financial_data["revenue"] = amount
                elif "영업이익" in account_nm:
                    financial_data["operating_profit"] = amount
                elif "당기순이익" in account_nm:
                    financial_data["net_profit"] = amount
                elif "자산총계" in account_nm:
                    financial_data["total_assets"] = amount
                elif "자본총계" in account_nm:
                    financial_data["total_equity"] = amount

            except (ValueError, AttributeError):
                continue

        logger.info(f"재무제표 조회 완료: {stock_code}, {year}년")
        return financial_data

    def get_major_shareholders(self, stock_code: str) -> List[Dict]:
        """대주주 정보 조회"""
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            logger.error(f"기업 고유번호 조회 실패: {stock_code}")
            return []

        params = {"corp_code": corp_code}

        result = self._make_request("hyslrSttus", params)
        if not result or not result.get("list"):
            return []

        shareholders = []
        for item in result["list"]:
            shareholder = {
                "stock_code": stock_code,
                "corp_code": corp_code,
                "shrhldr_nm": item.get("shrhldr_nm", ""),  # 주주명
                "hold_stock_co": item.get("hold_stock_co", "0"),  # 보유주식수
                "hold_stock_rt": item.get("hold_stock_rt", "0"),  # 지분율
                "created_at": datetime.now().isoformat(),
            }
            shareholders.append(shareholder)

        logger.info(f"대주주 정보 조회 완료: {stock_code}, {len(shareholders)}명")
        return shareholders

    def search_disclosures_by_keyword(
        self, stock_code: str, keyword: str, days: int = 30
    ) -> List[Dict]:
        """키워드로 공시 검색"""
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            logger.error(f"기업 고유번호 조회 실패: {stock_code}")
            return []

        # 조회 기간 설정
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")

        params = {
            "corp_code": corp_code,
            "bgn_de": start_date,
            "end_de": end_date,
            "page_no": "1",
            "page_count": "100",
        }

        result = self._make_request("list", params)
        if not result or not result.get("list"):
            return []

        # 키워드 필터링
        filtered_disclosures = []
        for item in result["list"]:
            report_nm = item.get("report_nm", "").lower()
            if keyword.lower() in report_nm:
                disclosure = {
                    "stock_code": stock_code,
                    "corp_code": corp_code,
                    "corp_name": item.get("corp_name", ""),
                    "rcept_no": item.get("rcept_no", ""),
                    "report_nm": item.get("report_nm", ""),
                    "rcept_dt": item.get("rcept_dt", ""),
                    "flr_nm": item.get("flr_nm", ""),
                    "rm": item.get("rm", ""),
                    "keyword_matched": keyword,
                    "created_at": datetime.now().isoformat(),
                }
                filtered_disclosures.append(disclosure)

        logger.info(
            f"키워드 공시 검색 완료: {stock_code}, '{keyword}', {len(filtered_disclosures)}건"
        )
        return filtered_disclosures

    def get_company_info(self, stock_code: str) -> Optional[Dict]:
        """기업 기본정보 조회"""
        params = {"corp_code": "", "corp_name": "", "stock_code": stock_code}

        result = self._make_request("company", params)
        if not result or not result.get("list"):
            return None

        company_info = result["list"][0]

        return {
            "stock_code": stock_code,
            "corp_code": company_info.get("corp_code", ""),
            "corp_name": company_info.get("corp_name", ""),
            "corp_name_eng": company_info.get("corp_name_eng", ""),
            "stock_name": company_info.get("stock_name", ""),
            "stock_code_full": company_info.get("stock_code", ""),
            "ceo_nm": company_info.get("ceo_nm", ""),
            "corp_cls": company_info.get("corp_cls", ""),
            "jurir_no": company_info.get("jurir_no", ""),
            "bizr_no": company_info.get("bizr_no", ""),
            "adres": company_info.get("adres", ""),
            "hm_url": company_info.get("hm_url", ""),
            "ir_url": company_info.get("ir_url", ""),
            "phn_no": company_info.get("phn_no", ""),
            "fax_no": company_info.get("fax_no", ""),
            "induty_code": company_info.get("induty_code", ""),
            "est_dt": company_info.get("est_dt", ""),
            "acc_mt": company_info.get("acc_mt", ""),
            "created_at": datetime.now().isoformat(),
        }

    def health_check(self) -> Dict:
        """DART API 상태 확인"""
        try:
            # 간단한 API 호출 테스트 (006800 기업정보)
            company_info = self.get_company_info("006800")

            if company_info:
                return {
                    "status": "healthy",
                    "api_key_configured": bool(self.api_key),
                    "test_company": company_info.get("corp_name", ""),
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "테스트 요청 실패",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"DART API 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """API 요청 수행"""
        try:
            # API 키 추가
            params["crtfc_key"] = self.api_key
            
            # URL 구성
            url = f"{self.api_url}/{endpoint}.json"
            logger.info(f"API 요청: {url}")
            logger.debug(f"요청 파라미터: {params}")
            
            # 요청 수행
            response = requests.get(url, params=params, timeout=self.timeout)
            logger.info(f"API 응답 상태 코드: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API 요청 실패: {response.status_code}")
                logger.error(f"응답 내용: {response.text}")
                return None
            
            # 응답 파싱
            result = response.json()
            logger.info(f"API 응답 결과: {result.get('status')}")
            
            if result.get("status") != "000":
                logger.error(f"API 오류: {result.get('message')}")
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"API 요청 중 오류 발생: {e}")
            return None


# 전역 DART API 클라이언트 인스턴스
dart_client = DARTAPIClient()
