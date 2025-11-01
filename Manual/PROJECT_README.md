# LangGraph Generator

LangGraph 기반 RAG (Retrieval-Augmented Generation) 시스템

## 🎯 주요 기능

- ✅ **LangGraph StateGraph** 사용한 명시적 워크플로우
- ✅ **Vertex AI** 통합 (Gemini, Embeddings, Vector Search)
- ✅ **모듈화된 구조** (State, Node, Edge 분리)
- ✅ **대화 이력 지원** (add_messages 활용)
- ✅ **스트리밍 지원** (실시간 응답)
- ✅ **확장 가능한 설계** (조건부 엣지, 멀티 소스 검색 준비)

## 📁 프로젝트 구조

```
Generator/
├── Core/              # 메인 Generator 클래스
│   ├── __init__.py
│   └── Generator.py
│
├── State/             # 상태 관리
│   ├── __init__.py
│   └── state.py       (State 정의 + Helper 함수)
│
├── Node/              # 워크플로우 노드 (기능별 그룹화)
│   ├── __init__.py
│   ├── retrieval.py   (검색 + 포맷팅)
│   └── generation.py  (생성 + 출력)
│
├── Edge/              # 워크플로우 엣지 (중앙 관리)
│   ├── __init__.py
│   └── workflow_edges.py
│
├── Utils/             # 유틸리티
│   ├── __init__.py
│   ├── document.py    (문서 포맷팅)
│   ├── file.py        (파일 처리)
│   ├── logging.py     (로깅 설정)
│   ├── search.py      (벡터 검색)
│   └── system.py      (시스템 정보)
│
├── Manual/            # 📖 프로젝트 문서
│   ├── README.md
│   ├── FINAL_PROJECT_STRUCTURE.md
│   ├── CONVERSATION_EXAMPLE.md
│   └── ...
│
├── Debug/             # 🔧 디버깅/테스트 파일
│   ├── README.md
│   └── main_test_backup.py
│
├── main.py            # 🎯 대화형 RAG 인터페이스 (메인 진입점)
├── config.py          # ⚙️ 설정 관리
├── requirements.txt   # 📦 의존성
├── .env               # 🔒 환경 변수 (Git 제외)
├── env.example.txt    # 📝 환경 변수 템플릿
├── .gitignore
└── README.md
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install langgraph langchain-google-vertexai python-dotenv google-cloud-aiplatform
```

### 2. 환경 변수 설정

#### Step 1: 환경 변수 파일 생성
```bash
# env.example.txt를 .env로 복사
cp env.example.txt .env

# 또는 Windows에서
copy env.example.txt .env
```

#### Step 2: .env 파일 수정
```bash
# 필수 설정 (반드시 수정 필요!)
GCP_PROJECT_ID=your-project-id              # GCP 프로젝트 ID
VERTEX_AI_INDEX_ID=8376679913746333696      # Vector Search Index ID
VERTEX_AI_ENDPOINT_ID=1234567890123456789   # Endpoint ID
GCS_BUCKET_NAME=your-bucket-name            # Cloud Storage 버킷

# 서비스 계정 키 (절대 경로)
GOOGLE_APPLICATION_CREDENTIALS=C:/keys/service-account.json
```

#### Step 3: 설정 검증
```bash
# 설정이 올바른지 확인
python config.py

# 또는 Python에서
python -c "from config import validate_config; validate_config()"
```

**⚠️ 주의사항:**
- `.env` 파일은 **절대 Git에 커밋하지 마세요!**
- `.gitignore`에 `.env`가 포함되어 있는지 확인하세요.
- `env.example.txt`는 템플릿이므로 Git에 포함해도 안전합니다.

### 3. 실행

#### 대화형 인터페이스 (권장)

```bash
# main.py 실행
python main.py
```

실행하면 대화형 인터페이스가 시작됩니다:
```
질문: 응급의료기관의 종류는?
🔄 처리 중...

📝 답변
응급의료기관은 ...

📚 출처 문서 (5개)
[1] ...
```

종료: `quit`, `exit`, `q`, `종료` 입력

#### 프로그래밍 방식

```python
from Core import Generator

# Generator 생성 (config.py 설정 사용)
generator = Generator(vector_store=None)

# 질문 처리
result = generator.process("응급의료기관의 종류는?")

print(result["answer"])
print(f"출처 문서: {result['num_sources']}개")
```

#### 스트리밍

```python
async for event in generator.process_stream("질문"):
    node = event.get("node")
    if node == "generate_answer":
        print(event["output"]["answer"])
```

## 🏗️ 워크플로우

```
START
  ↓
retrieve_documents (문서 검색)
  ↓
format_context (검색 결과 포맷팅)
  ↓
generate_answer (LLM 답변 생성)
  ↓
format_output (최종 출력 포맷팅)
  ↓
END
```

## 📖 문서

상세한 문서는 `Manual/` 폴더를 참고하세요:

- **FINAL_PROJECT_STRUCTURE.md**: 전체 프로젝트 구조 가이드 ⭐
- **CONVERSATION_EXAMPLE.md**: 대화형 RAG 구현 가이드
- **REFACTORING_NODE_STRUCTURE.md**: Node 모듈 설계 가이드
- **EDGE_MODULE_RESTRUCTURE.md**: Edge 모듈 사용 가이드
- **REMOVE_ERROR_HANDLER.md**: 에러 처리 설계 가이드

## 🎨 설계 원칙

### 1. 최신 LangGraph 권장 방식 준수
- ✅ `Annotated` + `add_messages` (메시지 관리)
- ✅ `operator.add` (리스트 병합)
- ✅ `START`, `END` 사용
- ✅ `MemorySaver` (Checkpointer)

### 2. 모듈화 및 응집도
- ✅ 기능별 그룹화 (retrieval, generation)
- ✅ 각 노드의 자체 완결성
- ✅ 엣지 중앙 관리

### 3. 확장 가능성
- ✅ 대화 이력 (messages 필드)
- ✅ 조건부 엣지 (Edge 모듈)
- ✅ 멀티 소스 검색 (operator.add)

## 🔧 API 서버 예제

### FastAPI

```python
from fastapi import FastAPI
from Core import Generator

app = FastAPI()

# 앱 시작 시 한 번만 초기화
@app.on_event("startup")
async def startup():
    global generator
    generator = Generator()

@app.post("/ask")
async def ask(question: str):
    result = generator.process(question)
    return result
```

## 📦 주요 모듈

| 모듈 | 역할 | 주요 기능 |
|------|------|-----------|
| **Core** | RAG 엔진 | Generator 클래스, 워크플로우 오케스트레이션 |
| **State** | 상태 관리 | State 정의, Helper 함수 |
| **Node** | 비즈니스 로직 | 검색, 생성, 포맷팅 |
| **Edge** | 제어 흐름 | 엣지 정의, 조건부 로직 |
| **Utils** | 유틸리티 | 문서 처리, 로깅, 검색 |

## 🌟 향후 확장

현재 구조는 다음 기능들을 쉽게 추가할 수 있도록 설계되었습니다:

- **대화 이력**: messages 필드 활용
- **재시도 로직**: Edge/workflow_edges.py에서 활성화
- **캐싱**: WorkflowEdgeConfig 설정
- **병렬 검색**: 멀티 소스 노드 추가
- **답변 품질 체크**: 조건부 엣지 추가

자세한 내용은 `Manual/` 폴더의 각 문서를 참고하세요.

## 📝 라이선스

프로젝트 라이선스 정보

---

**버전**: 1.0.0  
**최종 업데이트**: 2025-10-18

