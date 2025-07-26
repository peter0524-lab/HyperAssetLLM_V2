# 📊 주식 분석 시스템 v2 - 완전 설치 가이드

## 🎯 개요

이 문서는 주식 분석 시스템을 처음 설치하고 실행하는 사용자를 위한 **완전한 가이드**입니다.
지금까지의 디버깅 과정을 통해 검증된 모든 필요한 모듈과 단계가 포함되어 있습니다.

## 📋 시스템 요구사항

### 🖥️ 운영체제

- **macOS**: 10.15 이상 (Apple Silicon M1/M2 지원)
- **Windows**: 10 이상
- **Linux**: Ubuntu 18.04 이상

### 🐍 Python 버전

- **Python 3.9 이상** (권장: 3.9.x)
- Python 3.8 이하는 일부 패키지 호환성 문제 발생 가능

### 💾 시스템 리소스

- **RAM**: 최소 8GB (권장: 16GB 이상)
- **저장공간**: 최소 10GB 여유 공간
- **인터넷**: 안정적인 인터넷 연결 (패키지 설치 및 데이터 수집용)

### 🔧 필수 소프트웨어

- **MySQL Server 8.0 이상**
- **Google Chrome** (웹 스크래핑용)
- **Git** (코드 클론용)

## 🚀 설치 단계

### 1️⃣ 레포지토리 클론

```bash
# 1. 원하는 디렉토리로 이동
cd ~/Desktop  # 또는 원하는 경로

# 2. Git 레포지토리 클론
git clone <repository-url> 데이터한잔_v2
cd 데이터한잔_v2
```

### 2️⃣ Python 가상환경 설정

```bash
# 1. 가상환경 생성
python3 -m venv .venv

# 2. 가상환경 활성화
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# 3. 가상환경 활성화 확인 (터미널에 (.venv) 표시되어야 함)
```

### 3️⃣ 필수 패키지 설치

```bash
# 1. stock_analysis_service 디렉토리로 이동
cd stock_analysis_service

# 2. 최신 pip로 업그레이드
pip install --upgrade pip

# 3. 필수 패키지 설치 (검증된 최종 버전)
pip install -r requirements_final.txt
```

> ⚠️ **설치 시간**: 처음 설치 시 PyTorch, ChromaDB 등 대용량 패키지로 인해 **20-30분** 소요될 수 있습니다.

### 4️⃣ MySQL 데이터베이스 설정

```bash
# 1. MySQL 서버 실행 확인
mysql --version

# 2. MySQL 접속 및 데이터베이스 생성
mysql -u root -p
```

MySQL에서 다음 명령어 실행:

```sql
-- 데이터베이스 생성
CREATE DATABASE stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 생성 및 권한 부여 (선택사항)
CREATE USER 'stock_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON stock_analysis.* TO 'stock_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5️⃣ 환경 설정 파일 생성

```bash
# config/env_local.py 파일을 편집하여 다음 정보를 입력:
```

`config/env_local.py` 예시:

```python
# MySQL 데이터베이스 설정
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # 또는 생성한 사용자명
    'password': 'your_mysql_password',
    'database': 'stock_analysis',
    'charset': 'utf8mb4'
}

# API 키 설정 (필요한 경우)
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token"
HYPERCLOVA_API_KEY = "your_hyperclova_api_key"
DART_API_KEY = "your_dart_api_key"

# 기타 설정
LOG_LEVEL = "INFO"
```

## 🏃‍♂️ 시스템 실행

### 1️⃣ 모든 서비스 시작

```bash
# 1. stock_analysis_service 디렉토리에서 실행
cd stock_analysis_service

# 2. 가상환경 활성화 확인
source ../.venv/bin/activate  # macOS/Linux
# 또는
..\.venv\Scripts\activate  # Windows

# 3. 모든 서비스 시작
python start_all_services.py
```

### 2️⃣ 서비스 상태 확인

```bash
# 헬스체크 실행
python check_services_health.py
```

**예상 결과**: 7개 서비스 모두 ✅ healthy 상태여야 함

- News Service (포트: 8001)
- Disclosure Service (포트: 8002)
- Chart Service (포트: 8003)
- Report Service (포트: 8004)
- API Gateway (포트: 8005)
- User Service (포트: 8006)
- Flow Analysis Service (포트: 8010)

### 3️⃣ 시스템 테스트

```bash
# 1. 프로젝트 루트로 이동
cd ..

# 2. Frontend 데이터 흐름 테스트 실행
python test_frontend_data_flow.py
```

**예상 결과**: `🎯 전체 테스트 성공!` 메시지 출력

## 🛠️ 문제 해결

### ❌ 자주 발생하는 문제들

#### 1. 크롬드라이버 문제

**증상**: News Service에서 `ChromeDriverManager 설치 실패` 에러

```bash
# 해결방법: Chrome 브라우저 최신 버전 설치 확인
# Chrome이 설치되어 있고 최신 버전인지 확인
```

#### 2. 전화번호 중복 에러

**증상**: `이미 등록된 전화번호입니다` 에러

```bash
# 해결방법: test_frontend_data_flow.py에서 전화번호 변경
# 파일 내 phone_number 값을 다른 번호로 수정
```

#### 3. MySQL 연결 실패

**증상**: `Connection refused` 또는 `Access denied` 에러

```bash
# 해결방법:
# 1. MySQL 서버 실행 상태 확인
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# 2. 연결 정보 확인
mysql -u root -p -h localhost

# 3. config/env_local.py의 MySQL 설정 확인
```

#### 4. 패키지 설치 실패

**증상**: `pip install` 중 에러 발생

```bash
# 해결방법:
# 1. pip 업그레이드
pip install --upgrade pip

# 2. 개별 패키지 설치 시도
pip install fastapi uvicorn pandas

# 3. 시스템 의존성 설치 (Ubuntu)
sudo apt-get update
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential
```

#### 5. 포트 충돌 문제

**증상**: `Address already in use` 에러

```bash
# 해결방법:
# 1. 실행 중인 프로세스 확인
lsof -i :8001  # 특정 포트 확인
lsof -i :8000-8010  # 범위 확인

# 2. 프로세스 종료
python stop_all_services.py

# 3. 강제 종료 (필요시)
pkill -f "python"
```

### 🔧 유용한 명령어들

```bash
# 서비스 관리
python stop_all_services.py     # 모든 서비스 종료
python start_all_services.py    # 모든 서비스 시작
python check_services_health.py # 서비스 상태 확인

# 로그 확인
ls *.log                        # 로그 파일 목록
tail -f "news service.log"      # 실시간 로그 확인

# 프로세스 확인
ps aux | grep python            # Python 프로세스 확인
netstat -tulpn | grep :800      # 포트 사용 현황 확인
```

## 📁 프로젝트 구조

```
데이터한잔_v2/
├── .venv/                          # Python 가상환경
├── stock_analysis_service/         # 메인 서비스 디렉토리
│   ├── requirements_final.txt      # 최종 패키지 목록
│   ├── start_all_services.py       # 서비스 시작 스크립트
│   ├── stop_all_services.py        # 서비스 종료 스크립트
│   ├── check_services_health.py    # 헬스체크 스크립트
│   ├── config/                     # 설정 파일들
│   │   ├── env_local.py           # 로컬 환경 설정
│   │   └── stocks.json            # 주식 종목 정보
│   ├── services/                   # 마이크로서비스들
│   │   ├── news_service/          # 뉴스 수집 서비스
│   │   ├── disclosure_service/    # 공시 수집 서비스
│   │   ├── chart_service/         # 차트 분석 서비스
│   │   ├── report_service/        # 리포트 생성 서비스
│   │   ├── api_gateway/           # API 게이트웨이
│   │   ├── user_service/          # 사용자 관리 서비스
│   │   └── flow_analysis_service/ # 플로우 분석 서비스
│   ├── shared/                     # 공통 모듈
│   └── logs/                       # 로그 파일들
├── test_frontend_data_flow.py      # 통합 테스트 스크립트
└── README_v2.md                    # 이 파일
```

## 🎯 다음 단계

시스템이 정상적으로 실행되면:

1. **웹 대시보드 접속**: `http://localhost:8005` (API Gateway)
2. **사용자 등록**: 프론트엔드를 통해 사용자 프로필 생성
3. **주식 종목 설정**: 관심 종목 등록
4. **뉴스 수집 시작**: 자동으로 뉴스 수집 및 분석 시작

## 🆘 추가 지원

문제가 지속될 경우:

1. **로그 파일 확인**: `*.log` 파일들에서 상세 에러 메시지 확인
2. **GitHub Issues**: 프로젝트 저장소의 Issues 탭에서 문제 보고
3. **환경 정보 수집**:
   ```bash
   python --version
   pip list
   mysql --version
   ```

---

✅ **설치 완료 체크리스트**:

- [ ] Python 3.9+ 설치됨
- [ ] MySQL 서버 실행 중
- [ ] 가상환경 생성 및 활성화
- [ ] requirements_final.txt 패키지 설치 완료
- [ ] config/env_local.py 설정 완료
- [ ] 7개 서비스 모두 healthy 상태
- [ ] test_frontend_data_flow.py 테스트 성공

🎉 **축하합니다! 주식 분석 시스템이 성공적으로 설치되었습니다!**
