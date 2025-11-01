# LangGraph 기반 MCQ Generator

계층적 주제 선택과 중첩 선택을 지원하는 LangGraph 기반 MCQ 생성기입니다.

## 🎯 주요 특징

- ✅ **LangGraph StateGraph 사용**: 명시적 워크플로우 정의
- ✅ **중첩 선택 지원**: Part별로 다른 Chapter 전략 적용
- ✅ **7개 노드 구조**: 각 단계가 명확히 분리
- ✅ **하이브리드 재시도**: 1-5회는 빠른 재시도, 6회는 주제 변경 (최대 6회)
- ✅ **Few-shot Learning**: 예시 기반 품질 향상
- ✅ **Checkpointer**: 상태 저장/복원 지원
- ✅ **히스토리 추적**: MCQ 생성 기록 관리

## 📂 파일 구조

```
Generator/
├── State/
│   ├── state.py                    # RAG State
│   └── mcq_state.py                # MCQ State (신규)
│
├── Node/
│   ├── __init__.py                 # RAG + MCQ 노드 re-export
│   ├── retrieve.py                 # RAG 문서 검색
│   ├── context.py                  # RAG 컨텍스트 포맷팅
│   ├── answer.py                   # RAG 답변 생성
│   ├── output.py                   # RAG 출력 포맷팅
│   └── MCQ/                        # MCQ 노드 폴더 (신규)
│       ├── __init__.py             # MCQ 노드 exports
│       ├── select_part.py          # Part 선택
│       ├── select_chapter.py       # Chapter 선택
│       ├── retrieve_documents.py   # 문서 검색
│       ├── format_context.py       # 컨텍스트 포맷팅
│       ├── generate.py             # MCQ 생성
│       ├── validate.py             # 유효성 검증
│       └── format_output.py        # 출력 포맷팅
│
├── Edge/
│   ├── workflow_edges.py           # RAG 워크플로우 엣지
│   └── mcq_workflow_edges.py       # MCQ 워크플로우 엣지 (신규)
│
└── Core/
    ├── Generator.py                # RAG Generator (LangGraph)
    ├── Generator_MCQ.py            # MCQ Generator (LCEL, 기존)
    └── Generator_MCQ_LangGraph.py  # MCQ Generator (LangGraph, 신규)
```

## 🔄 워크플로우 구조

```
START
  ↓
[Node 1] select_part
  - 가중치 기반 Part 선택
  - State["selected_part"] = "Part 1"
  ↓
[Node 2] select_chapter
  - Part 내에서 Chapter 선택
  - State["selected_chapter"] = "Ch1"
  - State["selected_topic_query"] = "Part 1 - Ch1"
  ↓
[Node 3] retrieve_documents
  - 벡터 검색 수행
  - State["retrieved_documents"] = [doc1, doc2, ...]
  ↓ [조건부: 성공?]
  ├─ 실패 → select_part (재시도)
  └─ 성공 ↓
[Node 4] format_context
  - 문서 포맷팅
  - State["formatted_context"] = "..."
  ↓
[Node 5] generate_mcq
  - Few-shot 프롬프트 구성
  - LLM 호출
  - State["generated_mcq"] = {...}
  ↓
[Node 6] validate_mcq
  - 5가지 검증
  - State["is_valid"] = True/False
  ↓ [조건부: 하이브리드 재시도]
  ├─ 유효 → format_output
  ├─ 1-5회 무효 → retrieve_documents (빠른 재시도)
  ├─ 6회 무효 → select_part (새 주제 선택)
  └─ 7회 이상 → END
[Node 7] format_output
  - 메타데이터 추가
  - State["final_mcq"] = {...}
  ↓
END
```

## 🚀 사용 예시

### 1️⃣ 기본 사용법

```python
from Core.Generator_MCQ_LangGraph import Generator_MCQ_LangGraph

# 초기화
generator = Generator_MCQ_LangGraph(
    vector_store=vector_store,
    llm=llm
)

# 교재 구조 정의
topics_hierarchical = {
    "Part 1 응급의료체계": [
        "응급의료체계 개요",
        "응급의료기관",
        "응급구조사 역할",
    ],
    "Part 2 심폐소생술": [
        "심폐소생술 개요",
        "가슴압박",
    ],
}

# MCQ 생성
mcq = generator.generate_mcq(
    topics_hierarchical=topics_hierarchical
)

print(f"질문: {mcq['question']}")
print(f"정답: {mcq['answer_index']}번")
```

### 2️⃣ 중첩 선택 (Part별 다른 전략)

```python
# 중첩 선택 설정
topics_nested = {
    "Part 1 응급의료체계": {
        "chapters": ["응급의료체계 개요", "응급의료기관"],  # 특정 Chapter만
        "mode": "single",  # 하나씩 선택
        "weight": 0.6,     # 60% 확률
    },
    "Part 2 심폐소생술": {
        "chapters": ["*"],  # 모든 Chapter (와일드카드)
        "mode": "all",      # Part 전체 범위
        "weight": 0.4,      # 40% 확률
    },
}

# MCQ 생성
mcq = generator.generate_mcq(
    topics_hierarchical=topics_hierarchical,
    topics_nested=topics_nested
)

print(f"선택된 Part: {mcq['selected_part']}")
print(f"선택된 Chapter: {mcq['selected_chapter']}")
```

### 3️⃣ 배치 생성

```python
# 10개 MCQ 생성
mcqs = generator.generate_mcq_batch(
    topics_hierarchical=topics_hierarchical,
    topics_nested=topics_nested,
    count=10
)

for i, mcq in enumerate(mcqs, 1):
    print(f"{i}. {mcq['question']}")
```

### 4️⃣ 통계 및 히스토리

```python
# 통계 확인
stats = generator.get_mcq_statistics()
print(f"총 생성: {stats['total_count']}개")
print(f"Part별 분포: {stats['part_distribution']}")

# 히스토리 확인
history = generator.get_mcq_history()
for entry in history:
    print(f"{entry['timestamp']}: {entry['part']} - {entry['chapter']}")

# 히스토리 초기화
generator.clear_mcq_history()
```

## 📊 중첩 선택 옵션

### `chapters` 설정

```python
# 옵션 1: 특정 Chapter만
"chapters": ["Ch1", "Ch2"]

# 옵션 2: 모든 Chapter (와일드카드)
"chapters": ["*"]
```

### `mode` 설정

```python
# 옵션 1: 단일 선택 (지정된 Chapter 중 하나)
"mode": "single"

# 옵션 2: 전체 범위 (Part 전체를 다루는 문제)
"mode": "all"
```

### `weight` 설정

```python
# Part별 선택 가중치 (확률)
"weight": 0.5  # 50% 확률로 이 Part 선택
```

## 🎯 중첩 선택 패턴

### 패턴 1: Part 일부 + Chapter 하나씩
```python
{
    "Part 1": {
        "chapters": ["Ch1", "Ch2", "Ch3"],  # 일부 Chapter만
        "mode": "single",                    # 하나씩
        "weight": 1.0
    }
}
```

### 패턴 2: Part 전체 + Chapter 전체
```python
{
    "Part 1": {
        "chapters": ["*"],  # 모든 Chapter
        "mode": "all",      # 전체 범위
        "weight": 1.0
    }
}
```

### 패턴 3: Part 일부 + Chapter 전체
```python
{
    "Part 1": {
        "chapters": ["Ch1", "Ch2"],  # 일부만
        "mode": "all",                # 이 2개를 전체로
        "weight": 1.0
    }
}
```

### 패턴 4: 복수 Part 혼합
```python
{
    "Part 1": {
        "chapters": ["Ch1", "Ch2"],
        "mode": "single",
        "weight": 0.5
    },
    "Part 2": {
        "chapters": ["*"],
        "mode": "all",
        "weight": 0.5
    }
}
```

## 🔍 기존 Generator_MCQ vs Generator_MCQ_LangGraph

| 항목 | Generator_MCQ (기존) | Generator_MCQ_LangGraph (신규) |
|------|---------------------|-------------------------------|
| **아키텍처** | LCEL 체인 | LangGraph StateGraph |
| **노드 구조** | ❌ 없음 | ✅ 7개 노드 |
| **재시도 로직** | for loop | 조건부 엣지 |
| **상태 관리** | 내부 변수 | MCQState (TypedDict) |
| **추적 가능성** | 보통 | ✅ 높음 (각 노드별) |
| **확장성** | 보통 | ✅ 높음 (노드 추가 용이) |
| **중첩 선택** | ❌ 미지원 | ✅ 지원 |

## 🆚 LangGraph vs LCEL 비교

### LCEL 방식 (기존 Generator_MCQ)
```python
mcq_chain = (
    {
        "context": retriever | format_documents_for_llm,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | JsonOutputParser()
)
```
- ✅ 간결함
- ❌ 재시도 로직 복잡
- ❌ 중간 상태 추적 어려움

### LangGraph 방식 (신규 Generator_MCQ_LangGraph)
```python
workflow = StateGraph(MCQState)
workflow.add_node("select_part", select_part)
workflow.add_node("select_chapter", select_chapter)
# ... 7개 노드
workflow.add_conditional_edges(
    "validate_mcq",
    should_retry,
    {"retry": "select_part", "end": END}
)
```
- ✅ 명확한 흐름
- ✅ 조건부 재시도 쉬움
- ✅ 각 단계 추적 가능
- ✅ 노드 단위 확장 용이

## 📝 MCQ State 구조

```python
class MCQState(TypedDict):
    # 입력
    topics_nested: Optional[Dict[str, Dict[str, Any]]]
    topics_hierarchical: Optional[Dict[str, List[str]]]
    
    # 선택 결과
    selected_part: str
    selected_chapter: str
    selected_topic_query: str
    available_chapters: List[str]
    
    # 문서 검색
    retrieved_documents: List[Document]
    formatted_context: str
    
    # MCQ 생성
    instruction: str
    few_shot_examples: List[Dict]
    generated_mcq: Optional[Dict]
    
    # 검증
    is_valid: bool
    validation_errors: List[str]
    
    # 재시도
    retry_count: int
    max_retries: int
    should_retry: bool
    
    # 출력
    final_mcq: Optional[Dict]
```

## 🎓 검증 항목 (5가지)

1. **필수 필드**: question, options, answer_index, explanation
2. **options 개수**: 정확히 4개
3. **answer_index 범위**: 1-4 사이
4. **옵션 중복**: 중복 없음
5. **빈 필드**: 모든 필드 비어있지 않음

## 🔧 설정 가능 옵션

```python
generator.generate_mcq(
    topics_hierarchical=topics,      # 필수: 전체 구조
    topics_nested=nested_config,     # 선택: 중첩 선택
    max_retries=3                    # 선택: 최대 재시도 (기본 3)
)
```

## 📖 상세 예시 파일

`example_mcq_langgraph.py`를 참조하세요:
- 기본 사용법
- 중첩 선택
- 배치 생성
- 통계 확인
- 와일드카드 사용

## 🚀 시작하기

```python
from langchain_google_vertexai import VertexAI, VectorSearchVectorStore
from Core.Generator_MCQ_LangGraph import Generator_MCQ_LangGraph

# 1. 벡터 스토어 및 LLM 설정
vector_store = VectorSearchVectorStore.from_components(...)
llm = VertexAI(model_name="gemini-1.5-pro")

# 2. Generator 초기화
generator = Generator_MCQ_LangGraph(
    vector_store=vector_store,
    llm=llm
)

# 3. MCQ 생성
mcq = generator.generate_mcq(topics_hierarchical=your_topics)
```

## 💡 팁

1. **와일드카드 사용**: `["*"]`로 모든 Chapter 선택
2. **가중치 조절**: Part별 출제 비율 조정 가능
3. **모드 혼합**: Part마다 single/all 모드 다르게 설정
4. **히스토리 활용**: 생성 패턴 분석에 활용
5. **배치 생성**: 한 번에 여러 개 생성으로 효율성 향상

## 🔍 디버깅

워크플로우 구조 확인:
```python
from Edge import get_mcq_workflow_description
print(get_mcq_workflow_description())
```

## 📌 주의사항

1. **vector_store와 llm 필수**: 두 객체 모두 제공 필요
2. **topics_hierarchical 필수**: 전체 구조는 반드시 정의
3. **topics_nested 선택**: 중첩 선택이 필요할 때만 사용
4. **재시도 제한**: 최대 3회까지 자동 재시도

## 🎯 LangGraph 원칙 준수

이 구현은 LangGraph의 모든 권장 방식을 따릅니다:

1. ✅ StateGraph 사용
2. ✅ 노드 명시적 정의 (`add_node`)
3. ✅ 엣지 명시적 정의 (`add_edge`, `add_conditional_edges`)
4. ✅ START/END 사용
5. ✅ Checkpointer 포함
6. ✅ 팩토리 패턴
7. ✅ 노드는 업데이트할 필드만 반환

---

Made with ❤️ using LangGraph

