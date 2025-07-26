# 📊 주가 추이 분석 서비스

pykrx를 사용하여 한국 주식 시장의 주가 추이를 분석하고 텔레그램으로 알림을 전송하는 서비스입니다.

## 🚀 주요 기능

- **5일간 주가 데이터 분석**: 시가, 고가, 저가, 종가, 거래량, 거래대금 추이
- **등락률 분석**: 일별 등락률 및 기간 수익률 계산
- **거래량/거래대금 분석**: 평균 거래량과 거래대금 통계
- **텔레그램 알림**: 분석 결과를 예쁘게 포맷팅하여 텔레그램으로 전송
- **인기 종목 자동 선택**: 시가총액 기준 인기 종목 자동 분석
- **REST API 제공**: 웹 API를 통한 서비스 이용
- **명령줄 인터페이스**: CLI를 통한 간편한 사용

## 📋 필요한 라이브러리

```bash
pip install pykrx pandas fastapi uvicorn
```

또는 기존 requirements.txt 사용:
```bash
pip install -r requirements.txt
```

## ⚙️ 설정

### 1. 텔레그램 봇 설정

1. **텔레그램 봇 생성**:
   - @BotFather에게 `/newbot` 명령어 전송
   - 봇 이름과 사용자명 설정
   - 발급받은 토큰 저장

2. **채팅 ID 확인**:
   - 생성한 봇에게 메시지 전송
   - `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` 방문
   - chat.id 값 확인

### 2. 환경 변수 설정

`config/env_local.py` 파일에 다음 내용 추가:

```python
# 텔레그램 설정
TELEGRAM_BOT_TOKEN = "your_bot_token_here"
TELEGRAM_CHAT_ID = "your_chat_id_here"
TELEGRAM_PARSE_MODE = "HTML"
```

## 🖥️ 사용 방법

### 1. 명령줄 인터페이스 (CLI)

#### 기본 사용법
```bash
# 프로젝트 루트에서 실행
python run_stock_trend.py [명령어] [옵션]
```

#### 주요 명령어

```bash
# 1. 단일 종목 분석 (텔레그램 전송 없음)
python run_stock_trend.py analyze 005930

# 2. 단일 종목 분석 후 텔레그램 알림
python run_stock_trend.py alert 005930

# 3. 복수 종목 분석 후 텔레그램 알림
python run_stock_trend.py multi-alert 005930 000660 035420

# 4. 인기 종목 자동 선택 후 텔레그램 알림
python run_stock_trend.py popular --market KOSPI --count 5

# 5. API 서버 실행
python run_stock_trend.py server --port 8000

# 6. 서비스 상태 확인
python run_stock_trend.py health
```

#### 옵션

- `--days`: 분석 기간 (기본: 5일)
- `--market`: 시장 선택 (KOSPI, KOSDAQ)
- `--count`: 인기 종목 수 (기본: 5개)
- `--host`: 서버 호스트 (기본: 0.0.0.0)
- `--port`: 서버 포트 (기본: 8000)

### 2. 직접 실행 (서비스 디렉토리에서)

```bash
cd services/stock_trend_service

# 단일 종목 분석
python main.py analyze 005930

# 텔레그램 알림 전송
python main.py alert 005930

# 서버 실행
python main.py server
```

### 3. REST API 사용

#### 서버 시작
```bash
python run_stock_trend.py server
```

#### API 엔드포인트

```bash
# 서비스 상태 확인
GET http://localhost:8000/health

# 종목 분석 (텔레그램 전송 없음)
POST http://localhost:8000/analyze/005930?days=5

# 종목 알림 전송
POST http://localhost:8000/alert/005930?days=5

# 복수 종목 알림 전송
POST http://localhost:8000/alert/multiple
Content-Type: application/json
{
    "stock_codes": ["005930", "000660", "035420"],
    "days": 5
}

# 인기 종목 알림 전송
POST http://localhost:8000/alert/popular?market=KOSPI&count=5&days=5

# 인기 종목 리스트 조회
GET http://localhost:8000/stocks/popular?market=KOSPI&count=10
```

## 🧪 테스트 실행

### 1. 빠른 테스트 (기본 기능 확인)
```bash
cd services/stock_trend_service
python test_stock_trend.py --mode quick
```

### 2. 단위 테스트 (모든 기능 테스트)
```bash
python test_stock_trend.py --mode unit
```

### 3. 통합 테스트 (실제 데이터 사용)
```bash
python test_stock_trend.py --mode integration
```

### 4. 텔레그램 전송 테스트
```bash
python test_stock_trend.py --mode unit --telegram
```

## 📱 텔레그램 알림 예시

```
📊 삼성전자(005930) 5일 주가 추이 분석

💰 현재가: 71,000원
📈 기간 수익률: +2.15%
📈 최고 등락률: +3.45%
📉 최저 등락률: -1.20%
🎯 변동성: 1.85%

📊 거래 현황
💎 평균 거래량: 12,345.6만주
💰 평균 거래대금: 8,765.4억원

📅 일별 상세 내역

2024-01-15
└ 종가: 71,000원 (📈 +2.15%)
└ 거래량: 15,234.5만주 | 거래대금: 10,876.2억원

2024-01-14
└ 종가: 69,500원 (📉 -0.85%)
└ 거래량: 9,876.3만주 | 거래대금: 6,854.7억원

...

📈 분석 기간: 2024-01-11 ~ 2024-01-15
🕐 분석 시각: 2024-01-15 18:30:00

💡 투자에 참고하시기 바랍니다!
```

## 📋 주요 종목 코드

### KOSPI 대형주
- `005930`: 삼성전자
- `000660`: SK하이닉스
- `035420`: 네이버
- `068270`: 셀트리온
- `207940`: 삼성바이오로직스
- `005935`: 삼성전자우
- `051910`: LG화학
- `006400`: 삼성SDI
- `028260`: 삼성물산
- `012330`: 현대모비스

### KOSDAQ 대형주
- `091990`: 셀트리온헬스케어
- `240810`: 원익IPS
- `263750`: 펄어비스
- `196170`: 알테오젠
- `328130`: 루닛

## 🔧 문제 해결

### 1. pykrx 설치 오류
```bash
pip install --upgrade pykrx
```

### 2. 데이터 조회 실패
- 휴장일이나 장 시간 전에는 데이터가 없을 수 있습니다.
- 잘못된 종목 코드를 입력했는지 확인하세요.

### 3. 텔레그램 전송 실패
- 봇 토큰과 채팅 ID가 올바른지 확인하세요.
- 봇이 채팅방에 추가되어 있는지 확인하세요.

### 4. 네트워크 오류
- 한국투자증권 API 서버 상태를 확인하세요.
- 방화벽 설정을 확인하세요.

## 📈 활용 예시

### 1. 매일 아침 인기 종목 알림
```bash
# 매일 오전 9시에 실행하도록 cron 설정
0 9 * * 1-5 cd /path/to/project && python run_stock_trend.py popular --market KOSPI --count 5
```

### 2. 특정 종목 모니터링
```bash
# 관심 종목 리스트 모니터링
python run_stock_trend.py multi-alert 005930 000660 035420 068270
```

### 3. 웹 대시보드 연동
```bash
# API 서버 실행 후 웹 대시보드에서 활용
python run_stock_trend.py server --port 8000
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스를 따릅니다.

## ⚠️ 면책조항

이 서비스는 교육 및 참고 목적으로만 사용되어야 합니다. 실제 투자 결정은 사용자의 책임이며, 투자 손실에 대한 책임은 사용자에게 있습니다.

## 📞 지원

문제가 발생하거나 개선사항이 있으시면 GitHub Issues를 통해 알려주세요. 