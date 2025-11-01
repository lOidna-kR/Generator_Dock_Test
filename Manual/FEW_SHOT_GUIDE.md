# Few-shot Learning 가이드

LangGraph 기반 MCQ Generator의 Few-shot Learning 시스템 설명서입니다.

## 📁 파일 구조

```
Generator/
├── Data/
│   └── Dock_Exam_2025/
│       └── few_shot_examples.json  # Few-shot 예시 저장 (신규)
│
├── config.py                        # Few-shot 설정 로드
│
├── Utils/
│   └── few_shot.py                 # Few-shot 유틸리티 (신규)
│
└── Node/MCQ/
    └── generate.py                 # MCQ 생성 노드 (Few-shot 사용)
```

## 🎯 Few-shot 작동 흐름

```
[1] few_shot_examples.json
      ↓ (로드)
[2] config.py → get_mcq_types()
      ↓ (State에 저장)
[3] MCQState["few_shot_examples"]
      ↓ (노드 실행)
[4] Node/MCQ/generate.py
      ↓ (프롬프트 구성)
[5] Utils.few_shot.build_few_shot_prompt()
      ↓ (LLM 호출)
[6] Vertex AI LLM (Few-shot 예시 참고)
      ↓
[7] 생성된 MCQ
```

## 📄 Few-shot JSON 파일 형식

### 기본 구조

```json
{
  "MCQ_GENERAL": [
    {
      "question": "질문 텍스트",
      "options": [
        "보기 1",
        "보기 2",
        "보기 3",
        "보기 4"
      ],
      "answer_index": 3,
      "explanation": "정답 해설"
    }
  ]
}
```

### 고급 형식 (보기별 해설)

```json
{
  "MCQ_GENERAL": [
    {
      "question": "질문 텍스트",
      "options": ["보기1", "보기2", "보기3", "보기4"],
      "answer_index": 2,
      "explanations": [
        "1번 보기가 틀린 이유",
        "2번 보기가 정답인 이유",
        "3번 보기가 틀린 이유",
        "4번 보기가 틀린 이유"
      ]
    }
  ]
}
```

## 🔧 설정 방법

### 1️⃣ JSON 파일 경로 설정

`.env` 파일에 추가:
```bash
# Few-shot 설정
MCQ_FEW_SHOT_JSON_PATH=Data/Dock_Exam_2025/few_shot_examples.json
MCQ_FEW_SHOT_MAX_EXAMPLES=3
MCQ_RANDOM_SAMPLE_MAX=1000
```

### 2️⃣ JSON 파일 생성

```python
from Utils.few_shot import create_few_shot_template

# 템플릿 파일 생성 (3개 예시)
create_few_shot_template(
    output_path="Data/Dock_Exam_2025/few_shot_examples.json",
    num_examples=3
)
```

### 3️⃣ JSON 파일 직접 작성

`Data/Dock_Exam_2025/` 폴더에 `few_shot_examples.json` 생성 후 예시 추가

## 📝 Few-shot 예시 작성 가이드

### ✅ 좋은 예시

```json
{
  "question": "심폐소생술 시 가슴압박의 적절한 속도는?",
  "options": [
    "분당 60-80회",
    "분당 80-100회",
    "분당 100-120회",
    "분당 120-140회"
  ],
  "answer_index": 3,
  "explanation": "심폐소생술 가이드라인에 따르면 가슴압박은 분당 100-120회의 속도로 시행해야 합니다. 너무 빠르거나 느리면 효과가 감소합니다."
}
```

**왜 좋은가?**
- ✅ 질문이 명확하고 구체적
- ✅ 보기가 서로 유사하지만 구분됨 (60-80, 80-100, 100-120, 120-140)
- ✅ 오답도 그럴듯함 (단순히 "전혀 관계없는 답" 아님)
- ✅ 해설이 상세하고 교육적

### ❌ 나쁜 예시

```json
{
  "question": "응급처치는?",
  "options": [
    "좋은 것",
    "나쁜 것",
    "응급처치",
    "모르겠음"
  ],
  "answer_index": 3,
  "explanation": "정답입니다."
}
```

**왜 나쁜가?**
- ❌ 질문이 모호함
- ❌ 보기가 너무 다름 (구분이 너무 쉬움)
- ❌ 해설이 부실함

## 🚀 사용 방법

### 기본 사용 (JSON 자동 로드)

```python
from Core.Generator_MCQ_LangGraph import Generator_MCQ_LangGraph

generator = Generator_MCQ_LangGraph(
    vector_store=vector_store,
    llm=llm
)

# Few-shot 예시가 자동으로 로드되어 사용됨
mcq = generator.generate_mcq(topics_hierarchical=topics)
```

### JSON 파일 직접 로드

```python
from Utils.few_shot import load_few_shot_examples_from_json

# 커스텀 JSON 파일 사용
examples = load_few_shot_examples_from_json("my_custom_examples.json")
print(f"로드된 예시: {len(examples['MCQ_GENERAL'])}개")
```

### 프롬프트 빌드 (수동)

```python
from Utils.few_shot import build_few_shot_prompt

template = "문제를 만들어주세요:\n{context}"
examples = [
    {"question": "...", "options": [...], "answer_index": 1, "explanation": "..."}
]

prompt = build_few_shot_prompt(
    template=template,
    examples=examples,
    max_examples=3,      # 최대 3개 예시 사용
    randomize=True       # 랜덤하게 선택
)
```

## 🔍 Few-shot 동작 방식

### 1️⃣ 자동 로드 (config.py)

```python
def get_mcq_types():
    # JSON에서 자동 로드
    few_shot_dict = load_few_shot_examples_from_json(
        "Data/Dock_Exam_2025/few_shot_examples.json"
    )
    few_shot_examples = few_shot_dict.get("MCQ_GENERAL", [])
    
    return {
        "MCQ_GENERAL": {
            "instruction": "...",
            "few_shot_examples": few_shot_examples  # ← State에 전달
        }
    }
```

### 2️⃣ State에 저장

```python
# Core/Generator_MCQ_LangGraph.py

mcq_type = self.mcq_types.get("MCQ_GENERAL", {})
few_shot_examples = mcq_type.get("few_shot_examples", [])

initial_state = create_initial_mcq_state(
    few_shot_examples=few_shot_examples  # ← State에 저장
)
```

### 3️⃣ 노드에서 사용

```python
# Node/MCQ/generate.py

few_shot_examples = state.get("few_shot_examples", [])
if few_shot_examples:
    human_template = build_few_shot_prompt(
        human_template, few_shot_examples
    )
```

### 4️⃣ 프롬프트에 추가

```python
# Utils/few_shot.py

def build_few_shot_prompt(template, examples, max_examples=3):
    # 랜덤하게 최대 3개 선택
    selected = random.sample(examples, min(3, len(examples)))
    
    # 텍스트 형식으로 포맷팅
    examples_text = "\n\n**Few-shot 예시 (참고용):**\n\n"
    for i, ex in enumerate(selected, 1):
        examples_text += f"예시 {i}:\n"
        examples_text += f"질문: {ex['question']}\n"
        # ... 보기, 정답, 해설 추가
    
    return template + "\n" + examples_text
```

## 📊 Few-shot 효과

| 항목 | Few-shot 없음 | Few-shot 있음 |
|------|--------------|--------------|
| **문제 품질** | 중간 | ✅ 높음 |
| **형식 일관성** | 낮음 | ✅ 높음 |
| **해설 품질** | 간단 | ✅ 상세 |
| **오답 품질** | 명확함 | ✅ 그럴듯함 |

## 🛠️ 유틸리티 함수

### `load_few_shot_examples_from_json()`
JSON 파일에서 예시 로드

### `build_few_shot_prompt()`
프롬프트에 Few-shot 예시 추가

### `format_single_example()`
단일 예시 포맷팅

### `validate_few_shot_example()`
예시 유효성 검증

### `filter_valid_examples()`
유효한 예시만 필터링

### `create_few_shot_template()`
JSON 템플릿 파일 생성

## 💡 팁

1. **예시 개수**: 3-5개가 적당 (너무 많으면 프롬프트가 길어짐)
2. **랜덤 선택**: 매번 다른 예시 조합으로 다양성 보장
3. **유효성 검증**: JSON에 잘못된 예시가 있으면 자동으로 필터링
4. **Fallback**: JSON 로드 실패 시 기본 예시 자동 사용
5. **동적 업데이트**: JSON 파일만 수정하면 재시작 시 자동 반영

## 🎓 Few-shot 예시 추가 방법

### 방법 1: JSON 파일 직접 편집

```json
{
  "MCQ_GENERAL": [
    {
      "question": "새로운 질문",
      "options": ["보기1", "보기2", "보기3", "보기4"],
      "answer_index": 2,
      "explanation": "상세한 해설"
    }
  ]
}
```

### 방법 2: 프로그래밍 방식

```python
import json

# 기존 JSON 로드
json_path = "Data/Dock_Exam_2025/few_shot_examples.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 새 예시 추가
data["MCQ_GENERAL"].append({
    "question": "새로운 질문",
    "options": ["보기1", "보기2", "보기3", "보기4"],
    "answer_index": 3,
    "explanation": "상세한 해설"
})

# 저장
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

## ⚙️ 환경 변수 설정

`.env` 파일에 추가:

```bash
# Few-shot 설정
MCQ_FEW_SHOT_JSON_PATH=Data/Dock_Exam_2025/few_shot_examples.json
MCQ_FEW_SHOT_MAX_EXAMPLES=3
```

---

Made with ❤️ using Few-shot Learning

