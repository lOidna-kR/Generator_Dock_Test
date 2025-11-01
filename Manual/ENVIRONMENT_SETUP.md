# 환경 설정 가이드

## 🔐 민감정보 관리 방법

이 프로젝트는 API 키, 프로젝트 ID 등 민감한 정보를 **환경 변수**로 관리합니다.

## 📋 설정 파일 구조

```
Generator/
├── .env                    # 실제 민감정보 (Git 제외 ❌)
├── env.example.txt         # 템플릿 (Git 포함 ✅)
├── .gitignore              # .env 제외 설정
└── config.py               # 설정 로더
```

---

## 🚀 초기 설정 (3단계)

### Step 1: .env 파일 생성

```bash
# env.example.txt를 .env로 복사
cp env.example.txt .env

# Windows
copy env.example.txt .env
```

### Step 2: .env 파일 수정

```bash
# .env 파일을 에디터로 열기
# Windows
notepad .env

# Linux/Mac
nano .env
```

**필수 항목 수정:**

| 변수명 | 확인 방법 | 예시 |
|--------|----------|------|
| `GCP_PROJECT_ID` | GCP 콘솔 > 프로젝트 설정 | `yang-first-aid` |
| `VERTEX_AI_INDEX_ID` | Vertex AI > Vector Search > Indexes | `8376679913746333696` |
| `VERTEX_AI_ENDPOINT_ID` | Vertex AI > Vector Search > Endpoints | `1234567890123456789` |
| `GCS_BUCKET_NAME` | Cloud Storage > 버킷 | `rag-cloud-run-test` |
| `GOOGLE_APPLICATION_CREDENTIALS` | 서비스 계정 키 경로 | `C:/keys/service-account.json` |

### Step 3: 설정 검증

```bash
# 설정 확인
python config.py

# 출력 예시:
# ✅ 모든 필수 환경 변수가 설정되었습니다.
```

---

## 🔍 각 설정 항목 상세 가이드

### 1. GCP 프로젝트 ID

**확인 방법:**
1. [GCP 콘솔](https://console.cloud.google.com) 접속
2. 상단 프로젝트 선택 메뉴 클릭
3. 프로젝트 ID 복사

**예시:**
```bash
GCP_PROJECT_ID=yang-first-aid
```

### 2. Vertex AI Index ID

**확인 방법:**
1. GCP 콘솔 > Vertex AI > Vector Search
2. Indexes 탭에서 인덱스 선택
3. Index ID 복사 (긴 숫자)

**예시:**
```bash
VERTEX_AI_INDEX_ID=8376679913746333696
```

### 3. Vertex AI Endpoint ID

**확인 방법:**
1. GCP 콘솔 > Vertex AI > Vector Search
2. Index Endpoints 탭에서 엔드포인트 선택
3. Endpoint ID 복사

**예시:**
```bash
VERTEX_AI_ENDPOINT_ID=1234567890123456789
```

### 4. Cloud Storage 버킷

**확인 방법:**
1. GCP 콘솔 > Cloud Storage
2. 버킷 목록에서 버킷 이름 확인

**예시:**
```bash
GCS_BUCKET_NAME=rag-cloud-run-test
```

### 5. 서비스 계정 키

**생성 방법:**
1. GCP 콘솔 > IAM 및 관리자 > 서비스 계정
2. 서비스 계정 선택 (또는 새로 생성)
3. 키 탭 > 키 추가 > JSON 선택
4. 다운로드한 JSON 파일을 안전한 위치에 저장
5. 절대 경로를 .env에 설정

**필요한 권한:**
- Vertex AI User
- Storage Object Viewer

**예시:**
```bash
# Windows
GOOGLE_APPLICATION_CREDENTIALS=C:/keys/service-account.json

# Linux/Mac
GOOGLE_APPLICATION_CREDENTIALS=/home/user/keys/service-account.json
```

---

## ⚙️ 선택적 설정

### 모델 설정

```bash
# Gemini 모델 선택
GEMINI_MODEL_NAME=gemini-1.5-flash-002   # 빠르고 저렴
# GEMINI_MODEL_NAME=gemini-1.5-pro-002   # 느리지만 고품질

# 임베딩 모델
EMBEDDING_MODEL=text-embedding-004
```

### Retrieval 튜닝

```bash
# 검색할 문서 수 (많을수록 정확하지만 느림)
RETRIEVAL_K=5

# 유사도 임계값 (높을수록 관련성 높은 문서만)
SIMILARITY_THRESHOLD=0.7
```

### LLM 파라미터

```bash
# Temperature (0.0 ~ 2.0)
# 낮음: 일관적/정확한 답변
# 높음: 창의적/다양한 답변
LLM_TEMPERATURE=0.7

# 최대 출력 토큰 (길이 제한)
MAX_OUTPUT_TOKENS=2048
```

---

## 🐛 문제 해결

### ❌ "환경 변수가 설정되지 않았습니다"

**원인:**
- .env 파일이 없거나
- .env 파일의 값이 기본값(your-xxx-here)으로 남아있음

**해결:**
```bash
# .env 파일 확인
cat .env

# env.example.txt에서 다시 복사
cp env.example.txt .env

# 실제 값으로 수정
```

### ❌ "python-dotenv를 찾을 수 없습니다"

**해결:**
```bash
pip install python-dotenv
```

### ❌ "서비스 계정 키를 찾을 수 없습니다"

**원인:**
- `GOOGLE_APPLICATION_CREDENTIALS` 경로가 잘못됨
- 파일이 존재하지 않음

**해결:**
```bash
# 경로 확인 (절대 경로 사용)
# Windows: C:/keys/service-account.json
# Linux/Mac: /home/user/keys/service-account.json

# 파일 존재 확인
ls $GOOGLE_APPLICATION_CREDENTIALS  # Linux/Mac
dir %GOOGLE_APPLICATION_CREDENTIALS%  # Windows
```

### ❌ Cursor가 .env를 못 읽습니다

**이유:**
- .gitignore에 .env가 포함되어 Cursor가 무시함 (보안!)

**해결 (개발 중에만):**
1. `env.example.txt` 파일에서 설정 확인 (Cursor가 읽을 수 있음)
2. `config.py`의 주석 참고 (Cursor가 읽을 수 있음)
3. `README.md`의 가이드 참고 (Cursor가 읽을 수 있음)

**✅ 이것이 정상입니다!** .env의 민감정보를 AI가 학습하는 것을 방지합니다.

---

## 🔒 보안 체크리스트

설정 완료 후 다음을 확인하세요:

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있음
- [ ] `.env` 파일을 Git에 커밋하지 않음 (`git status`로 확인)
- [ ] 서비스 계정 키 JSON 파일도 `.gitignore`에 포함
- [ ] `env.example.txt`에는 실제 값이 없음 (템플릿만)
- [ ] README.md에 설정 방법이 문서화되어 있음

---

## 📚 추가 참고

### GCP 인증 방법

프로젝트는 다음 순서로 인증을 시도합니다:

1. **GOOGLE_APPLICATION_CREDENTIALS** 환경 변수
2. **Application Default Credentials (ADC)**
   ```bash
   gcloud auth application-default login
   ```
3. **GCP 인스턴스 메타데이터** (Cloud Run, GCE에서 실행 시)

로컬 개발 시에는 **방법 1 (서비스 계정 키)** 권장합니다.

### 환경별 설정

**개발 환경:**
```bash
# .env.development
GCP_PROJECT_ID=dev-project
VERTEX_AI_INDEX_ID=dev-index-id
```

**프로덕션 환경:**
```bash
# .env.production
GCP_PROJECT_ID=prod-project
VERTEX_AI_INDEX_ID=prod-index-id
```

**사용:**
```python
# 환경별 .env 로드
import os
env = os.getenv("ENV", "development")
load_dotenv(f".env.{env}")
```

---

**설정 완료 후 `python main.py`로 실행하세요!** 🚀

