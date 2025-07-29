#!/usr/bin/env python3
"""
텔레그램 채널 ID 확인 및 테스트 스크립트
"""

import requests
import json
from config.env_local import get_env_var

def get_channel_info():
    """채널 정보 조회"""
    bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    
    # 1. 봇 정보 확인
    print("🔍 봇 정보 확인 중...")
    bot_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    response = requests.get(bot_url)
    
    if response.status_code == 200:
        bot_info = response.json()
        if bot_info.get("ok"):
            print(f"✅ 봇 정보: {bot_info['result']}")
        else:
            print(f"❌ 봇 정보 조회 실패: {bot_info}")
            return
    else:
        print(f"❌ 봇 정보 조회 실패: {response.status_code}")
        return
    
    # 2. 현재 설정된 채팅 ID로 테스트
    current_chat_id = get_env_var("TELEGRAM_CHAT_ID")
    print(f"\n🔍 현재 설정된 채팅 ID: {current_chat_id}")
    
    test_url = f"https://api.telegram.org/bot{bot_token}/getChat"
    params = {"chat_id": current_chat_id}
    
    response = requests.get(test_url, params=params)
    
    if response.status_code == 200:
        chat_info = response.json()
        if chat_info.get("ok"):
            print(f"✅ 현재 채팅 정보: {chat_info['result']}")
        else:
            print(f"❌ 현재 채팅 정보 조회 실패: {chat_info}")
    else:
        print(f"❌ 현재 채팅 정보 조회 실패: {response.status_code}")

def test_send_message():
    """메시지 전송 테스트"""
    bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_var("TELEGRAM_CHAT_ID")
    
    print(f"\n🧪 메시지 전송 테스트...")
    print(f"봇 토큰: {bot_token[:20]}...")
    print(f"채팅 ID: {chat_id}")
    
    test_message = "🧪 HyperAsset 텔레그램 알림 테스트\n\n✅ 이 메시지가 보이면 연결이 정상입니다!"
    
    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": test_message,
        "parse_mode": "HTML"
    }
    
    response = requests.post(send_url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            print("✅ 메시지 전송 성공!")
            print(f"메시지 ID: {result['result']['message_id']}")
        else:
            print(f"❌ 메시지 전송 실패: {result}")
    else:
        print(f"❌ 메시지 전송 실패: {response.status_code}")
        print(f"응답: {response.text}")

def find_channel_id():
    """채널 ID 찾기 가이드"""
    print("\n📋 채널 ID 찾는 방법:")
    print("1. 텔레그램에서 @userinfobot 검색")
    print("2. /start 명령어 입력")
    print("3. 채널에 메시지 전송 (봇이 관리자인 경우)")
    print("4. 봇이 반환하는 정보에서 채널 ID 확인")
    print("\n또는:")
    print("1. 채널에서 아무 메시지나 전송")
    print("2. https://api.telegram.org/bot{BOT_TOKEN}/getUpdates 접속")
    print("3. 응답에서 'chat' -> 'id' 값 확인")

if __name__ == "__main__":
    print("🚀 텔레그램 채널 테스트 시작")
    print("=" * 50)
    
    get_channel_info()
    test_send_message()
    find_channel_id()
    
    print("\n" + "=" * 50)
    print("✅ 테스트 완료") 