"""
텔레그램 API 연결 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_env_var
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_telegram_config():
    """텔레그램 설정 확인"""
    bot_token = get_env_var("TELEGRAM_BOT_TOKEN", "")
    chat_id = get_env_var("TELEGRAM_CHAT_ID", "")
    
    print("📱 텔레그램 설정 확인:")
    print(f"   • 봇 토큰: {bot_token[:20]}...{bot_token[-10:] if len(bot_token) > 30 else bot_token}")
    print(f"   • 채팅 ID: {chat_id}")
    print()
    
    return bot_token, chat_id

def test_bot_info():
    """봇 정보 확인"""
    print("🤖 봇 정보 확인:")
    
    telegram_bot = TelegramBotClient()
    bot_info = telegram_bot.get_bot_info()
    
    if bot_info:
        print(f"   • 봇 이름: {bot_info.get('first_name', 'Unknown')}")
        print(f"   • 봇 사용자명: @{bot_info.get('username', 'Unknown')}")
        print(f"   • 봇 ID: {bot_info.get('id', 'Unknown')}")
        print("   ✅ 봇 정보 조회 성공")
    else:
        print("   ❌ 봇 정보 조회 실패")
    print()
    
    return bot_info is not None

def test_sync_message():
    """동기 메시지 전송 테스트"""
    print("📤 동기 메시지 전송 테스트:")
    
    telegram_bot = TelegramBotClient()
    test_message = "🧪 텔레그램 동기 메시지 테스트\n현재 시간: {}"
    
    from datetime import datetime
    formatted_message = test_message.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        result = telegram_bot.send_message(formatted_message)
        if result:
            print("   ✅ 동기 메시지 전송 성공")
        else:
            print("   ❌ 동기 메시지 전송 실패")
        return result
    except Exception as e:
        print(f"   ❌ 동기 메시지 전송 예외: {e}")
        return False

async def test_async_message():
    """비동기 메시지 전송 테스트"""
    print("📤 비동기 메시지 전송 테스트:")
    
    telegram_bot = TelegramBotClient()
    test_message = "🧪 텔레그램 비동기 메시지 테스트\n현재 시간: {}"
    
    from datetime import datetime
    formatted_message = test_message.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        result = await telegram_bot.send_message_async(formatted_message)
        if result:
            print("   ✅ 비동기 메시지 전송 성공")
        else:
            print("   ❌ 비동기 메시지 전송 실패")
        return result
    except Exception as e:
        print(f"   ❌ 비동기 메시지 전송 예외: {e}")
        return False

def test_health_check():
    """텔레그램 봇 상태 확인"""
    print("🏥 텔레그램 봇 상태 확인:")
    
    telegram_bot = TelegramBotClient()
    health_status = telegram_bot.health_check()
    
    print(f"   • 상태: {health_status.get('status', 'Unknown')}")
    print(f"   • 봇 토큰: {'설정됨' if health_status.get('bot_token_configured') else '미설정'}")
    print(f"   • 채팅 ID: {'설정됨' if health_status.get('chat_id_configured') else '미설정'}")
    print(f"   • 봇 정보 확인: {'성공' if health_status.get('bot_info_available') else '실패'}")
    print()
    
    return health_status.get('status') == 'healthy'

async def main():
    """메인 테스트 함수"""
    print("🚀 텔레그램 API 연결 테스트 시작")
    print("=" * 50)
    
    # 1. 설정 확인
    bot_token, chat_id = test_telegram_config()
    
    if not bot_token or not chat_id:
        print("❌ 텔레그램 설정이 올바르지 않습니다.")
        print("   봇 토큰과 채팅 ID를 확인해주세요.")
        return
    
    # 2. 봇 정보 확인
    bot_info_ok = test_bot_info()
    
    if not bot_info_ok:
        print("❌ 봇 정보 조회 실패. 토큰을 확인해주세요.")
        return
    
    # 3. 상태 확인
    health_ok = test_health_check()
    
    if not health_ok:
        print("❌ 텔레그램 봇 상태 이상")
        return
    
    # 4. 동기 메시지 테스트
    sync_result = test_sync_message()
    
    # 5. 비동기 메시지 테스트
    async_result = await test_async_message()
    
    # 6. 결과 요약
    print("📊 테스트 결과 요약:")
    print(f"   • 봇 정보 확인: {'✅' if bot_info_ok else '❌'}")
    print(f"   • 상태 확인: {'✅' if health_ok else '❌'}")
    print(f"   • 동기 메시지: {'✅' if sync_result else '❌'}")
    print(f"   • 비동기 메시지: {'✅' if async_result else '❌'}")
    print()
    
    if sync_result and async_result:
        print("🎉 모든 테스트 통과! 텔레그램 API 연결이 정상입니다.")
    else:
        print("⚠️ 일부 테스트 실패. 로그를 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(main()) 