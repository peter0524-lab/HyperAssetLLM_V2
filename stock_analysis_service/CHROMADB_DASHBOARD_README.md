# ChromaDB 대시보드 사용법

## 📊 개요
ChromaDB 대시보드는 MySQL Workbench와 같은 기능을 제공하는 ChromaDB 전용 시각화 도구입니다.

## 🚀 실행 방법

### 1. 간단한 실행 (권장)
```bash
# Windows에서
start_dashboard.bat

# Linux/Mac에서
python chromadb_dashboard.py
```

### 2. 수동 실행
```bash
# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate.bat  # Windows

# 필요한 패키지 설치
pip install jinja2 python-multipart

# 대시보드 실행
python chromadb_dashboard.py
```

## 🌐 접속 URL

- **메인 대시보드**: http://localhost:8080
- **검색 페이지**: http://localhost:8080/search
- **컬렉션 상세**: http://localhost:8080/collection/{collection_name}
- **API 문서**: http://localhost:8080/docs

## 📱 주요 기능

### 1. 메인 대시보드
- **시스템 상태**: ChromaDB 연결 상태 확인
- **컬렉션 통계**: 각 컬렉션별 문서 수 표시
- **빠른 검색**: 메인 화면에서 바로 검색 가능

### 2. 고급 검색
- **벡터 유사도 검색**: 의미 기반 스마트 검색
- **컬렉션별 검색**: 특정 컬렉션에서만 검색
- **결과 개수 조절**: 5개~50개 결과 선택 가능
- **유사도 점수**: 각 결과의 유사도 점수 표시

### 3. 컬렉션 상세 보기
- **문서 목록**: 컬렉션 내 모든 문서 조회
- **메타데이터**: 각 문서의 메타데이터 상세 표시
- **페이지네이션**: 대용량 데이터 효율적 탐색

## 🗂️ 컬렉션 구조

### high_impact_news
- **용도**: 영향력 0.7 이상의 고영향 뉴스
- **아이콘**: ⚠️ 경고 삼각형
- **설명**: 과거 분석 및 유사 사례 검색에 활용

### daily_news
- **용도**: 일일 뉴스 임시 저장
- **아이콘**: 📅 달력
- **설명**: 중복 검사 및 실시간 분석에 활용

### weekly_keywords
- **용도**: 주간 핵심 키워드
- **아이콘**: 🏷️ 태그
- **설명**: 뉴스 영향력 평가시 참조

### past_events
- **용도**: 과거 중요 사건
- **아이콘**: 📈 히스토리
- **설명**: 역사적 패턴 분석에 활용

## 🔍 검색 사용법

### 1. 기본 검색
```
1. 컬렉션 선택
2. 검색어 입력 (예: "주가 상승")
3. 검색 버튼 클릭
```

### 2. 고급 검색 팁
- **종목명 검색**: "삼성전자", "현대차" 등
- **이벤트 검색**: "실적 발표", "신제품 출시" 등
- **감정 검색**: "긍정적", "부정적" 등
- **키워드 조합**: "AI 반도체 투자" 등

### 3. 결과 해석
- **유사도 점수**: 0.800 이상이면 높은 유사도
- **메타데이터**: 날짜, 종목, 영향력 등 정보
- **정렬**: 유사도 순으로 자동 정렬

## 📈 활용 예시

### 1. 고영향 뉴스 분석
```
컬렉션: high_impact_news
검색어: "반도체 수급 부족"
→ 과거 반도체 관련 고영향 뉴스 분석
```

### 2. 일일 뉴스 모니터링
```
컬렉션: daily_news
검색어: "삼성전자"
→ 오늘의 삼성전자 관련 뉴스 확인
```

### 3. 키워드 트렌드 분석
```
컬렉션: weekly_keywords
검색어: "ESG"
→ ESG 관련 주간 키워드 트렌드 분석
```

## 🛠️ API 사용법

### 1. 컬렉션 목록 조회
```bash
GET /api/collections
```

### 2. 문서 검색
```bash
POST /api/search
{
    "collection_name": "high_impact_news",
    "query": "주가 상승",
    "top_k": 10
}
```

### 3. 시스템 상태 확인
```bash
GET /api/health
```

## 🔧 트러블슈팅

### 1. 대시보드가 시작되지 않는 경우
```bash
# 가상환경 확인
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
pip install jinja2 python-multipart

# 직접 실행
python chromadb_dashboard.py
```

### 2. ChromaDB 연결 오류
```bash
# 뉴스 서비스 먼저 실행
python services/news_service/main.py

# 대시보드 다시 실행
python chromadb_dashboard.py
```

### 3. 검색 결과가 없는 경우
- 컬렉션에 데이터가 있는지 확인
- 검색어를 간단하게 변경
- 다른 컬렉션에서 시도

## 📱 브라우저 호환성

### 지원 브라우저
- ✅ Chrome (권장)
- ✅ Firefox
- ✅ Edge
- ✅ Safari

### 추천 설정
- JavaScript 활성화
- 쿠키 허용
- 팝업 차단 해제

## 🎯 성능 최적화

### 1. 검색 성능
- 구체적인 검색어 사용
- 결과 개수 적절히 조절
- 자주 사용하는 검색어 북마크

### 2. 시스템 성능
- 브라우저 캐시 정리
- 메모리 모니터링
- 대용량 컬렉션 주의

## 🔐 보안 고려사항

### 1. 접근 제한
- 현재 localhost에서만 접근 가능
- 외부 접근 필요시 방화벽 설정 필요

### 2. 데이터 보호
- 중요 데이터 접근 시 인증 고려
- 로그 모니터링

## 📞 지원 및 문의

### 문제 발생시
1. 로그 파일 확인: `logs/` 디렉토리
2. 터미널 오류 메시지 확인
3. 브라우저 개발자 도구 확인

### 추가 기능 요청
- 새로운 검색 필터
- 데이터 시각화 차트
- 자동 새로고침 기능
- 데이터 내보내기 기능

---

**🎉 즐거운 데이터 탐색을 위한 ChromaDB 대시보드!**

MySQL Workbench처럼 직관적이고 강력한 ChromaDB 탐색 도구로 벡터 데이터베이스의 모든 기능을 활용해보세요. 