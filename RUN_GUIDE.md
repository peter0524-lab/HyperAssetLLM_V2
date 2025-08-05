# 🚀 HyperAssetLLM_V2 실행 설명서

## 가상환경 생성 및 활성화

### Windows에서:
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux에서:
```bash
python3 -m venv venv
source venv/bin/activate
```

## 의존성 설치

```bash
cd stock_analysis_service
pip install -r requirements_final_complete.txt

cd frontend
npm install
```

## 백엔드 실행

```bash
cd stock_analysis_service
python simple_server_starter.py
```

## 프론트엔드 실행

```bash
cd stock_analysis_service/frontend
npm run dev
```

1. 백엔드 서버 실행
2. 프론트 빌드 실행
3. 대시보드 가기 클릭 !
4. 신규회원인 경우 회원 정보 입력하면 자동 가입

**성공적으로 실행되면 브라우저에서 `http://localhost:8000`에 접속하여 애플리케이션을 사용할 수 있습니다!** 🎉 