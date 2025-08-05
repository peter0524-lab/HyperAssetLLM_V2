#!/usr/bin/env python3
"""
텔레그램 API 직접 테스트
프론트엔드에서 호출하는 API 엔드포인트를 직접 테스트
"""

import requests
import json
from datetime import datetime

def test_telegram_api():
    """텔레그램 API 직접 테스트"""
    base_url = "http://localhost:8006"  # user_service 포트
    test_user_id = "user_1735632000_12345"  # 테스트용 사용자 ID
    
    print("🧪 텔레그램 API 직접 테스트")
    print("=" * 50)
    
    # 1. 채널 정보 조회 테스트
    print("\n1️⃣ 채널 정보 조회 테스트")
    try:
        response = requests.get(f"{base_url}/users/{test_user_id}/telegram-channel")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"에러: {response.text}")
    except Exception as e:
        print(f"채널 정보 조회 실패: {e}")
    
    # 2. 테스트 메시지 전송 테스트
    print("\n2️⃣ 테스트 메시지 전송 테스트")
    try:
        response = requests.post(f"{base_url}/users/{test_user_id}/telegram-test-simple")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"에러: {response.text}")
    except Exception as e:
        print(f"테스트 메시지 전송 실패: {e}")
    
    # 3. 환영 메시지 전송 테스트
    print("\n3️⃣ 환영 메시지 전송 테스트")
    try:
        response = requests.post(f"{base_url}/users/{test_user_id}/telegram-welcome-simple")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"에러: {response.text}")
    except Exception as e:
        print(f"환영 메시지 전송 실패: {e}")
    
    # 4. 헬스체크
    print("\n4️⃣ 서비스 헬스체크")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"에러: {response.text}")
    except Exception as e:
        print(f"헬스체크 실패: {e}")

def test_frontend_api():
    """프론트엔드 API 클라이언트 테스트"""
    print("\n🧪 프론트엔드 API 클라이언트 테스트")
    print("=" * 50)
    
    try:
        # 프론트엔드에서 사용하는 API 클라이언트 테스트
        from shared.apis.telegram_api import TelegramBotClient
        
        bot = TelegramBotClient()
        print(f"봇 토큰: {bot.bot_token[:20]}...")
        print(f"채팅 ID: {bot.chat_id}")
        
        # 직접 메시지 전송 테스트
        test_message = f"""
🧪 <b>API 클라이언트 테스트</b>

✅ 이 메시지는 API 클라이언트를 통해 전송되었습니다!

📊 <b>테스트 정보:</b>
• 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• 클라이언트: TelegramBotClient
• 메서드: send_message

💡 <i>API 클라이언트가 정상 작동합니다!</i>
        """.strip()
        
        success = bot.send_message(test_message)
        if success:
            print("✅ API 클라이언트 메시지 전송 성공!")
        else:
            print("❌ API 클라이언트 메시지 전송 실패!")
            
    except Exception as e:
        print(f"API 클라이언트 테스트 실패: {e}")

if __name__ == "__main__":
    test_telegram_api()
    test_frontend_api() 