"""
빗썸 스타일 텔레그램 채널 관리 서비스
- 채널 기반 알림 시스템
- 관리봇을 통한 메시지 푸시
- 사용자별 구독 관리
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config


class TelegramChannelService:
    """빗썸 스타일 텔레그램 채널 관리 서비스"""

    def __init__(self):
        self.config = get_config()
        self.mysql_client = get_mysql_client()
        self.telegram_bot = TelegramBotClient()
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    async def get_channel_info(self, channel_id: int = 1) -> Optional[Dict]:
        """채널 정보 조회"""
        try:
            query = """
                SELECT * FROM telegram_channels 
                WHERE channel_id = %s AND is_active = TRUE
            """
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (channel_id,))
                channel = cursor.fetchone()
                
            return channel
            
        except Exception as e:
            self.logger.error(f"채널 정보 조회 실패: {e}")
            return None

    async def get_user_subscription(self, user_id: str, channel_id: int = 1) -> Optional[Dict]:
        """사용자 구독 설정 조회"""
        try:
            query = """
                SELECT * FROM user_telegram_subscriptions 
                WHERE user_id = %s AND channel_id = %s
            """
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (user_id, channel_id))
                subscription = cursor.fetchone()
                
            return subscription
            
        except Exception as e:
            self.logger.error(f"사용자 구독 설정 조회 실패: {e}")
            return None

    async def save_user_subscription(self, user_id: str, subscription_data: Dict) -> bool:
        """사용자 구독 설정 저장/업데이트"""
        try:
            query = """
                INSERT INTO user_telegram_subscriptions 
                (user_id, channel_id, news_alerts, disclosure_alerts, chart_alerts, 
                 price_alerts, weekly_reports, error_alerts, is_active, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                news_alerts = VALUES(news_alerts),
                disclosure_alerts = VALUES(disclosure_alerts),
                chart_alerts = VALUES(chart_alerts),
                price_alerts = VALUES(price_alerts),
                weekly_reports = VALUES(weekly_reports),
                error_alerts = VALUES(error_alerts),
                is_active = VALUES(is_active),
                updated_at = NOW()
            """
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    user_id,
                    subscription_data.get('channel_id', 1),
                    subscription_data.get('news_alerts', True),
                    subscription_data.get('disclosure_alerts', True),
                    subscription_data.get('chart_alerts', True),
                    subscription_data.get('price_alerts', True),
                    subscription_data.get('weekly_reports', False),
                    subscription_data.get('error_alerts', False),
                    subscription_data.get('is_active', True)
                ))
                conn.commit()
                
            self.logger.info(f"사용자 구독 설정 저장 완료: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"사용자 구독 설정 저장 실패: {e}")
            return False

    async def get_active_subscribers(self, notification_type: str) -> List[Dict]:
        """특정 알림 유형을 활성화한 구독자 목록 조회"""
        try:
            query = f"""
                SELECT user_id, {notification_type}
                FROM user_telegram_subscriptions 
                WHERE is_active = TRUE AND {notification_type} = TRUE
            """
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query)
                subscribers = cursor.fetchall()
                
            return subscribers
            
        except Exception as e:
            self.logger.error(f"활성 구독자 조회 실패: {e}")
            return []

    async def send_channel_message(self, message: str, notification_type: str = "general") -> bool:
        """채널에 메시지 전송 (빗썸 스타일)"""
        try:
            # 채널 정보 조회
            channel = await self.get_channel_info()
            if not channel:
                self.logger.error("활성 채널을 찾을 수 없음")
                return False

            # 빗썸 스타일 메시지 포맷팅
            formatted_message = self._format_bithumb_style_message(message, notification_type)
            
            # 채널에 메시지 전송
            success = self.telegram_bot.send_message(formatted_message)
            
            if success:
                # 알림 로그 저장
                await self._save_notification_log(channel['channel_id'], notification_type, message)
                self.logger.info(f"채널 메시지 전송 완료: {notification_type}")
            else:
                self.logger.error(f"채널 메시지 전송 실패: {notification_type}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"채널 메시지 전송 중 오류: {e}")
            return False

    def _format_bithumb_style_message(self, message: str, notification_type: str) -> str:
        """빗썸 스타일 메시지 포맷팅"""
        timestamp = datetime.now().strftime("%H:%M")
        
        # 알림 유형별 아이콘
        icons = {
            "news": "📰",
            "disclosure": "📢", 
            "chart": "📊",
            "price": "💰",
            "weekly_report": "📈",
            "error": "🚨",
            "general": "🔔"
        }
        
        icon = icons.get(notification_type, "🔔")
        
        # 빗썸 스타일 포맷
        formatted = f"""
{icon} <b>HyperAsset 실시간 알림</b>

{message}

⏰ {timestamp}
🔗 <a href="https://t.me/HyperAssetAlerts">채널 바로가기</a>

💡 <i>이 분석은 참고용이며, 투자 결정은 신중하게 하시기 바랍니다.</i>
        """.strip()
        
        return formatted

    async def _save_notification_log(self, channel_id: int, notification_type: str, message: str) -> None:
        """알림 로그 저장"""
        try:
            query = """
                INSERT INTO telegram_notification_logs 
                (channel_id, notification_type, message_content, sent_at, status)
                VALUES (%s, %s, %s, NOW(), 'sent')
            """
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (channel_id, notification_type, message))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"알림 로그 저장 실패: {e}")

    async def test_channel_connection(self) -> bool:
        """채널 연결 테스트"""
        try:
            test_message = "🔍 HyperAsset 채널 연결 테스트\n\n✅ 정상적으로 연결되었습니다!"
            return await self.send_channel_message(test_message, "general")
            
        except Exception as e:
            self.logger.error(f"채널 연결 테스트 실패: {e}")
            return False 