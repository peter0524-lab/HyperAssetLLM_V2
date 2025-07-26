"""
한국투자증권 KIS API 클라이언트 모듈
실시간 주가 데이터, 차트 데이터, 웹소켓 연결 기능 제공
"""

import requests
import websocket
import json
import time
import threading
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from config.env_local import get_env_var, get_bool_env_var
import aiohttp

# 로깅 설정
logger = logging.getLogger(__name__)


class KISAPIClient:
    """한국투자증권 KIS API 클라이언트 클래스"""

    def __init__(self):
        """KIS API 클라이언트 초기화"""
        self.app_key = get_env_var("KIS_APP_KEY", "")
        self.app_secret = get_env_var("KIS_APP_SECRET", "")
        self.paper_trading = get_bool_env_var("KIS_PAPER_TRADING", True)
        
        # 실전/모의투자 URL 설정
        if self.paper_trading:
            self.api_url = "https://openapivts.koreainvestment.com:29443"
            self.ws_url = "ws://ops.koreainvestment.com:31000"
        else:
            self.api_url = "https://openapi.koreainvestment.com:9443"
            self.ws_url = "ws://ops.koreainvestment.com:21000"

        # 인증 토큰
        self.access_token = None
        self.approval_key = None
        self.token_expires_at = None

        # 웹소켓 관련
        self.ws = None
        self.ws_connected = False
        self.ws_callbacks = {}
        self.ws_thread = None

        # API 키 유효성 검사
        if not self.app_key or not self.app_secret:
            logger.warning("KIS API 키가 설정되지 않음")
        else:
            self._initialize_tokens()

    def _initialize_tokens(self) -> None:
        """토큰 초기화 (접근토큰, 승인키 발급)"""
        try:
            # 접근토큰 발급
            self._get_access_token()
            logger.info("KIS API 토큰 초기화 완료")

        except Exception as e:
            logger.error(f"KIS API 토큰 초기화 실패: {e}")

    def _get_access_token(self) -> None:
        """접근토큰 발급"""
        # 토큰이 유효한 경우 재사용
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                logger.info("기존 토큰이 유효하여 재사용")
                return
            else:
                logger.info("토큰이 만료되어 재발급 필요")
        
        url = f"{self.api_url}/oauth2/token"
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "Accept": "*/*"
        }
        params = {
            "grant_type": "client_credentials"
        }
        data = {
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            logger.info("토큰 발급 요청")
            
            # 토큰 발급 요청 전 1초 대기
            time.sleep(1)
            
            # form-urlencoded 형식으로 데이터 전송
            response = requests.post(url, headers=headers, params=params, data=data)
            
            # EGW00133 에러(rate limit)인 경우 60초 대기 후 재시도
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    if error_data.get("error_code") == "EGW00133":
                        logger.info("토큰 발급 속도 제한으로 60초 대기 후 재시도")
                        time.sleep(60)
                        response = requests.post(url, headers=headers, params=params, data=data)
                except:
                    pass
            
            response.raise_for_status()

            result = response.json()
            if "access_token" in result:
                self.access_token = result["access_token"]
                # 토큰 만료 시간 설정 (23시간)
                self.token_expires_at = datetime.now() + timedelta(hours=23)
                logger.info("접근토큰 발급 완료")
            else:
                raise Exception(
                    f"토큰 발급 실패: {result.get('msg1', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"접근토큰 발급 실패: {e}")
            raise

    def _revoke_approval_key(self) -> bool:
        """웹소켓 승인키 반납"""
        if not self.approval_key:
            return True

        url = f"{self.api_url}/oauth2/Approval"
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.delete(url, headers=headers)
            if response.status_code == 200:
                logger.info("승인키 반납 성공")
                self.approval_key = None
                return True
            else:
                # 404 에러는 이미 만료된 것으로 간주
                if response.status_code == 404:
                    logger.info("승인키가 이미 만료됨")
                    self.approval_key = None
                    return True
                logger.warning(f"승인키 반납 실패: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"승인키 반납 중 오류: {e}")
            return False

    def _get_approval_key(self, max_retries: int = 3) -> None:
        """웹소켓 승인키 발급"""
        # 기존 웹소켓 연결 해제
        self.disconnect_websocket()
        
        # 기존 승인키 반납
        if self.approval_key:
            self._revoke_approval_key()
            time.sleep(2)  # 반납 후 2초 대기

        url = f"{self.api_url}/oauth2/Approval"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret  # appsecret -> secretkey로 변경
        }

        for attempt in range(max_retries):
            try:
                logger.info(f"승인키 발급 시도 {attempt + 1}/{max_retries}")
                logger.info(f"요청 URL: {url}")
                logger.info(f"요청 헤더: {headers}")
                logger.info(f"요청 데이터: {data}")
                
                response = requests.post(url, headers=headers, json=data)
                
                logger.info(f"응답 상태 코드: {response.status_code}")
                logger.info(f"응답 헤더: {dict(response.headers)}")
                logger.info(f"응답 내용: {response.text}")
                
                if response.status_code == 403:
                    error_data = response.json()
                    error_code = error_data.get("error_code", "")
                    error_message = error_data.get("error_description", "")
                    
                    # 기존 승인키가 있는 경우
                    if error_code in ["EGW00121", "EGW00124"]:
                        logger.info(f"기존 승인키 존재 (시도 {attempt + 1}/{max_retries}): {error_message}")
                        # 강제로 기존 승인키 무효화
                        self._revoke_approval_key()
                        time.sleep(3)  # 3초 대기 후 재시도
                        continue
                    else:
                        logger.warning(f"알 수 없는 403 에러: {error_code} - {error_message}")
                
                response.raise_for_status()

                result = response.json()
                if "approval_key" in result:
                    self.approval_key = result["approval_key"]
                    logger.info("웹소켓 승인키 발급 완료")
                    return
                else:
                    raise Exception(f"승인키 발급 실패: {result.get('msg1', 'Unknown error')}")

            except Exception as e:
                logger.warning(f"승인키 발급 시도 {attempt + 1}/{max_retries} 실패: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(3)  # 재시도 전 3초 대기

    def _check_token_validity(self) -> None:
        """토큰 유효성 검사 및 갱신"""
        if not self.access_token or not self.token_expires_at:
            self._get_access_token()
        elif datetime.now() >= self.token_expires_at:
            logger.info("토큰 만료, 재발급 중...")
            self._get_access_token()

    def _get_headers(self, tr_id: str, tr_cont: str = "") -> Dict[str, str]:
        """API 요청 헤더 생성"""
        self._check_token_validity()

        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "tr_cont": tr_cont,
            "custtype": "P",
            "hashkey": ""
        }

    def get_current_price(self, stock_code: str) -> Optional[Dict]:
        """현재가 조회"""
        tr_id = "FHKST01010100"
        url = f"{self.api_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            result = response.json()
            if "output" in result:
                return result["output"]
            else:
                logger.warning(f"현재가 조회 실패: {result.get('msg1', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"현재가 조회 중 오류: {e}")
            return None

    async def get_daily_chart(self, stock_code: str, days: int = 30) -> List[Dict]:
        """일봉 차트 데이터 조회"""
        # 토큰 유효성 체크
        self._check_token_validity()

        tr_id = "FHKST03010100"
        url = f"{self.api_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        headers = self._get_headers(tr_id)

        # 조회 종료일 (오늘)
        end_date = datetime.now().strftime("%Y%m%d")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분
            "FID_INPUT_ISCD": stock_code,    # 종목코드
            "FID_PERIOD_DIV_CODE": "D",      # 기간분류(D:일봉)
            "FID_ORG_ADJ_PRC": "1",          # 수정주가 여부(1:수정주가)
            "FID_INPUT_DATE_1": "",          # 조회시작일자
            "FID_INPUT_DATE_2": end_date,    # 조회종료일자
            "FID_COMP_PRC_YN": "Y",          # 비교가격 여부
            "FID_UNIT_CLS": "D"              # 단위(D:일단위)
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_text = await response.text()
                    logger.info(f"일봉 차트 응답: {response_text}")

                    if response.status != 200:
                        logger.error(f"일봉 차트 조회 실패 - HTTP {response.status}")
                        return []

                    result = await response.json()
                    if result.get("rt_cd") != "0":
                        logger.error(f"일봉 차트 조회 실패: {result.get('msg1', 'Unknown error')}")
                        return []

                    daily_data = []
                    # 일봉 데이터는 output2에 배열 형태로 있음
                    output = result.get("output2", [])
                    if not output:
                        # fallback: output1 확인 (단일 데이터)
                        output = result.get("output1", [])
                        if isinstance(output, dict):  # 단일 데이터인 경우
                            output = [output]

                    for item in output:
                        daily_data.append({
                            "date": item.get("stck_bsop_date", ""),
                            "open": float(item.get("stck_oprc", 0)),
                            "high": float(item.get("stck_hgpr", 0)),
                            "low": float(item.get("stck_lwpr", 0)),
                            "close": float(item.get("stck_clpr", 0)),
                            "volume": int(item.get("acml_vol", 0))
                        })

                    logger.info(f"일봉 데이터 조회 완료: {stock_code}, {len(daily_data)}일")
                    return daily_data

        except Exception as e:
            logger.error(f"일봉 데이터 조회 실패: {e}")
            return []

    async def get_daily_chart_extended(self, stock_code: str, start_date: str = None, end_date: str = None, period: int = 500) -> List[Dict]:
        """확장된 일봉 차트 데이터 조회 (더 긴 기간 지원)
        
        Args:
            stock_code: 종목코드
            start_date: 조회 시작일 (YYYYMMDD) - 옵션
            end_date: 조회 종료일 (YYYYMMDD) - 기본값: 오늘
            period: 조회 기간 (일) - 기본값: 500일, 최대 1000일
        """
        # 토큰 유효성 체크
        self._check_token_validity()

        tr_id = "FHKST03010100"
        url = f"{self.api_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        headers = self._get_headers(tr_id)

        # 종료일 설정 (기본값: 오늘)
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        
        # 시작일 계산 (period 기준으로)
        if start_date is None:
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            # 영업일 기준으로 대략 계산 (주말 제외하여 1.4배)
            start_dt = end_dt - timedelta(days=int(period * 1.4))
            start_date = start_dt.strftime("%Y%m%d")

        # KIS API 파라미터 설정
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",      # 시장 구분
            "FID_INPUT_ISCD": stock_code,        # 종목코드
            "FID_PERIOD_DIV_CODE": "D",          # 기간분류(D:일봉)
            "FID_ORG_ADJ_PRC": "1",              # 수정주가 여부(1:수정주가)
            "FID_INPUT_DATE_1": start_date,      # 조회시작일자
            "FID_INPUT_DATE_2": end_date,        # 조회종료일자
            "FID_COMP_PRC_YN": "Y",              # 비교가격 여부
            "FID_UNIT_CLS": "D"                  # 단위(D:일단위)
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_text = await response.text()
                    logger.info(f"확장 일봉 차트 응답: {response_text[:500]}...")

                    if response.status != 200:
                        logger.error(f"확장 일봉 차트 조회 실패 - HTTP {response.status}")
                        return []

                    result = await response.json()
                    if result.get("rt_cd") != "0":
                        logger.error(f"확장 일봉 차트 조회 실패: {result.get('msg1', 'Unknown error')}")
                        return []

                    daily_data = []
                    # 일봉 데이터는 output2에 배열 형태로 있음
                    output = result.get("output2", [])
                    if not output:
                        # fallback: output1 확인 (단일 데이터)
                        output = result.get("output1", [])
                        if isinstance(output, dict):  # 단일 데이터인 경우
                            output = [output]

                    for item in output:
                        # 날짜 필터링 (시작일과 종료일 사이만)
                        item_date = item.get("stck_bsop_date", "")
                        if item_date and start_date <= item_date <= end_date:
                            daily_data.append({
                                "date": item_date,
                                "open": float(item.get("stck_oprc", 0)),
                                "high": float(item.get("stck_hgpr", 0)),
                                "low": float(item.get("stck_lwpr", 0)),
                                "close": float(item.get("stck_clpr", 0)),
                                "volume": int(item.get("acml_vol", 0))
                            })

                    logger.info(f"확장 일봉 데이터 조회 완료: {stock_code}, {len(daily_data)}일 ({start_date}~{end_date})")
                    return daily_data

        except Exception as e:
            logger.error(f"확장 일봉 데이터 조회 실패: {e}")
            return []

    def get_minute_chart(self, stock_code: str, time_unit: int = 1) -> List[Dict]:
        """분봉 차트 조회"""
        tr_id = "FHKST03010200"
        url = f"{self.api_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_HOUR_1": time_unit,
            "FID_PW_DATA_INCU_YN": "Y"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            result = response.json()
            if "output" in result:
                return result["output"]
            else:
                logger.warning(f"분봉 차트 조회 실패: {result.get('msg1', 'Unknown error')}")
                return []

        except Exception as e:
            logger.error(f"분봉 차트 조회 중 오류: {e}")
            return []

    def start_realtime_price(
        self, stock_code: str, callback: Callable[[Dict], None]
    ) -> bool:
        """실시간 시세 수신 시작"""
        try:
            # 웹소켓 연결이 없으면 연결
            if not self.ws_connected:
                # 승인키 발급 (기존 키 반납 포함)
                self._get_approval_key()
                # 웹소켓 연결
                self._connect_websocket()
                time.sleep(1)  # 연결 대기

            # 콜백 등록
            self.ws_callbacks[stock_code] = callback

            # 실시간 등록 요청
            register_data = {
                "header": {"approval_key": self.approval_key, "custtype": "P", "tr_type": "1"},
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0",  # 주식체결통보
                        "tr_key": stock_code   # 종목코드
                    }
                }
            }

            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(json.dumps(register_data))
                logger.info(f"실시간 시세 등록 요청 전송: {stock_code}")
                return True
            else:
                logger.error("웹소켓이 연결되지 않음")
                return False

        except Exception as e:
            logger.error(f"실시간 시세 등록 실패: {e}")
            return False

    def stop_realtime_price(self, stock_code: str) -> bool:
        """실시간 시세 수신 중단"""
        try:
            # 실시간 해제 요청
            unregister_data = {
                "header": {"approval_key": self.approval_key, "custtype": "P", "tr_type": "2"},
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0",  # 주식체결통보
                        "tr_key": stock_code   # 종목코드
                    }
                }
            }

            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(json.dumps(unregister_data))
                logger.info(f"실시간 시세 해제 요청 전송: {stock_code}")

                # 콜백 제거
                if stock_code in self.ws_callbacks:
                    del self.ws_callbacks[stock_code]

                # 더 이상 구독 중인 종목이 없으면 웹소켓 연결 해제
                if not self.ws_callbacks:
                    self.disconnect_websocket()
                
                return True
            else:
                logger.error("웹소켓이 연결되지 않음")
                return False

        except Exception as e:
            logger.error(f"실시간 시세 해제 실패: {e}")
            return False

    def _connect_websocket(self) -> None:
        """웹소켓 연결"""
        if self.ws_connected:
            logger.info("이미 웹소켓이 연결되어 있음")
            return

        def on_open(ws):
            logger.info("웹소켓 연결됨")
            self.ws_connected = True

        def on_message(ws, message):
            try:
                data = json.loads(message)
                self._process_realtime_data(data)
            except Exception as e:
                logger.error(f"웹소켓 메시지 처리 실패: {e}")

        def on_error(ws, error):
            logger.error(f"웹소켓 오류: {error}")
            self.ws_connected = False

        def on_close(ws, close_status_code, close_msg):
            logger.info(f"웹소켓 연결 종료 (상태 코드: {close_status_code}, 메시지: {close_msg})")
            self.ws_connected = False
            self.approval_key = None  # 연결 종료 시 승인키도 무효화

        # 웹소켓 객체 생성
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        # 웹소켓 연결 스레드 시작
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def _on_ws_open(self, ws) -> None:
        """웹소켓 연결 시 호출"""
        self.ws_connected = True
        logger.info("웹소켓 연결됨")

    def _on_ws_message(self, ws, message: str) -> None:
        """웹소켓 메시지 수신 시 호출"""
        try:
            # 메시지 파싱
            if message.startswith("{"):
                data = json.loads(message)
                self._process_realtime_data(data)
            else:
                # 파이프 구분자로 분리된 실시간 데이터
                parts = message.split("|")
                if len(parts) >= 3:
                    tr_id = parts[0]
                    stock_code = parts[1]
                    data_part = parts[2]

                    if tr_id == "H0STCNT0":  # 실시간 주식체결통보
                        self._process_price_data(stock_code, data_part)

        except Exception as e:
            logger.error(f"웹소켓 메시지 처리 에러: {e}")

    def _on_ws_error(self, ws, error) -> None:
        """웹소켓 에러 시 호출"""
        logger.error(f"웹소켓 에러: {error}")
        self.ws_connected = False

    def _on_ws_close(self, ws, close_status_code, close_msg) -> None:
        """웹소켓 종료 시 호출"""
        logger.info(f"웹소켓 연결 종료: {close_status_code}, {close_msg}")
        self.ws_connected = False

    def _process_realtime_data(self, data: Dict) -> None:
        """실시간 데이터 처리"""
        try:
            if "header" in data and "body" in data:
                tr_id = data["header"].get("tr_id")
                if tr_id == "H0STCNT0":
                    # 실시간 주가 데이터 처리
                    output = data["body"]["output"]
                    stock_code = output.get("mksc_shrn_iscd")

                    if stock_code in self.ws_callbacks:
                        price_data = {
                            "stock_code": stock_code,
                            "current_price": int(output.get("stck_prpr", 0)),
                            "change_rate": float(output.get("prdy_ctrt", 0)),
                            "change_amount": int(output.get("prdy_vrss", 0)),
                            "volume": int(output.get("acml_vol", 0)),
                            "timestamp": datetime.now(),
                        }

                        # 콜백 함수 호출
                        self.ws_callbacks[stock_code](price_data)

        except Exception as e:
            logger.error(f"실시간 데이터 처리 에러: {e}")

    def _process_price_data(self, stock_code: str, data_part: str) -> None:
        """실시간 주가 데이터 처리 (파이프 구분 형태)"""
        try:
            # 데이터 파싱 (실제 KIS API 응답 형식에 맞춰 조정 필요)
            fields = data_part.split("^")
            if len(fields) >= 10:
                price_data = {
                    "stock_code": stock_code,
                    "current_price": int(fields[2]) if fields[2] else 0,
                    "change_amount": int(fields[3]) if fields[3] else 0,
                    "change_rate": float(fields[4]) if fields[4] else 0.0,
                    "volume": int(fields[9]) if fields[9] else 0,
                    "timestamp": datetime.now(),
                }

                # 콜백 함수 호출
                if stock_code in self.ws_callbacks:
                    self.ws_callbacks[stock_code](price_data)

        except Exception as e:
            logger.error(f"실시간 주가 데이터 처리 에러: {e}")

    def disconnect_websocket(self) -> None:
        """웹소켓 연결 해제"""
        try:
            if self.ws and not self.ws.closed:
                self.ws.close()
                logger.info("웹소켓 연결 해제 완료")
            self.ws_connected = False
        except Exception as e:
            logger.error(f"웹소켓 연결 해제 중 오류: {e}")

    def get_market_status(self) -> Dict:
        """장 운영 시간 조회"""
        tr_id = "CTCA0903R"
        url = f"{self.api_url}/uapi/domestic-stock/v1/quotations/chk-holiday"
        headers = self._get_headers(tr_id)

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            result = response.json()
            if "output" in result:
                return result["output"]
            else:
                logger.warning(f"장 운영 시간 조회 실패: {result.get('msg1', 'Unknown error')}")
                return {}

        except Exception as e:
            logger.error(f"장 운영 시간 조회 중 오류: {e}")
            return {}

    def health_check(self) -> Dict:
        """API 서버 상태 확인"""
        try:
            # 토큰 유효성 검사
            self._check_token_validity()

            # 현재가 API로 상태 체크
            response = self.get_current_price("005930")  # 삼성전자
            if response:
                return {
                    "status": "healthy",
                    "message": "API 서버가 정상 작동 중입니다."
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "API 응답이 없습니다."
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"API 서버 상태 확인 중 오류: {e}"
            }


    # === 수급 분석을 위한 새로운 메서드들 ===
    
    def subscribe_program_trade_data(self, stock_code: str, callback: Callable):
        """
        프로그램 매매 데이터 실시간 구독
        
        Args:
            stock_code: 종목코드 (6자리)
            callback: 데이터 수신 콜백 함수
        """
        try:
            if not self.ws_connected:
                self.connect_websocket()
            
            # 프로그램 매매 데이터 구독 메시지
            subscribe_message = {
                "header": {
                    "approval_key": self.approval_key,
                    "custtype": "P",  # 개인
                    "tr_type": "1",   # 구독
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "H0STCNI0",  # 프로그램매매추이
                        "tr_key": stock_code
                    }
                }
            }
            
            # 콜백 등록
            callback_key = f"program_trade_{stock_code}"
            self.ws_callbacks[callback_key] = callback
            
            # 구독 메시지 전송
            if self.ws and self.ws_connected:
                self.ws.send(json.dumps(subscribe_message))
                logger.info(f"프로그램 매매 데이터 구독 시작: {stock_code}")
                return True
            else:
                logger.error("WebSocket 연결이 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"프로그램 매매 데이터 구독 실패: {e}")
            return False
    
    def get_program_trade_history(self, stock_code: str, period: int = 30) -> Dict:
        """
        과거 프로그램 매매 이력 조회 (최근 N일)
        
        Args:
            stock_code: 종목코드
            period: 조회 기간 (일)
            
        Returns:
            Dict: 프로그램 매매 이력 데이터
        """
        try:
            if not self.access_token:
                self.get_access_token()
            
            # 날짜 계산
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=period)).strftime("%Y%m%d")
            
            url = f"{self.api_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            
            headers = {
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST03010100"
            }
            
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": stock_code,
                "fid_input_date_1": start_date,
                "fid_input_date_2": end_date,
                "fid_period_div_code": "D",
                "fid_org_adj_prc": "1"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "data": data.get("output2", []),
                    "stock_code": stock_code,
                    "period": period
                }
            else:
                logger.error(f"프로그램 매매 이력 조회 실패: {response.status_code}")
                return {"status": "error", "message": "데이터 조회 실패"}
                
        except Exception as e:
            logger.error(f"프로그램 매매 이력 조회 오류: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_institutional_trading_data(self, stock_code: str, period: int = 30) -> Dict:
        """
        기관 매매 동향 조회
        
        Args:
            stock_code: 종목코드
            period: 조회 기간 (일)
            
        Returns:
            Dict: 기관 매매 동향 데이터
        """
        try:
            if not self.access_token:
                self.get_access_token()
            
            # 날짜 계산
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=period)).strftime("%Y%m%d")
            
            url = f"{self.api_url}/uapi/domestic-stock/v1/quotations/inquire-investor"
            
            headers = {
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010900"
            }
            
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": stock_code,
                "fid_input_date_1": start_date,
                "fid_input_date_2": end_date,
                "fid_etc_cls_code": "",
                "fid_input_cnt_1": str(period)
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "data": data.get("output", []),
                    "stock_code": stock_code,
                    "period": period
                }
            else:
                logger.error(f"기관 매매 동향 조회 실패: {response.status_code}")
                return {"status": "error", "message": "데이터 조회 실패"}
                
        except Exception as e:
            logger.error(f"기관 매매 동향 조회 오류: {e}")
            return {"status": "error", "message": str(e)}


# 전역 KIS API 클라이언트 인스턴스
kis_client = KISAPIClient()
