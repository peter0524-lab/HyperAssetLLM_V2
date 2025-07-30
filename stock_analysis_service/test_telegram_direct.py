#!/usr/bin/env python3
"""
텔레그램 봇 직접 테스트 스크립트
실제로 텔레그램 채팅방에 메시지가 오는지 확인
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.apis.telegram_api import TelegramBotClient

async def test_telegram_direct():
    """텔레그램 봇 직접 테스트"""
    try:
        print("🚀 텔레그램 봇 직접 테스트 시작")
        
        # 텔레그램 봇 클라이언트 생성
        telegram_bot = TelegramBotClient()
        
        # 테스트 메시지
        test_message = """
🔔 **테스트 알림** 🔔

📊 **서비스**: 테스트 서비스
🏢 **종목**: 미래에셋증권 (006800)
📅 **시간**: 테스트 시간
💡 **내용**: 이 메시지가 보이면 텔레그램 봇이 정상 작동합니다!

✅ **테스트 성공**
        """
        
        print("📤 텔레그램 메시지 전송 중...")
        
        # 동기 방식으로 메시지 전송
        result = telegram_bot.send_message(test_message)
        
        if result:
            print("✅ 텔레그램 메시지 전송 성공!")
            print("📱 텔레그램 채팅방을 확인해주세요.")
        else:
            print("❌ 텔레그램 메시지 전송 실패!")
            
    except Exception as e:
        print(f"❌ 텔레그램 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_telegram_async():
    """텔레그램 봇 비동기 테스트"""
    try:
        print("🚀 텔레그램 봇 비동기 테스트 시작")
        
        # 텔레그램 봇 클라이언트 생성
        telegram_bot = TelegramBotClient()
        
        # 테스트 메시지
        test_message = """
🔔 **비동기 테스트 알림** 🔔

📊 **서비스**: 비동기 테스트 서비스
🏢 **종목**: 미래에셋증권 (006800)
📅 **시간**: 비동기 테스트 시간
💡 **내용**: 이 메시지가 보이면 비동기 텔레그램 봇이 정상 작동합니다!

✅ **비동기 테스트 성공**
        """
        
        print("📤 비동기 텔레그램 메시지 전송 중...")
        
        # 비동기 방식으로 메시지 전송
        result = await telegram_bot.send_message_async(test_message)
        
        if result:
            print("✅ 비동기 텔레그램 메시지 전송 성공!")
            print("📱 텔레그램 채팅방을 확인해주세요.")
        else:
            print("❌ 비동기 텔레그램 메시지 전송 실패!")
            
    except Exception as e:
        print(f"❌ 비동기 텔레그램 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """메인 함수"""
    print("=" * 60)
    print("🔔 텔레그램 봇 직접 테스트")
    print("=" * 60)
    
    # 동기 테스트
    await test_telegram_direct()
    
    print("\n" + "=" * 60)
    
    # 비동기 테스트
    await test_telegram_async()
    
    print("\n" + "=" * 60)
    print("🏁 테스트 완료")

if __name__ == "__main__":
    asyncio.run(main()) 