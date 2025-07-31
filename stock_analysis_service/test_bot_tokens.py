#!/usr/bin/env python3
"""
다른 봇 토큰들로 HyperAsset 채널 테스트
"""

import requests
import json
from config.env_local import get_env_var

def test_bot_token(bot_token: str, bot_name: str):
    """봇 토큰 테스트"""
    print(f"\n🔍 {bot_name} 테스트")
    print("=" * 50)
    
    # 1. 봇 정보 확인
    print("1️⃣ 봇 정보 확인...")
    bot_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    response = requests.get(bot_url)
    
    if response.status_code == 200:
        bot_info = response.json()
        if bot_info.get("ok"):
            bot_data = bot_info['result']
            print(f"✅ 봇 정보:")
            print(f"   • 봇 이름: {bot_data.get('first_name', 'N/A')}")
            print(f"   • 사용자명: {bot_data.get('username', 'N/A')}")
            print(f"   • 봇 ID: {bot_data.get('id', 'N/A')}")
        else:
            print(f"❌ 봇 정보 조회 실패: {bot_info}")
            return False
    else:
        print(f"❌ 봇 정보 조회 실패: {response.status_code}")
        return False
    
    # 2. 채널 정보 확인
    channel_id = "-1002819230740"
    print(f"\n2️⃣ 채널 정보 확인: {channel_id}")
    
    chat_url = f"https://api.telegram.org/bot{bot_token}/getChat"
    params = {"chat_id": channel_id}
    
    response = requests.get(chat_url, params=params)
    
    if response.status_code == 200:
        chat_info = response.json()
        if chat_info.get("ok"):
            chat_data = chat_info['result']
            print(f"✅ 채널 정보:")
            print(f"   • 채널 제목: {chat_data.get('title', 'N/A')}")
            print(f"   • 채널 사용자명: {chat_data.get('username', 'N/A')}")
            print(f"   • 채널 타입: {chat_data.get('type', 'N/A')}")
        else:
            print(f"❌ 채널 정보 조회 실패: {chat_info}")
            return False
    else:
        print(f"❌ 채널 정보 조회 실패: {response.status_code}")
        return False
    
    # 3. 메시지 전송 테스트
    print(f"\n3️⃣ 메시지 전송 테스트...")
    
    from datetime import datetime
    test_message = f"""
🧪 {bot_name} 테스트 메시지

✅ 이 메시지가 보이면 {bot_name}이 정상 작동합니다!

📱 채널: HypperAsset 주식 알림
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """.strip()
    
    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": channel_id,
        "text": test_message,
        "parse_mode": "HTML"
    }
    
    response = requests.post(send_url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            print("✅ 메시지 전송 성공!")
            print(f"   • 메시지 ID: {result['result'].get('message_id', 'N/A')}")
            return True
        else:
            print(f"❌ 메시지 전송 실패: {result}")
            return False
    else:
        print(f"❌ 메시지 전송 실패: {response.status_code}")
        print(f"   • 응답: {response.text}")
        return False

def main():
    """메인 함수"""
    
    print("🤖 HyperAsset 봇 토큰 테스트")
    print("=" * 60)
    
    # 테스트할 봇 토큰들
    bot_tokens = [
        ("7804706615:AAF_1WH5LZFa5mWktH3CZiHHKf98WRp4Buo", "현재 활성화된 봇"),
        ("8019204369:AAH343PfdI_JKnr12OB3wafHYb-nNfNaWnM", "이태환 봇"),
        ("7888091225:AAHMqbCQV4_so7VqDeLqbWaiGTvVyQ698-M", "테스트 봇 3")
    ]
    
    results = []
    
    for bot_token, bot_name in bot_tokens:
        success = test_bot_token(bot_token, bot_name)
        results.append((bot_name, success))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    
    for bot_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status}: {bot_name}")
    
    # 성공한 봇이 있으면 추천
    successful_bots = [name for name, success in results if success]
    if successful_bots:
        print(f"\n🎉 추천 봇: {', '.join(successful_bots)}")
        print("이 봇 토큰을 env_local.py에 설정하세요!")
    else:
        print("\n⚠️ 모든 봇 토큰이 실패했습니다.")
        print("봇 권한이나 채널 설정을 확인해주세요.")

if __name__ == "__main__":
    main() 