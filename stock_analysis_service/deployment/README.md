# 🚀 HyperAsset LLM 배포 도구

이 디렉토리는 **HyperAsset LLM 주식 분석 시스템**의 배포를 위한 모든 도구들을 포함합니다.

## 📁 파일 구조

```
deployment/
├── README.md                    # 이 파일 (사용법 가이드)
├── FIREBASE_DEPLOYMENT_README.md # 완전한 배포 가이드
├── DEPLOYMENT_CHECKLIST.md      # 배포 체크리스트
├── deploy.sh                    # 전체 자동 배포 스크립트 (프론트+백엔드)
├── quick-deploy.sh              # 프론트엔드 전용 배포 스크립트
├── deploy-backend.sh            # 백엔드 전용 배포 스크립트
├── check-connection.sh          # 연결 확인 스크립트
├── Dockerfile                   # Cloud Run 배포용
├── .dockerignore                # Docker 빌드 최적화
└── chromadb_config.py           # 프로덕션 ChromaDB 설정
```

## 🎯 배포 옵션

### 1. 전체 배포 (프론트+백엔드)
```bash
# Linux/Mac
chmod +x deploy.sh
./deploy.sh

# Windows PowerShell
./deploy.sh
```

### 2. 프론트엔드만 배포
```bash
chmod +x quick-deploy.sh
./quick-deploy.sh
```

### 3. 백엔드만 배포
```bash
chmod +x deploy-backend.sh
./deploy-backend.sh
```

### 4. 연결 확인
```bash
chmod +x check-connection.sh
./check-connection.sh
```

## 🛠️ 권장 워크플로우

- **UI/프론트엔드만 변경**: `quick-deploy.sh` 실행
- **API/백엔드만 변경**: `deploy-backend.sh` 실행
- **전체 변경/최초 배포**: `deploy.sh` 실행
- **배포 후 연결 확인**: `check-connection.sh` 실행

## 🌐 배포 후 URL

- **Frontend**: https://hyperasset-llm.web.app
- **Backend**: https://stock-analysis-api-xxxxx-xx.a.run.app
- **API Docs**: https://stock-analysis-api-xxxxx-xx.a.run.app/docs

## 🚨 문제 해결/문의
- `FIREBASE_DEPLOYMENT_README.md` 및 `DEPLOYMENT_CHECKLIST.md` 참고
- 로그 확인: `firebase hosting:channel:list`, `gcloud logs read --service=stock-analysis-api`
- 개발팀에 문의

---

**🎉 분리 배포로 효율적이고 안전하게 운영하세요!** 