# 🚀 빠른 설정 가이드

프로젝트를 처음 설정하는 경우 이 가이드를 따라주세요.

## ⏱️ 예상 소요 시간: 10분

---

## 1️⃣ 의존성 설치 (2분)

```bash
pip install -r requirements.txt
```

**설치되는 패키지:**
- langgraph, langchain (워크플로우)
- langchain-google-vertexai (Vertex AI 연동)
- google-cloud-aiplatform (GCP)
- python-dotenv (환경 변수)

---

## 2️⃣ 환경 변수 설정 (5분)

### Step 1: .env 파일 생성
```bash
# Windows
copy env.example.txt .env

# Linux/Mac
cp env.example.txt .env
```

### Step 2: 필수 값 수정

.env 파일을 열어서 다음 항목을 **반드시 수정**하세요:

```bash
# 🔴 필수 (반드시 수정!)
GCP_PROJECT_ID=your-project-id              # → 실제 프로젝트 ID
VERTEX_AI_INDEX_ID=your-index-id            # → 실제 Index ID
VERTEX_AI_ENDPOINT_ID=your-endpoint-id      # → 실제 Endpoint ID
GCS_BUCKET_NAME=your-bucket-name            # → 실제 버킷 이름
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key # → 실제 키 경로

# 🟡 선택 (기본값 사용 가능)
GEMINI_MODEL_NAME=gemini-1.5-flash-002
EMBEDDING_MODEL=text-embedding-004
RETRIEVAL_K=5
LLM_TEMPERATURE=0.7
```

**각 값을 어디서 확인하는지는 `Manual/ENVIRONMENT_SETUP.md` 참고**

### Step 3: 설정 검증
```bash
python config.py
```

**성공 시:**
```
✅ 모든 필수 환경 변수가 설정되었습니다.
```

**실패 시:**
```
❌ 누락된 환경 변수: GCP_PROJECT_ID, ...
```
→ .env 파일을 다시 확인하세요!

---

## 3️⃣ 테스트 실행 (3분)

```bash
python main.py
```

**정상 동작 시:**
```
==============================
LangGraph Generator 기본 사용 테스트
==============================
✅ Generator 초기화 완료
...
질문: 응급의료기관의 종류는 무엇인가요?
답변: ...
✅ 기본 사용 테스트 완료
```

---

## ✅ 완료 체크리스트

설정이 완료되었는지 확인하세요:

- [ ] `pip install -r requirements.txt` 실행 완료
- [ ] `.env` 파일 생성됨
- [ ] `.env` 파일에 실제 값 입력됨
- [ ] `python config.py` 실행 시 ✅ 표시됨
- [ ] `python main.py` 실행 시 정상 동작
- [ ] `.env` 파일이 Git에 커밋되지 않음 (`git status` 확인)

---

## 🆘 도움이 필요하신가요?

### 상세 가이드
- **전체 설정**: `Manual/ENVIRONMENT_SETUP.md`
- **프로젝트 구조**: `Manual/FINAL_PROJECT_STRUCTURE.md`
- **사용 방법**: `README.md`

### 설정 값 확인 방법

| 필요한 값 | 확인 위치 |
|-----------|----------|
| GCP 프로젝트 ID | GCP 콘솔 > 홈 > 프로젝트 정보 |
| Index ID | Vertex AI > Vector Search > Indexes |
| Endpoint ID | Vertex AI > Vector Search > Index Endpoints |
| 버킷 이름 | Cloud Storage > 버킷 목록 |
| 서비스 계정 키 | IAM > 서비스 계정 > 키 생성 |

---

**설정 완료 후 바로 사용할 수 있습니다!** 🎉

