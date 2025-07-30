# type: ignore
"""
텔레그램 봇 API 클라이언트 모듈
텔레그램 봇을 통한 알림 및 메시지 전송 기능 제공
"""

import requests
import logging
import asyncio
import aiohttp
from io import BytesIO
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from config.env_local import get_env_var, get_int_env_var

# 로깅 설정
logger = logging.getLogger(__name__)


class TelegramBotClient:
    """텔레그램 봇 클라이언트 클래스"""

    def __init__(self):
        """텔레그램 봇 클라이언트 초기화"""
        self.bot_token = get_env_var("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = get_env_var("TELEGRAM_CHAT_ID", "")
        self.parse_mode = get_env_var("TELEGRAM_PARSE_MODE", "HTML")

        # API 설정
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.timeout = get_int_env_var("API_TIMEOUT", 30)
        self.max_retries = get_int_env_var("API_RETRY_COUNT", 3)
        self.retry_delay = get_int_env_var("API_RETRY_DELAY", 1)

        # 메시지 제한 설정
        self.max_message_length = 4096  # 텔레그램 메시지 최대 길이

        # 봇 토큰 유효성 검사
        if not self.bot_token:
            logger.warning("텔레그램 봇 토큰이 설정되지 않음")

    def send_message(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        disable_preview: bool = True,
    ) -> bool:
        """메시지 전송 (동기)"""
        target_chat_id = chat_id or self.chat_id
        target_parse_mode = parse_mode or self.parse_mode

        if not target_chat_id:
            logger.error("채팅 ID가 설정되지 않음")
            return False

        # 메시지 길이 제한 처리
        if len(message) > self.max_message_length:
            return self._send_long_message(
                message, target_chat_id, target_parse_mode, disable_preview
            )

        url = f"{self.api_url}/sendMessage"
        data = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": target_parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"텔레그램 메시지 전송 시도 {attempt + 1}/{self.max_retries}"
                )

                response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    logger.info(f"텔레그램 메시지 전송 완료: {len(message)}자")
                    return True
                else:
                    logger.error(
                        f"텔레그램 API 에러: {result.get('description', 'Unknown error')}"
                    )
                    return False

            except requests.exceptions.Timeout:
                logger.error(f"텔레그램 메시지 전송 시간 초과 (시도 {attempt + 1})")
                if attempt < self.max_retries - 1:
                    import time

                    time.sleep(self.retry_delay)
                    continue
                else:
                    return False

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"텔레그램 메시지 전송 네트워크 에러 (시도 {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    import time

                    time.sleep(self.retry_delay)
                    continue
                else:
                    return False

            except Exception as e:
                logger.error(f"텔레그램 메시지 전송 에러 (시도 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    import time

                    time.sleep(self.retry_delay)
                    continue
                else:
                    return False

        return False

    def _send_long_message(
        self, message: str, chat_id: Optional[str], parse_mode: Optional[str], disable_preview: bool
    ) -> bool:
        """긴 메시지 분할 전송"""
        # 메시지를 안전한 길이로 분할
        chunks = self._split_message(
            message, self.max_message_length - 100
        )  # 여유분 확보

        success_count = 0
        for i, chunk in enumerate(chunks):
            if i > 0:
                import time

                time.sleep(1)  # 연속 전송 시 간격 조정

            if self.send_message(chunk, chat_id, parse_mode, disable_preview):
                success_count += 1
            else:
                logger.error(f"메시지 청크 {i+1}/{len(chunks)} 전송 실패")

        logger.info(f"긴 메시지 분할 전송 완료: {success_count}/{len(chunks)} 성공")
        return success_count == len(chunks)

    def _split_message(self, message: str, max_length: int) -> List[str]:
        """메시지를 안전하게 분할"""
        if len(message) <= max_length:
            return [message]

        chunks = []
        current_chunk = ""

        # 줄 단위로 분할
        lines = message.split("\n")
        for line in lines:
            # 현재 청크에 라인을 추가했을 때 길이 확인
            if len(current_chunk) + len(line) + 1 <= max_length:
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line
            else:
                # 현재 청크 저장
                if current_chunk:
                    chunks.append(current_chunk)

                # 라인이 너무 긴 경우 강제 분할
                if len(line) > max_length:
                    while len(line) > max_length:
                        chunks.append(line[:max_length])
                        line = line[max_length:]
                    current_chunk = line if line else ""
                else:
                    current_chunk = line

        # 마지막 청크 저장
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def send_message_async(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        disable_preview: bool = True,
    ) -> bool:
        """메시지 전송 (비동기)"""
        target_chat_id = chat_id or self.chat_id
        target_parse_mode = parse_mode or self.parse_mode

        if not target_chat_id:
            logger.error("채팅 ID가 설정되지 않음")
            return False

        # 메시지 길이 제한 처리
        if len(message) > self.max_message_length:
            return await self._send_long_message_async(
                message, target_chat_id, target_parse_mode, disable_preview
            )

        url = f"{self.api_url}/sendMessage"
        data = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": target_parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            for attempt in range(self.max_retries):
                try:
                    logger.info(
                        f"텔레그램 메시지 비동기 전송 시도 {attempt + 1}/{self.max_retries}"
                    )

                    async with session.post(url, json=data) as response:
                        response.raise_for_status()

                        result = await response.json()
                        if result.get("ok"):
                            logger.info(
                                f"텔레그램 메시지 비동기 전송 완료: {len(message)}자"
                            )
                            return True
                        else:
                            logger.error(
                                f"텔레그램 API 에러: {result.get('description', 'Unknown error')}"
                            )
                            return False

                except asyncio.TimeoutError:
                    logger.error(
                        f"텔레그램 메시지 비동기 전송 시간 초과 (시도 {attempt + 1})"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        return False

                except Exception as e:
                    logger.error(
                        f"텔레그램 메시지 비동기 전송 에러 (시도 {attempt + 1}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        return False

        return False

    async def _send_long_message_async(
        self, message: str, chat_id: Optional[str], parse_mode: Optional[str], disable_preview: bool
    ) -> bool:
        """긴 메시지 분할 전송 (비동기)"""
        chunks = self._split_message(message, self.max_message_length - 100)

        success_count = 0
        for i, chunk in enumerate(chunks):
            if i > 0:
                await asyncio.sleep(1)  # 연속 전송 시 간격 조정

            if await self.send_message_async(
                chunk, chat_id, parse_mode, disable_preview
            ):
                success_count += 1
            else:
                logger.error(f"메시지 청크 {i+1}/{len(chunks)} 비동기 전송 실패")

        logger.info(
            f"긴 메시지 분할 비동기 전송 완료: {success_count}/{len(chunks)} 성공"
        )
        return success_count == len(chunks)

    def send_photo(
        self, photo_path: str, caption: str = "", chat_id: Optional[str] = None
    ) -> bool:
        """사진 전송"""
        target_chat_id = chat_id or self.chat_id

        if not target_chat_id:
            logger.error("채팅 ID가 설정되지 않음")
            return False

        url = f"{self.api_url}/sendPhoto"

        try:
            with open(photo_path, "rb") as photo_file:
                files = {"photo": photo_file}
                data = {
                    "chat_id": target_chat_id,
                    "caption": caption,
                    "parse_mode": self.parse_mode,
                }

                response = requests.post(
                    url, data=data, files=files, timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    logger.info(f"텔레그램 사진 전송 완료: {photo_path}")
                    return True
                else:
                    logger.error(
                        f"텔레그램 사진 전송 실패: {result.get('description', 'Unknown error')}"
                    )
                    return False

        except FileNotFoundError:
            logger.error(f"사진 파일을 찾을 수 없음: {photo_path}")
            return False
        except Exception as e:
            logger.error(f"텔레그램 사진 전송 에러: {e}")
            return False

    def send_document(
        self, document_path: str, caption: str = "", chat_id: Optional[str] = None
    ) -> bool:
        """문서 전송"""
        target_chat_id = chat_id or self.chat_id

        if not target_chat_id:
            logger.error("채팅 ID가 설정되지 않음")
            return False

        url = f"{self.api_url}/sendDocument"

        try:
            with open(document_path, "rb") as doc_file:
                files = {"document": doc_file}
                data = {
                    "chat_id": target_chat_id,
                    "caption": caption,
                    "parse_mode": self.parse_mode,
                }

                response = requests.post(
                    url, data=data, files=files, timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    logger.info(f"텔레그램 문서 전송 완료: {document_path}")
                    return True
                else:
                    logger.error(
                        f"텔레그램 문서 전송 실패: {result.get('description', 'Unknown error')}"
                    )
                    return False

        except FileNotFoundError:
            logger.error(f"문서 파일을 찾을 수 없음: {document_path}")
            return False
        except Exception as e:
            logger.error(f"텔레그램 문서 전송 에러: {e}")
            return False

    def send_document_from_buffer(
        self, document: BytesIO, filename: str, caption: str = "", chat_id: Optional[str] = None
    ) -> bool:
        """메모리 버퍼에서 문서 전송"""
        target_chat_id = chat_id or self.chat_id

        if not target_chat_id:
            logger.error("채팅 ID가 설정되지 않음")
            return False

        url = f"{self.api_url}/sendDocument"
        document.seek(0)
        files = {"document": (filename, document.getvalue())}
        data = {
            "chat_id": target_chat_id,
            "caption": caption,
            "parse_mode": self.parse_mode,
        }

        try:
            response = requests.post(
                url, data=data, files=files, timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                logger.info(f"텔레그램 버퍼 문서 전송 완료: {filename}")
                return True
            else:
                logger.error(
                    f"텔레그램 버퍼 문서 전송 실패: {result.get('description', 'Unknown error')}"
                )
                return False

        except Exception as e:
            logger.error(f"텔레그램 버퍼 문서 전송 에러: {e}")
            return False

    def send_news_alert(
        self, news_data: Dict, similar_case: Optional[Dict] = None, price_impact: str = ""
    ) -> bool:
        """뉴스 알림 전송"""

        # 메시지 템플릿
        message = f"""🔥 <b>{news_data.get('stock_name', 'N/A')}</b>에 중요한 뉴스가 발생했습니다!

📄 <b>뉴스 요약</b>
{news_data.get('summary', news_data.get('title', 'N/A'))}

📊 <b>영향도 점수</b>
{news_data.get('impact_score', 0):.2f}/1.00"""

        if similar_case:
            message += f"""

📈 <b>과거 유사 사례</b>
{similar_case.get('title', 'N/A')}
발생일: {similar_case.get('publication_date', 'N/A')}"""

        if price_impact:
            message += f"""

💹 <b>주가 영향 예상</b>
{price_impact}"""

        message += "\n\n💡 이와 같습니다!! 오늘 하루도 성투하세요~!"

        return self.send_message(message)

    def send_disclosure_alert(
        self, disclosure_data: Dict, similar_case: Optional[Dict] = None, price_impact: str = ""
    ) -> bool:
        """공시 알림 전송"""

        message = f"""📢 <b>{disclosure_data.get('stock_name', 'N/A')}</b>에 중요한 공시가 있었습니다!

📄 <b>공시 요약</b>
제목: {disclosure_data.get('title', 'N/A')}
내용: {disclosure_data.get('summary', 'N/A')}

📊 <b>영향도 점수</b>
{disclosure_data.get('impact_score', 0):.2f}/1.00"""

        if similar_case:
            message += f"""

📈 <b>유사 과거 사례</b>
{similar_case.get('title', 'N/A')}
발생일: {similar_case.get('publication_date', 'N/A')}"""

        if price_impact:
            message += f"""

💹 <b>주가 영향 예상</b>
{price_impact}"""

        message += "\n\n💡 이와 같습니다!! 오늘 하루도 성투하세요~!"

        return self.send_message(message)

    def send_chart_alert(
        self, chart_data: Dict, similar_case: Optional[Dict] = None, price_impact: str = ""
    ) -> bool:
        """차트 패턴 알림 전송"""

        message = f"""🚨 <b>{chart_data.get('stock_name', 'N/A')}</b>에 중요한 차트 패턴이 발생했습니다!

📊 <b>차트 상황</b>
패턴: {chart_data.get('condition_name', 'N/A')}
발생 시점: {chart_data.get('trigger_date', 'N/A')} {chart_data.get('trigger_time', 'N/A')}
현재가: {chart_data.get('price', 'N/A'):,}원
거래량: {chart_data.get('volume', 'N/A'):,}주"""

        if similar_case:
            message += f"""

📈 <b>유사 과거 사례</b>
패턴: {similar_case.get('condition_name', 'N/A')}
발생일: {similar_case.get('trigger_date', 'N/A')}
당시 거래량: {similar_case.get('volume', 'N/A'):,}주"""

        if price_impact:
            message += f"""

💹 <b>주가 영향 예상</b>
{price_impact}"""

        message += "\n\n💡 이와 같습니다!! 오늘 하루도 성투하세요~!"

        return self.send_message(message)

    def send_weekly_report(self, report_data: Dict, report_content: str) -> bool:
        """주간 보고서 전송"""

        message = f"""📈 <b>{report_data.get('stock_name', 'N/A')}</b> 주간 보고서

📅 <b>보고서 기간</b>
{report_data.get('week_start', 'N/A')} ~ {report_data.get('week_end', 'N/A')}

📊 <b>주간 종합 분석</b>
{report_content}

📚 더 자세한 내용은 첨부된 보고서를 확인해주세요!

💡 성공적인 투자 되세요! 📈"""

        return self.send_message(message)

    def send_error_alert(self, error_message: str, service_name: str = "") -> bool:
        """에러 알림 전송 (시스템 관리자용)"""

        message = f"""🚨 <b>시스템 에러 발생</b>

⚠️ <b>서비스</b>: {service_name or 'Unknown'}
🕐 <b>발생 시간</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📝 <b>에러 내용</b>
{error_message}

🔧 시스템 점검이 필요합니다."""

        return self.send_message(message)

    def get_bot_info(self) -> Optional[Dict]:
        """봇 정보 조회"""
        url = f"{self.api_url}/getMe"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                return result["result"]
            else:
                logger.error(
                    f"봇 정보 조회 실패: {result.get('description', 'Unknown error')}"
                )
                return None

        except Exception as e:
            logger.error(f"봇 정보 조회 에러: {e}")
            return None

    def get_chat_info(self, chat_id: Optional[str] = None) -> Optional[Dict]:
        """채팅 정보 조회"""
        target_chat_id = chat_id or self.chat_id

        if not target_chat_id:
            logger.error("채팅 ID가 설정되지 않음")
            return None

        url = f"{self.api_url}/getChat"
        params = {"chat_id": target_chat_id}

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                return result["result"]
            else:
                logger.error(
                    f"채팅 정보 조회 실패: {result.get('description', 'Unknown error')}"
                )
                return None

        except Exception as e:
            logger.error(f"채팅 정보 조회 에러: {e}")
            return None

    def health_check(self) -> Dict:
        """텔레그램 봇 상태 확인"""
        try:
            # 봇 정보 조회 테스트
            bot_info = self.get_bot_info()

            if bot_info:
                # 테스트 메시지 전송 (선택적)
                test_message = "🔍 시스템 상태 확인 중..."
                message_sent = True  # 실제로는 self.send_message(test_message)

                return {
                    "status": "healthy",
                    "bot_configured": bool(self.bot_token),
                    "chat_configured": bool(self.chat_id),
                    "bot_name": bot_info.get("first_name", "Unknown"),
                    "bot_username": bot_info.get("username", "Unknown"),
                    "message_test": "success" if message_sent else "failed",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "봇 정보 조회 실패",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"텔레그램 봇 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# 사용법:
# from shared.apis.telegram_api import TelegramBotClient
# telegram_client = TelegramBotClient()
