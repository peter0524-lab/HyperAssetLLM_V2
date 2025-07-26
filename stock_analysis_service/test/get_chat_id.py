import sys
import os
import asyncio
from telegram import Bot
from config.env_local import get_env_var

async def get_chat_updates():
    """텔레그램 봇의 업데이트를 받아 채팅 ID를 확인"""
    bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    bot = Bot(token=bot_token)
    
    try:
        print("\n=== 텔레그램 봇 정보 ===")
        me = await bot.get_me()
        print(f"봇 이름: {me.first_name}")
        print(f"봇 사용자명: @{me.username}")
        print(f"봇 ID: {me.id}")
        
        print("\n=== 최근 업데이트 확인중... ===")
        updates = await bot.get_updates(timeout=60)
        
        if not updates:
            print("\n❌ 최근 메시지가 없습니다.")
            print("다음 사항을 확인해주세요:")
            print("1. @miraeaibot 과 대화를 시작하셨나요?")
            print("2. /start 명령어를 입력하셨나요?")
            print("3. 아무 메시지나 보내보셨나요?")
            return
        
        print(f"\n총 {len(updates)}개의 업데이트를 찾았습니다.")
        for update in updates:
            print("\n--- 업데이트 정보 ---")
            print(f"업데이트 ID: {update.update_id}")
            
            if update.message:
                chat = update.message.chat
                print(f"채팅 정보:")
                print(f"- 채팅 ID: {chat.id}")
                print(f"- 채팅 타입: {chat.type}")
                if chat.username:
                    print(f"- 사용자명: @{chat.username}")
                print(f"- 메시지: {update.message.text}")
                
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        print("\n봇 토큰을 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(get_chat_updates()) 