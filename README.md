# Generator Dock - LangGraph 기반 RAG & MCQ 시스템

Vertex AI와 LangGraph를 활용한 RAG(Retrieval-Augmented Generation) 질의응답 시스템 및 MCQ(Multiple Choice Question) 자동 생성기

## 🎯 주요 기능

- ✅ **LangGraph StateGraph** 기반 워크플로우
- ✅ **RAG 시스템**: Vertex AI Vector Search 기반 질의응답 (Ask Mode)
- ✅ **MCQ 생성**: 계층적 주제 선택 및 자동 문제 생성 (Forge Mode)
- ✅ **FastAPI REST API**: 프론트엔드 연동 지원
- ✅ **Few-shot Learning**: JSON 기반 예시 학습
- ✅ **다양성 추적**: 리듬, 질문 형식, 시간대, 논리 추적
- ✅ **Checkpointer**: 상태 저장/복원 지원

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
# Manual/env.example.txt를 복사하여 .env 생성
copy Manual\env.example.txt .env
# .env 파일을 실제 GCP 값으로 수정
```

### 3. 실행 방법

#### **테스트용 (CLI)** - main.py
```bash
python main.py
```
- 대화형 MCQ 생성 인터페이스
- 범위별 문제 생성 (총론, 법령, 각론)
- 동형모의고사 40문제 생성

#### **웹앱용 (API)** - api.py
```bash
# 방법 1: 직접 실행
uvicorn api:app --reload --port 8000

# 방법 2: 배치 파일
run_api.bat
```
- FastAPI REST API 서버
- Swagger UI: http://localhost:8000/docs
- 프론트엔드 연동 가능

## 📚 주요 컴포넌트

### Ask Mode - RAG 질의응답 (`Core/ask_mode.py`)
```python
from Core import AskMode

ask_mode = AskMode(logger=logger)
result = ask_mode.process("응급의료기관의 종류는?")
print(result["answer"])
print(result["source_documents"])
```

### Forge Mode - MCQ 생성 (`Core/forge_mode.py`)
```python
from Core import ForgeMode

forge_mode = ForgeMode(
    vector_store=vector_store,
    llm=llm,
    logger=logger
)

# 특정 주제로 MCQ 생성
mcq = forge_mode.generate_mcq(
    topics_hierarchical=topics,
    user_topic="전문심장소생술",
    category_weights={"ECG_BASED": 0.7}
)
print(mcq["question"])
print(mcq["options"])
```

### API 사용 - FastAPI REST API (`api.py`)
```bash
# 서버 실행
uvicorn api:app --reload --port 8000

# API 문서
http://localhost:8000/docs
```

**주요 엔드포인트**:
- `POST /api/ask`: RAG 질의응답
- `POST /api/forge`: MCQ 생성
- `GET /api/health`: 헬스 체크
- `GET /api/textbook`: 교재 구조

## 📂 프로젝트 구조

```
Generator_Dock_Test/
├── main.py                  # 🖥️  테스트용 CLI (대화형 MCQ 생성)
├── api.py                   # 🌐 FastAPI REST API (웹앱용)
├── run_api.bat              # API 실행 스크립트
├── config.py                # 설정 관리 (GCP, 교재 구조, 가중치)
├── requirements.txt         # Python 의존성
│
├── Core/                    # 핵심 모드
│   ├── ask_mode.py          # Ask Mode (RAG 질의응답)
│   └── forge_mode.py        # Forge Mode (MCQ 생성)
│
├── State/                   # LangGraph State
│   └── state.py             # 통합 State 정의
│
├── Node/                    # LangGraph 노드
│   ├── RAG/                 # Ask Mode 노드
│   │   ├── retrieve.py      # 문서 검색
│   │   ├── context.py       # 컨텍스트 선택
│   │   ├── answer.py        # 답변 생성
│   │   └── ...
│   └── MCQ/                 # Forge Mode 노드
│       ├── retrieve_documents.py  # 문서 검색
│       ├── select_context.py      # 컨텍스트 선택
│       ├── generate.py            # MCQ 생성
│       └── validate.py            # 검증
│
├── Edge/                    # LangGraph 엣지 (워크플로우 로직)
│   ├── RAG/
│   │   └── workflow_edges.py
│   └── MCQ/
│       └── mcq_workflow_edges.py
│
├── Utils/                   # 유틸리티
│   ├── few_shot.py          # Few-shot 로딩
│   ├── rhythm_tracker.py    # 리듬 다양성 추적
│   ├── diversity_tracker.py # 질문 형식 추적
│   ├── logic_pool_tracker.py # 논리(5H5T) 추적
│   └── ...
│
├── Data/
│   ├── Few_Shot/            # Few-shot 예시 (209개)
│   │   ├── Single_Type.json     # 단순형 (73개)
│   │   ├── Case_Type.json       # 케이스형 (69개)
│   │   ├── ECG_Type.json        # 심전도형 (42개)
│   │   ├── Multiple_Type.json   # 복수형 (15개)
│   │   └── Image_Type.json      # 이미지형 (10개)
│   ├── Prompts/             # 프롬프트 템플릿 (범위별)
│   └── Result/              # 생성된 MCQ 결과
│
└── Manual/                  # 📖 문서
    ├── INDEX.md             # 문서 목차
    ├── PROJECT_README.md
    ├── MCQ_LANGGRAPH_README.md
    ├── FEW_SHOT_GUIDE.md
    └── ...
```

## 📖 상세 문서

모든 상세 문서는 **[`Manual/`](Manual/)** 폴더에 있습니다.

### 🎯 시작하기
- **[INDEX.md](Manual/INDEX.md)**: 전체 문서 목록 및 가이드 ⭐
- **[PROJECT_README.md](Manual/PROJECT_README.md)**: 프로젝트 상세 설명
- **[ENVIRONMENT_SETUP.md](Manual/ENVIRONMENT_SETUP.md)**: 환경 설정 가이드

### 🎓 MCQ 시스템
- **[MCQ_LANGGRAPH_README.md](Manual/MCQ_LANGGRAPH_README.md)**: MCQ Generator 완전 가이드 ⭐
- **[FEW_SHOT_GUIDE.md](Manual/FEW_SHOT_GUIDE.md)**: Few-shot Learning 설명서
- **[SETUP_INSTRUCTIONS.md](Manual/SETUP_INSTRUCTIONS.md)**: 빠른 설정 가이드

## 🔗 프론트엔드 연동

프론트엔드 프로젝트: `C:\Development\UI_Dock_Test`

### 연결 방법
1. 백엔드 실행: `uvicorn api:app --reload --port 8000`
2. 프론트엔드 실행: `cd UI_Dock_Test/frontend && npm run dev`
3. 브라우저: `http://localhost:5178`

자세한 내용은 `C:\Development\INTEGRATION_GUIDE.md` 참고

---

**버전**: 3.0.0  
**최종 업데이트**: 2025-11-04

## 📝 변경 이력

### v3.0.0 (2025-11-04)
- ✅ FastAPI REST API 추가 (`api.py`)
- ✅ 프론트엔드 연동 지원
- ❌ Streamlit, Gradio 앱 제거
- ✅ 프로젝트 구조 단순화

### v2.0.0 (2025-10-21)
- ✅ LangGraph 기반 워크플로우
- ✅ Ask Mode, Forge Mode 분리
- ✅ 다양성 추적 시스템

