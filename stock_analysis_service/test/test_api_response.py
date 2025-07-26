#!/usr/bin/env python3
"""
네이버 API 응답 구조 확인 테스트
"""

import sys
import os
import json
import requests
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_naver_api_response():
    """네이버 API 응답 구조 확인"""
    print("🔍 네이버 API 응답 구조 확인 시작")
    
    stock_code = "006800"  # 미래에셋증권
    api_url = f"https://m.stock.naver.com/api/news/stock/{stock_code}"
    
    # 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': f'https://m.stock.naver.com/domestic/stock/{stock_code}/news',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }
    
    try:
        print(f"📡 API 호출: {api_url}")
        
        # API 호출
        response = requests.get(api_url, headers=headers, params={'page': 1, 'size': 3}, timeout=10)
        print(f"📊 HTTP 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📋 응답 타입: {type(data)}")
            print(f"📋 응답 길이: {len(data) if isinstance(data, list) else 'N/A'}")
            
            # 응답 구조 분석
            if isinstance(data, list):
                print(f"📋 리스트 길이: {len(data)}")
                for i, item in enumerate(data):
                    print(f"  [{i}] 타입: {type(item)}")
                    print(f"  [{i}] 키: {list(item.keys()) if isinstance(item, dict) else 'N/A'}")
                    if isinstance(item, dict) and 'items' in item:
                        print(f"  [{i}] items 길이: {len(item['items'])}")
                        if item['items']:
                            print(f"  [{i}] 첫 번째 item 키: {list(item['items'][0].keys())}")
            elif isinstance(data, dict):
                print(f"📋 딕셔너리 키: {list(data.keys())}")
                if 'items' in data:
                    print(f"📋 items 길이: {len(data['items'])}")
                    if data['items']:
                        print(f"📋 첫 번째 item 키: {list(data['items'][0].keys())}")
            else:
                print(f"📋 예상치 못한 응답 타입: {type(data)}")
            
            # JSON 출력 (처음 1000자)
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            print(f"📋 JSON 응답 (처음 1000자):")
            print(json_str[:1000])
            if len(json_str) > 1000:
                print("... (이하 생략)")
                
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"❌ 응답 내용: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    test_naver_api_response() 