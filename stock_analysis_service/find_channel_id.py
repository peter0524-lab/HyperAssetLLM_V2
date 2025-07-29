#!/usr/bin/env python3
"""
새로운 텔레그램 채널 ID 찾기
"""

import requests
from config.env_local import get_env_var

def find_channel_id():
    """채널 ID 찾기"""
    bot_token = get_env_var("TELEGRAM_BOT_TOKEN")
    
    print("🔍 새로운 채널 ID 찾기")
    print("=" * 50)
    
    # 1. 봇이 관리자인 채널 목록 확인
    print("1️⃣ 봇이 관리자인 채널 확인...")
    
    # 2. 채널 정보 직접 조회 시도
    channel_username = "HypperAssetAlerts"  # @ 제외
    
    # 방법 1: 채널 사용자명으로 조회
    print(f"2️⃣ 채널 사용자명으로 조회: @{channel_username}")
    url = f"https://api.telegram.org/bot{bot_token}/getChat"
    params = {"chat_id": f"@{channel_username}"}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            chat_info = result["result"]
            print(f"✅ 채널 정보 조회 성공!")
            print(f"채널 ID: {chat_info.get('id')}")
            print(f"채널 제목: {chat_info.get('title')}")
            print(f"채널 사용자명: {chat_info.get('username')}")
            print(f"채널 타입: {chat_info.get('type')}")
            
            # 새로운 채널 ID로 환경변수 업데이트
            new_chat_id = chat_info.get('id')
            if new_chat_id:
                print(f"\n🔄 새로운 채널 ID: {new_chat_id}")
                print("이 ID를 환경변수 TELEGRAM_CHAT_ID에 설정하세요!")
                
                # 테스트 메시지 전송
                test_message = "🧪 새로운 채널 테스트\n\n✅ 이 메시지가 보이면 새 채널 연결이 정상입니다!"
                
                send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    "chat_id": new_chat_id,
                    "text": test_message,
                    "parse_mode": "HTML"
                }
                
                send_response = requests.post(send_url, json=data)
                
                if send_response.status_code == 200:
                    send_result = send_response.json()
                    if send_result.get("ok"):
                        print("✅ 새 채널로 테스트 메시지 전송 성공!")
                    else:
                        print(f"❌ 새 채널로 메시지 전송 실패: {send_result}")
                else:
                    print(f"❌ 새 채널로 메시지 전송 실패: {send_response.status_code}")
                
        else:
            print(f"❌ 채널 정보 조회 실패: {result}")
    else:
        print(f"❌ 채널 정보 조회 실패: {response.status_code}")
        print(f"응답: {response.text}")

def update_env_file():
    """환경변수 파일 업데이트 가이드"""
    print("\n📋 환경변수 업데이트 방법:")
    print("1. config/env_local.py 파일 열기")
    print("2. TELEGRAM_CHAT_ID 값을 새로운 채널 ID로 변경")
    print("3. 서버 재시작")

if __name__ == "__main__":
    find_channel_id()
    update_env_file() 