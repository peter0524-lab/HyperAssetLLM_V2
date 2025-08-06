"""
사용자 종목 설정 테스트 스크립트
"""

import requests
import json

def test_user_stocks():
    """사용자 ID 1에 테스트 종목 추가"""
    
    base_url = "http://localhost:8006"
    
    # 1. 사용자 프로필 생성 (없는 경우)
    profile_data = {
        "username": "테스트 사용자",
        "phone_number": "01012345678",
        "news_similarity_threshold": 0.7,
        "news_impact_threshold": 0.8
    }
    
    try:
        response = requests.post(f"{base_url}/users/profile", json=profile_data)
        print(f"프로필 생성 응답: {response.status_code}")
        if response.status_code == 200:
            print("✅ 사용자 프로필 생성 완료")
    except Exception as e:
        print(f"❌ 프로필 생성 실패: {e}")
    
    # 2. 사용자 ID 1에 종목 추가
    stocks_to_add = [
        {
            "stock_code": "006800",
            "stock_name": "미래에셋증권",
            "enabled": True
        },
        {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "enabled": True
        },
        {
            "stock_code": "000660",
            "stock_name": "SK하이닉스",
            "enabled": True
        }
    ]
    
    for stock in stocks_to_add:
        try:
            response = requests.post(f"{base_url}/users/1/stocks", json=stock)
            print(f"종목 추가 응답 ({stock['stock_code']}): {response.status_code}")
            if response.status_code == 200:
                print(f"✅ 종목 추가 완료: {stock['stock_name']} ({stock['stock_code']})")
        except Exception as e:
            print(f"❌ 종목 추가 실패 ({stock['stock_code']}): {e}")
    
    # 3. 사용자 종목 목록 확인
    try:
        response = requests.get(f"{base_url}/users/1/stocks")
        print(f"종목 목록 조회 응답: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stocks = data.get("data", [])
                print(f"✅ 사용자 종목 목록 ({len(stocks)}개):")
                for stock in stocks:
                    print(f"  - {stock['stock_name']} ({stock['stock_code']}) - 활성화: {stock.get('enabled', True)}")
            else:
                print(f"❌ 종목 목록 조회 실패: {data.get('message')}")
        else:
            print(f"❌ 종목 목록 조회 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 종목 목록 조회 실패: {e}")
    
    # 4. 텔레그램 설정 확인
    try:
        response = requests.get(f"{base_url}/users/1/telegram-config")
        print(f"텔레그램 설정 조회 응답: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                config = data.get("data", {})
                print(f"✅ 텔레그램 설정:")
                print(f"  - 활성화: {config.get('enabled', False)}")
                print(f"  - 뉴스 알림: {config.get('news_alerts', False)}")
                print(f"  - 공시 알림: {config.get('disclosure_alerts', False)}")
                print(f"  - 차트 알림: {config.get('chart_alerts', False)}")
            else:
                print(f"❌ 텔레그램 설정 조회 실패: {data.get('message')}")
        else:
            print(f"❌ 텔레그램 설정 조회 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 텔레그램 설정 조회 실패: {e}")

if __name__ == "__main__":
    print("🧪 사용자 종목 설정 테스트 시작...")
    test_user_stocks()
    print("✅ 테스트 완료!") 