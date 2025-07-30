#!/usr/bin/env python3
"""
새로운 채널 메시지 전송 테스트
"""

import requests
from config.env_local import get_env_var

def test_new_channel():
    """새로운 채널로 메시지 전송 테스트"""
    bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_var("TELEGRAM_CHAT_ID")
    
    print("🧪 새로운 채널 메시지 전송 테스트")
    print("=" * 50)
    print(f"봇 토큰: {bot_token[:20]}...")
    print(f"채널 ID: {chat_id}")
    
    # 테스트 메시지
    test_message = """
🧪 <b>HyperAsset 텔레그램 알림 테스트</b>

✅ 이 메시지가 보이면 새 채널 연결이 정상입니다!

🔧 <b>시스템 상태:</b>
• 봇 연결: ✅ 정상
• 채널 접근: ✅ 정상  
• 메시지 전송: ✅ 정상

📊 <b>테스트 정보:</b>
• 채널: @HypperAssetAlerts
• 서비스: HyperAsset 알림 시스템
• 버전: v1.0

💡 <i>실시간 알림 시스템이 준비되었습니다!</i>
    """.strip()
    
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
            return True
        else:
            print(f"❌ 메시지 전송 실패: {result}")
            return False
    else:
        print(f"❌ 메시지 전송 실패: {response.status_code}")
        print(f"응답: {response.text}")
        return False

def check_bot_permissions():
    """봇 권한 확인"""
    bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_var("TELEGRAM_CHAT_ID")
    
    print("\n🔍 봇 권한 확인...")
    
    # 채널 정보 조회
    url = f"https://api.telegram.org/bot{bot_token}/getChat"
    params = {"chat_id": chat_id}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            chat_info = result["result"]
            print(f"✅ 채널 정보 조회 성공")
            print(f"채널 제목: {chat_info.get('title')}")
            print(f"채널 타입: {chat_info.get('type')}")
            print(f"채널 사용자명: {chat_info.get('username')}")
            
            # 봇이 관리자인지 확인
            if "all_members_are_administrators" in chat_info:
                print("⚠️ 모든 멤버가 관리자인 채널입니다")
            else:
                print("✅ 일반 채널입니다")
                
        else:
            print(f"❌ 채널 정보 조회 실패: {result}")
    else:
        print(f"❌ 채널 정보 조회 실패: {response.status_code}")

if __name__ == "__main__":
    check_bot_permissions()
    test_new_channel() 