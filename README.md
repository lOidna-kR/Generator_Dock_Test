# Generator - LangGraph 기반 RAG & MCQ 시스템

Vertex AI와 LangGraph를 활용한 RAG(Retrieval-Augmented Generation) 질의응답 시스템 및 MCQ(Multiple Choice Question) 자동 생성기

## 🎯 주요 기능

- ✅ **LangGraph StateGraph** 기반 워크플로우
- ✅ **RAG 시스템**: Vertex AI Vector Search 기반 질의응답
- ✅ **MCQ 생성**: 계층적 주제 선택 및 자동 문제 생성
- ✅ **중첩 선택**: Part별로 다른 Chapter 선택 전략
- ✅ **Few-shot Learning**: JSON 기반 예시 학습
- ✅ **Checkpointer**: 상태 저장/복원 지원

## 🚀 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
copy env.example.txt .env
# .env 파일을 실제 값으로 수정

# 3. 설정 검증
python config.py

# 4-1. RAG 시스템 실행
python RAG_main.py

# 4-2. MCQ 생성 실행
python MCQ_main.py
```

## 📚 주요 컴포넌트

### RAG Generator (`Core/Generator.py`)
```python
from Core import Generator

generator = Generator(vector_store=vector_store)
result = generator.process("응급의료기관의 종류는?")
print(result["answer"])
```

### MCQ Generator (`Core/MCQ_Generator.py`)
```python
from Core import MCQ_Generator

generator = MCQ_Generator(
    vector_store=vector_store,
    llm=llm
)

mcq = generator.generate_mcq(topics_hierarchical=topics)
print(mcq["question"])
```

## 📂 프로젝트 구조

```
Generator/
├── RAG_main.py              # RAG 시스템 실행
├── MCQ_main.py              # MCQ 생성 실행
├── config.py                # 설정 관리
├── Core/                    # 메인 Generator
│   ├── Generator.py         # RAG Generator
│   └── MCQ_Generator.py     # MCQ Generator
├── State/                   # 상태 관리
│   ├── RAG/                 # RAG State
│   └── MCQ/                 # MCQ State
├── Node/                    # 워크플로우 노드
│   ├── RAG/                 # RAG 노드
│   └── MCQ/                 # MCQ 노드
├── Edge/                    # 워크플로우 엣지
│   ├── RAG/                 # RAG 엣지
│   └── MCQ/                 # MCQ 엣지
├── Utils/                   # 유틸리티
├── Data/
│   └── Few_Shot/            # Few-shot 예시
│       └── MCQ_GENERAL.json
└── Manual/                  # 📖 문서
    ├── INDEX.md
    ├── PROJECT_README.md
    ├── MCQ_LANGGRAPH_README.md
    └── FEW_SHOT_GUIDE.md
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

---

**버전**: 2.0.0  
**최종 업데이트**: 2025-10-21

