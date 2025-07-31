# Dockerfile

# 1. 기본 이미지 선택: Python 3.9 버전의 경량화된 Debian 기반 이미지 사용
#    - slim-buster는 불필요한 라이브러리가 제거되어 이미지 크기가 작습니다.
FROM python:3.9-slim-buster

# 2. 작업 디렉토리 설정: 컨테이너 내부에서 작업할 디렉토리
#    - 모든 애플리케이션 파일은 이 디렉토리 아래에 복사됩니다.
WORKDIR /app

# 3. 종속성 파일 복사 및 설치
#    - requirements_final.txt 파일만 먼저 복사하여 Docker 캐싱을 활용합니다.
#    - 이렇게 하면 requirements.txt가 변경되지 않는 한, pip install 단계는 다시 실행되지 않습니다.
#    - stock_analysis_service/requirements_final.txt 경로를 사용합니다.
COPY stock_analysis_service/requirements_final.txt .
RUN pip install --no-cache-dir -r requirements_final.txt

# 4. 프로젝트의 모든 파일 복사
#    - 현재 디렉토리(Dockerfile이 있는 곳)의 모든 내용을 컨테이너의 /app 디렉토리로 복사합니다.
#    - .dockerignore 파일에 명시된 파일/폴더는 제외됩니다.
COPY . .

# 5. 컨테이너가 사용할 포트 선언
#    - simple_server_starter.py가 9998 포트를 사용하므로 이를 노출합니다.
EXPOSE 9998

# 6. 컨테이너 시작 시 실행될 명령어
#    - simple_server_starter.py 파일을 Python으로 실행합니다.
#    - Koyeb의 "Run Command" 또는 "Entrypoint"에 해당합니다.
CMD ["python", "stock_analysis_service/simple_server_starter.py"]
