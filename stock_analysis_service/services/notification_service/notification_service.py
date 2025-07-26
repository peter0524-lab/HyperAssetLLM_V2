"""
알림 서비스 (Notification Service)
- 텔레그램 봇을 통한 통합 알림 전송
- 메시지 템플릿 관리
- 알림 우선순위 및 스케줄링
- 알림 히스토리 관리
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import sys
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config


class NotificationLevel(Enum):
    """알림 우선순위 레벨"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationService:
    """알림 서비스 클래스"""

    def __init__(self, config: Dict):
        self.config = config
        self.mysql_client = get_mysql_client()
        self.telegram_bot = TelegramBotClient()

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 알림 큐
        self.notification_queue = asyncio.Queue()

        # 메시지 템플릿
        self.message_templates = {
            "news_alert": {
                "title": "📰 뉴스 알림",
                "template": """
📰 **뉴스 알림**

🏷️ **종목**: {stock_code} - {company_name}
📅 **날짜**: {date}
⭐ **영향도**: {impact_score}/1.0

📝 **제목**: {title}

📊 **요약**: {summary}

🔍 **키워드**: {keywords}

📈 **과거 사례**: {similar_cases}
                """,
            },
            "disclosure_alert": {
                "title": "📢 공시 알림",
                "template": """
📢 **공시 알림**

🏢 **기업**: {company_name}
📋 **공시명**: {report_name}
📅 **공시일**: {date}
⭐ **영향도**: {impact_score}/1.0
📈 **영향 방향**: {impact_direction}

📝 **요약**: {summary}

🔍 **키워드**: {keywords}
                """,
            },
            "chart_alert": {
                "title": "📊 차트 알림",
                "template": """
📊 **차트 조건 만족 알림**

🏷️ **종목**: {stock_code}
💰 **현재가**: {current_price:,}원
📈 **거래량**: {current_volume:,}주
⏰ **시간**: {timestamp}

🔔 **만족 조건**:
{conditions}
                """,
            },
            "weekly_report": {
                "title": "📋 주간 보고서",
                "template": """
📋 **주간 보고서**

📅 **기간**: {start_date} ~ {end_date}

📊 **종목 분석**:
{stock_analysis}

📰 **주요 뉴스**:
{major_news}

📋 **중요 공시**:
{major_disclosures}

🔍 **핵심 키워드**:
{key_keywords}

📈 **시장 전망**:
{market_outlook}
                """,
            },
            "analysis_alert": {
                "title": "🔍 원인 분석",
                "template": """
🔍 **주가 급등락 원인 분석**

🏷️ **종목**: {stock_code} - {company_name}
📊 **변동률**: {change_rate}%
💰 **현재가**: {current_price:,}원
📈 **거래량**: {volume:,}주

🔍 **원인 분석**:
{analysis_result}

📰 **관련 뉴스**:
{related_news}

📋 **관련 공시**:
{related_disclosures}

📊 **유사 사례**:
{similar_cases}
                """,
            },
            "system_alert": {
                "title": "⚠️ 시스템 알림",
                "template": """
⚠️ **시스템 알림**

🔧 **서비스**: {service_name}
📊 **상태**: {status}
⏰ **시간**: {timestamp}

📝 **메시지**: {message}

🔍 **상세 정보**: {details}
                """,
            },
            "error_alert": {
                "title": "🚨 오류 알림",
                "template": """
🚨 **오류 알림**

🔧 **서비스**: {service_name}
❌ **오류 유형**: {error_type}
⏰ **발생 시간**: {timestamp}

📝 **오류 메시지**: {error_message}

🔍 **스택 트레이스**: {stack_trace}

🔧 **해결 방법**: {resolution}
                """,
            },
        }

    async def initialize_database(self):
        """데이터베이스 초기화"""
        try:
            # 알림 히스토리 테이블 생성
            create_notification_history_table = """
            CREATE TABLE IF NOT EXISTS notification_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                notification_type VARCHAR(50) NOT NULL,
                level VARCHAR(20) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                recipient VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                INDEX idx_notification_type (notification_type),
                INDEX idx_level (level),
                INDEX idx_sent_at (sent_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """

            # 알림 설정 테이블 생성
            create_notification_settings_table = """
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                min_level VARCHAR(20) DEFAULT 'medium',
                schedule_settings JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_type (user_id, notification_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """

            await self.mysql_client.execute_query_async(
                create_notification_history_table
            )
            await self.mysql_client.execute_query_async(
                create_notification_settings_table
            )

            self.logger.info("알림 서비스 데이터베이스 초기화 완료")

        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    async def format_message(self, template_name: str, data: Dict) -> str:
        """메시지 템플릿 포맷팅"""
        try:
            template = self.message_templates.get(template_name)
            if not template:
                return f"템플릿 없음: {template_name}"

            # 템플릿 데이터 포맷팅
            formatted_message = template["template"].format(**data)

            return formatted_message

        except Exception as e:
            self.logger.error(f"메시지 포맷팅 실패: {e}")
            return f"메시지 포맷팅 오류: {str(e)}"

    async def send_notification(
        self,
        notification_type: str,
        level: NotificationLevel,
        data: Dict,
        recipient: Optional[str] = None,
    ):
        """알림 전송"""
        try:
            # 메시지 포맷팅
            formatted_message = await self.format_message(notification_type, data)

            # 수신자 설정
            if not recipient:
                recipient = str(self.config.get("telegram", {}).get("chat_id", ""))

            # 텔레그램 전송
            self.telegram_bot.send_message(formatted_message, str(recipient))

            # 히스토리 저장
            await self.save_notification_history(
                notification_type=notification_type,
                level=level.value,
                title=self.message_templates.get(notification_type, {}).get(
                    "title", "알림"
                ),
                message=formatted_message,
                recipient=str(recipient) if recipient is not None else "unknown",
                status="sent",
                metadata=data,
            )

            self.logger.info(f"알림 전송 완료: {notification_type}, {level.value}")

        except Exception as e:
            self.logger.error(f"알림 전송 실패: {e}")

            # 실패 히스토리 저장
            await self.save_notification_history(
                notification_type=notification_type,
                level=level.value,
                title=self.message_templates.get(notification_type, {}).get(
                    "title", "알림"
                ),
                message=f"전송 실패: {str(e)}",
                recipient=str(recipient) if recipient is not None else "unknown",
                status="failed",
                metadata=data,
            )

    async def save_notification_history(
        self,
        notification_type: str,
        level: str,
        title: str,
        message: str,
        recipient: str,
        status: str,
        metadata: Dict,
    ):
        """알림 히스토리 저장"""
        try:
            insert_query = """
            INSERT INTO notification_history 
            (notification_type, level, title, message, recipient, status, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            await self.mysql_client.execute_query_async(
                insert_query,
                (
                    notification_type,
                    level,
                    title,
                    message,
                    recipient,
                    status,
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )

        except Exception as e:
            self.logger.error(f"알림 히스토리 저장 실패: {e}")

    async def send_news_alert(self, news_data: Dict):
        """뉴스 알림 전송"""
        try:
            await self.send_notification(
                notification_type="news_alert",
                level=NotificationLevel.HIGH,
                data=news_data,
            )

        except Exception as e:
            self.logger.error(f"뉴스 알림 전송 실패: {e}")

    async def send_disclosure_alert(self, disclosure_data: Dict):
        """공시 알림 전송"""
        try:
            await self.send_notification(
                notification_type="disclosure_alert",
                level=NotificationLevel.HIGH,
                data=disclosure_data,
            )

        except Exception as e:
            self.logger.error(f"공시 알림 전송 실패: {e}")

    async def send_chart_alert(self, chart_data: Dict):
        """차트 알림 전송"""
        try:
            await self.send_notification(
                notification_type="chart_alert",
                level=NotificationLevel.MEDIUM,
                data=chart_data,
            )

        except Exception as e:
            self.logger.error(f"차트 알림 전송 실패: {e}")

    async def send_weekly_report(self, report_data: Dict):
        """주간 보고서 전송"""
        try:
            await self.send_notification(
                notification_type="weekly_report",
                level=NotificationLevel.MEDIUM,
                data=report_data,
            )

        except Exception as e:
            self.logger.error(f"주간 보고서 전송 실패: {e}")

    async def send_analysis_alert(self, analysis_data: Dict):
        """원인 분석 알림 전송"""
        try:
            await self.send_notification(
                notification_type="analysis_alert",
                level=NotificationLevel.HIGH,
                data=analysis_data,
            )

        except Exception as e:
            self.logger.error(f"원인 분석 알림 전송 실패: {e}")

    async def send_system_alert(self, system_data: Dict):
        """시스템 알림 전송"""
        try:
            await self.send_notification(
                notification_type="system_alert",
                level=NotificationLevel.LOW,
                data=system_data,
            )

        except Exception as e:
            self.logger.error(f"시스템 알림 전송 실패: {e}")

    async def send_error_alert(self, error_data: Dict):
        """오류 알림 전송"""
        try:
            await self.send_notification(
                notification_type="error_alert",
                level=NotificationLevel.CRITICAL,
                data=error_data,
            )

        except Exception as e:
            self.logger.error(f"오류 알림 전송 실패: {e}")

    async def process_notification_queue(self):
        """알림 큐 처리"""
        try:
            while True:
                try:
                    # 큐에서 알림 가져오기
                    notification_data = await asyncio.wait_for(
                        self.notification_queue.get(), timeout=1.0
                    )

                    # 알림 타입에 따른 처리
                    notification_type = notification_data.get("type")
                    data = notification_data.get("data", {})

                    if notification_type == "news":
                        await self.send_news_alert(data)
                    elif notification_type == "disclosure":
                        await self.send_disclosure_alert(data)
                    elif notification_type == "chart":
                        await self.send_chart_alert(data)
                    elif notification_type == "weekly_report":
                        await self.send_weekly_report(data)
                    elif notification_type == "analysis":
                        await self.send_analysis_alert(data)
                    elif notification_type == "system":
                        await self.send_system_alert(data)
                    elif notification_type == "error":
                        await self.send_error_alert(data)

                    # 큐 작업 완료 표시
                    self.notification_queue.task_done()

                except asyncio.TimeoutError:
                    # 타임아웃 시 계속 진행
                    continue
                except Exception as e:
                    self.logger.error(f"알림 큐 처리 실패: {e}")
                    await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"알림 큐 처리 중단: {e}")

    async def add_notification_to_queue(self, notification_type: str, data: Dict):
        """알림 큐에 추가"""
        try:
            await self.notification_queue.put(
                {
                    "type": notification_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            self.logger.error(f"알림 큐 추가 실패: {e}")

    async def get_notification_history(
        self,
        limit: int = 100,
        notification_type: Optional[str] = None,
        level: Optional[str] = None,
    ) -> List[Dict]:
        """알림 히스토리 조회"""
        try:
            query = "SELECT * FROM notification_history WHERE 1=1"
            params = []

            if notification_type:
                query += " AND notification_type = %s"
                params.append(notification_type)

            if level:
                query += " AND level = %s"
                params.append(level)

            query += " ORDER BY sent_at DESC LIMIT %s"
            params.append(limit)

            history = self.mysql_client.fetch_all(query, tuple(params))
            return history

        except Exception as e:
            self.logger.error(f"알림 히스토리 조회 실패: {e}")
            return []

    async def cleanup_old_notifications(self, days: int = 30):
        """오래된 알림 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            delete_query = """
            DELETE FROM notification_history 
            WHERE sent_at < %s
            """

            await self.mysql_client.execute_query_async(
                delete_query, (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
            )

            self.logger.info(f"오래된 알림 정리 완료: {days}일 이전")

        except Exception as e:
            self.logger.error(f"오래된 알림 정리 실패: {e}")

    async def run_service(self):
        """알림 서비스 실행"""
        try:
            self.logger.info("알림 서비스 시작")

            # 데이터베이스 초기화
            await self.initialize_database()

            # 알림 큐 처리 태스크 시작
            queue_task = asyncio.create_task(self.process_notification_queue())

            # 실행 루프
            while True:
                try:
                    # 24시간마다 오래된 알림 정리
                    await self.cleanup_old_notifications()

                    # 24시간 대기
                    await asyncio.sleep(86400)

                except KeyboardInterrupt:
                    self.logger.info("서비스 중단 요청")
                    break
                except Exception as e:
                    self.logger.error(f"서비스 실행 오류: {e}")
                    await asyncio.sleep(60)

            # 태스크 정리
            queue_task.cancel()

        except Exception as e:
            self.logger.error(f"알림 서비스 실행 실패: {e}")
            raise
        finally:
            # 리소스 정리
            self.mysql_client.close()


async def main():
    """메인 실행 함수"""
    try:
        # 알림 서비스 실행
        notification_service = NotificationService(get_config())
        await notification_service.run_service()

    except KeyboardInterrupt:
        print("서비스 중단")
    except Exception as e:
        print(f"서비스 실행 실패: {e}")


if __name__ == "__main__":
    asyncio.run(main())
