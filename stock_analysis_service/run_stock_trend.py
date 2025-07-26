#!/usr/bin/env python3
"""
주가 추이 분석 서비스 실행 스크립트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 서비스 모듈 임포트
from services.stock_trend_service.main import run_cli

def main():
    """메인 함수"""
    print("🚀 주가 추이 분석 서비스")
    print("=" * 50)
    print("📊 pykrx를 사용한 주가 데이터 분석 및 텔레그램 알림")
    print("=" * 50)
    
    # 환경 변수 확인
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("⚠️  TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
        print("   config/env_local.py 파일을 확인하세요.")
        print("")
    
    if not os.getenv("TELEGRAM_CHAT_ID"):
        print("⚠️  TELEGRAM_CHAT_ID 환경 변수가 설정되지 않았습니다.")
        print("   config/env_local.py 파일을 확인하세요.")
        print("")
    
    # CLI 실행
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 