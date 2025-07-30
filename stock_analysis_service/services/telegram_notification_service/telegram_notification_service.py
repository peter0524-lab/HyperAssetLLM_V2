"""
빗썸 스타일 텔레그램 알림 서비스
기존 telegram_api.py의 인사이트를 바탕으로 간단하고 안정적인 알림 시스템
"""

import logging
import requests
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config


class TelegramNotificationService:
    """빗썸 스타일 텔레그램 알림 서비스"""

    def __init__(self):
        self.config = get_config()
        self.telegram_bot = TelegramBotClient()
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def send_welcome_message(self, username: str = "사용자") -> bool:
        """환영 메시지 전송 (빗썸 스타일)"""
        try:
            message = f"""
🎉 <b>HyperAsset 텔레그램 알림에 오신 것을 환영합니다!</b>

👋 안녕하세요, <b>{username}</b>님!

📱 이제 실시간 주식 알림을 받으실 수 있습니다:

• 📰 <b>실시간 뉴스 알림</b> - 중요한 뉴스가 발생하면 즉시 알림
• 📢 <b>중요 공시 정보</b> - 기업 공시 정보를 실시간으로 받아보세요  
• 📊 <b>차트 패턴 분석</b> - 기술적 분석 결과를 알림으로 받아보세요
• 💰 <b>가격 변동 알림</b> - 관심 종목의 가격 변동을 실시간으로

🔗 <a href="https://t.me/HyperAssetAlerts">채널 바로가기</a>

💡 <i>전문적인 주식 알림 서비스를 경험해보세요!</i>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            success = self.telegram_bot.send_message(message)
            
            if success:
                self.logger.info(f"환영 메시지 전송 완료: {username}")
            else:
                self.logger.error(f"환영 메시지 전송 실패: {username}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"환영 메시지 전송 중 오류: {e}")
            return False

    def send_test_message(self) -> bool:
        """테스트 메시지 전송 (빗썸 스타일)"""
        try:
            message = f"""
🧪 <b>HyperAsset 텔레그램 알림 테스트</b>

✅ 이 메시지가 보이면 채널 연결이 정상입니다!

🔧 <b>시스템 상태:</b>
• 봇 연결: ✅ 정상
• 채널 접근: ✅ 정상  
• 메시지 전송: ✅ 정상

📊 <b>테스트 정보:</b>
• 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• 서비스: HyperAsset 알림 시스템
• 버전: v1.0

🔗 <a href="https://t.me/HyperAssetAlerts">채널 바로가기</a>

💡 <i>실시간 알림 시스템이 준비되었습니다!</i>
            """.strip()
            
            success = self.telegram_bot.send_message(message)
            
            if success:
                self.logger.info("테스트 메시지 전송 완료")
            else:
                self.logger.error("테스트 메시지 전송 실패")
                
            return success
            
        except Exception as e:
            self.logger.error(f"테스트 메시지 전송 중 오류: {e}")
            return False

    def send_custom_message(self, message: str, notification_type: str = "general") -> bool:
        """커스텀 메시지 전송"""
        try:
            formatted_message = self._format_bithumb_style_message(message, notification_type)
            success = self.telegram_bot.send_message(formatted_message)
            
            if success:
                self.logger.info(f"커스텀 메시지 전송 완료: {notification_type}")
            else:
                self.logger.error(f"커스텀 메시지 전송 실패: {notification_type}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"커스텀 메시지 전송 중 오류: {e}")
            return False

    def _format_bithumb_style_message(self, message: str, notification_type: str) -> str:
        """빗썸 스타일 메시지 포맷팅"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 알림 유형에 따른 아이콘 설정
        icons = {
            "news": "📰",
            "disclosure": "📢", 
            "chart": "📊",
            "price": "💰",
            "alert": "🚨",
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "general": "🔔"
        }
        
        icon = icons.get(notification_type, "🔔")
        
        formatted_message = f"""
{icon} <b>HyperAsset 알림</b>

{message}

⏰ {timestamp}
🔗 <a href="https://t.me/HyperAssetAlerts">채널 바로가기</a>
        """.strip()
        
        return formatted_message

    def health_check(self) -> Dict[str, Any]:
        """헬스체크"""
        try:
            # 봇 정보 확인
            bot_info = self.telegram_bot.get_bot_info()
            
            if bot_info:
                return {
                    "status": "healthy",
                    "bot_username": bot_info.get("username"),
                    "bot_name": bot_info.get("first_name"),
                    "can_join_groups": bot_info.get("can_join_groups", False),
                    "can_read_all_group_messages": bot_info.get("can_read_all_group_messages", False)
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "봇 정보를 가져올 수 없습니다."
                }
                
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e)
            }


# 사용법:
# from services.telegram_notification_service.telegram_notification_service import TelegramNotificationService
# notification_service = TelegramNotificationService()
# success = notification_service.send_welcome_message("사용자명") 