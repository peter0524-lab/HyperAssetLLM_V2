"""
Issue Scheduler Service

유상증자, 무상증자, 실적발표, 주주총회 등 중요한 기업 이슈 일정을 
사전에 추적하고 사용자에게 알림을 제공하는 서비스

주요 기능:
- FnGuide 캘린더 크롤링
- 중요 일정 사전 알림 (D-1, D-day)
- 사용자별 관심 종목 기반 필터링
- GPT를 통한 일정 중요도 해석
"""

__version__ = "1.0.0"
__author__ = "Stock Analysis Team" 