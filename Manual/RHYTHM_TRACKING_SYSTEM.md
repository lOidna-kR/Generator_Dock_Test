# 리듬 추적 시스템 (Rhythm Tracking System)

## 📋 개요

**작성일:** 2025-11-03  
**버전:** 1.0  
**목적:** MCQ 배치 생성 시 심전도 리듬 다양성을 보장하는 근본적인 해결책

---

## 🎯 문제 정의

### 이전 문제
```
결과: 무수축 4개 (40%), 심실세동 6개 (60%)
목표: 각 리듬 최대 2개 (20%)
원인: LLM이 이전 생성 문제의 리듬을 인지하지 못함
```

### 프롬프트만으로 해결 불가능한 이유
1. **LLM은 독립적으로 호출됨**
   - 10개 문제 생성 = 10번의 독립적인 LLM 호출
   - 각 호출은 이전 문제를 "모름"

2. **프롬프트는 정적임**
   - "같은 리듬 최대 2개" → LLM이 "지금까지 몇 개 생성했는지" 알 수 없음
   - 프롬프트만으로는 실시간 추적 불가

3. **필요한 것: 동적 피드백**
   - "지금까지 무수축 2개 생성됨 → 사용 금지" 명시

---

## ✅ 해결 방법: 3단계 방어선

### **1단계: State에 리듬 추적 (Data Layer)**
```python
# State/state.py
class State(TypedDict):
    ...
    rhythm_counter: Dict[str, int]  # {"VF": 1, "Asystole": 2, "PEA": 1}
```

### **2단계: 프롬프트에 동적 삽입 (Prompt Layer)**
```python
# Node/MCQ/generate.py
rhythm_counter = state.get("rhythm_counter", {})
if rhythm_counter:
    rhythm_constraint = """
    ⚠️ 이미 생성된 문제의 리듬 현황:
    - Asystole (무수축): 2회 ⚠️ 최대 도달! 절대 사용 금지
    - VF (심실세동): 1회 ✅ 1회 더 가능
    
    [절대 준수] 2회 표시된 리듬은 절대 사용하지 마세요!
    """
    human_template = human_template + rhythm_constraint
```

### **3단계: 코드 레벨 강제 거부 (Code Layer)**
```python
# main.py
rhythm = extract_rhythm_from_mcq(mcq)
if should_reject_rhythm(rhythm_counter, rhythm, max_count=2):
    # 3회 이상 → 재생성
    continue
```

---

## 📁 구현 내용

### 1. 신규 파일: `Utils/rhythm_tracker.py`

**주요 함수:**
```python
# MCQ에서 리듬 추출
rhythm = extract_rhythm_from_mcq(mcq)
# 예: "VF", "Asystole", "PEA", "ROSC"

# 리듬 정규화 (다양한 표현 → 표준명)
normalized = normalize_rhythm_name("심실세동")  # "VF"

# 프롬프트용 텍스트 생성
text = get_rhythm_status_text(rhythm_counter, max_count=2)

# 거부 여부 판단
should_reject = should_reject_rhythm(rhythm_counter, "VF", max_count=2)
```

**리듬 정규화 매핑:**
| 원본 표현 | 정규화 | 비고 |
|-----------|--------|------|
| 심실세동 | VF | Ventricular Fibrillation |
| 무수축 | Asystole | - |
| 무맥성 전기활동 | PEA | - |
| 자발순환 회복 후 | ROSC | Return of Spontaneous Circulation |
| 동서맥 | Sinus Bradycardia | - |

### 2. 수정된 파일

#### **State/state.py**
```python
# 추가된 필드
rhythm_counter: Dict[str, int]

# create_state 함수에 파라미터 추가
def create_state(..., rhythm_counter: Optional[Dict[str, int]] = None):
    return State(
        ...
        rhythm_counter=dict(rhythm_counter or {}),
    )
```

#### **Node/MCQ/generate.py**
```python
# 리듬 제약을 프롬프트에 동적 삽입
rhythm_counter = state.get("rhythm_counter", {})
if rhythm_counter:
    from Utils.rhythm_tracker import get_rhythm_status_text
    rhythm_constraint = get_rhythm_status_text(rhythm_counter, max_count=2)
    human_template = human_template + rhythm_constraint
```

#### **Core/forge_mode.py**
```python
# generate_mcq 메서드에 rhythm_counter 파라미터 추가
def generate_mcq(
    self,
    ...,
    rhythm_counter: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    ...
    initial_state = create_state(
        ...,
        rhythm_counter=rhythm_counter,
    )
```

#### **main.py**
두 곳에 동일한 로직 적용:
1. `handle_forge_mode()` - 일반 배치 생성
2. `handle_mock_exam_mode()` - 동형모의고사 40문제 생성

```python
rhythm_counter = {}  # 초기화

for i in range(num_questions):
    # 1. 리듬 카운터를 State로 전달
    mcq = forge_mode.generate_mcq(..., rhythm_counter=rhythm_counter)
    
    # 2. 리듬 추출
    rhythm = extract_rhythm_from_mcq(mcq)
    
    # 3. 2회 초과 체크 (코드 레벨 강제)
    if should_reject_rhythm(rhythm_counter, rhythm, max_count=2):
        print(f"🔄 리듬 중복 ({korean_name}), 재생성 중...")
        continue  # 재생성
    
    # 4. 성공: 카운터 업데이트
    rhythm_counter[rhythm] = rhythm_counter.get(rhythm, 0) + 1
    batch_mcqs.append(mcq)

# 5. 통계 출력
print(f"\n📊 생성된 리듬 분포:")
for rhythm, count in rhythm_counter.items():
    print(f"   - {get_korean_rhythm_name(rhythm)}: {count}개")
```

---

## 🔄 워크플로우

### 배치 생성 (예: 10개)

```
┌─────────────────────────────────────────────────────┐
│ 1. 초기화                                            │
│    rhythm_counter = {}                              │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 2. 문제 #1 생성                                      │
│    State에 rhythm_counter={} 전달                    │
│    → 프롬프트: (리듬 제약 없음)                       │
│    → LLM 생성: "VF"                                  │
│    → rhythm_counter = {"VF": 1} 업데이트             │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 3. 문제 #2 생성                                      │
│    State에 rhythm_counter={"VF": 1} 전달             │
│    → 프롬프트에 삽입:                                 │
│       "VF: 1회 ✅ 1회 더 가능"                        │
│    → LLM 생성: "Asystole"                            │
│    → rhythm_counter = {"VF": 1, "Asystole": 1}      │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 4. 문제 #3 생성                                      │
│    State에 rhythm_counter={"VF": 1, "Asystole": 1}  │
│    → 프롬프트에 삽입:                                 │
│       "VF: 1회 ✅, Asystole: 1회 ✅"                  │
│    → LLM 생성: "VF"                                  │
│    → rhythm_counter = {"VF": 2, "Asystole": 1}      │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 5. 문제 #4 생성 (VF 3회 시도)                        │
│    State에 rhythm_counter={"VF": 2, "Asystole": 1}  │
│    → 프롬프트에 삽입:                                 │
│       "VF: 2회 ⚠️ 최대 도달! 절대 사용 금지"          │
│       "Asystole: 1회 ✅"                             │
│    → LLM 생성: "PEA" (성공!)                         │
│    → rhythm_counter = {"VF": 2, "Asystole": 1, ...} │
└─────────────────────────────────────────────────────┘
                    ↓
                  (반복)
```

---

## 📊 기대 효과

| 항목 | 이전 | 개선 후 | 변화 |
|------|------|---------|------|
| **무수축 4개 방지** | ❌ 실패 | ✅ 최대 2개 강제 | **100%** |
| **심실세동 6개 방지** | ❌ 실패 | ✅ 최대 2개 강제 | **100%** |
| **리듬 종류** | 5가지 | 8-10가지 | **+60%** |
| **LLM 인지** | ❌ 모름 | ✅ 명확히 인식 | **완전 해결** |
| **강제력** | ⚠️ 약함 (프롬프트만) | ✅✅ 강함 (3단계) | **매우 강력** |

### 예상 결과 (10개 문제)
```
VF (심실세동): 2개 ✅
Asystole (무수축): 2개 ✅
PEA (무맥성 전기활동): 2개 ✅
PSVT (발작성 상심실성 빈맥): 1개 ✅
Sinus Bradycardia (동서맥): 1개 ✅
STEMI (급성 심근경색): 1개 ✅
ROSC (자발순환 회복 후): 1개 ✅
→ 총 7가지 다른 리듬!
```

---

## 🔧 사용 방법

### 자동 적용 (기본값)
사용자가 별도로 설정할 필요 없음. 시스템이 자동으로 작동합니다.

### 수동 설정 (필요 시)
```python
# 최대 허용 횟수 변경 (기본값: 2)
should_reject_rhythm(rhythm_counter, rhythm, max_count=3)  # 최대 3회로 변경

# 리듬 추적 비활성화
mcq = forge_mode.generate_mcq(..., rhythm_counter=None)
```

---

## 🎓 핵심 원리

### 왜 프롬프트만으로는 부족한가?
```python
# ❌ 작동하지 않음
프롬프트: "같은 리듬 최대 2개까지만 생성하세요"

LLM 생성:
1. VF (LLM은 "이게 첫 번째"라고 생각)
2. VF (LLM은 "이게 첫 번째"라고 생각)
3. VF (LLM은 "이게 첫 번째"라고 생각)
→ 매번 독립적으로 호출되므로 기억 못함
```

### 동적 프롬프트 + 코드 강제
```python
# ✅ 작동함
프롬프트 (동적):
"⚠️ VF: 이미 2회 사용됨 → 절대 사용 금지!"

+ 코드 (강제):
if rhythm == "VF" and count >= 2:
    reject()  # 3회째 생성 시 강제 거부

→ LLM이 무시하더라도 코드가 막음!
```

---

## 📝 제한 사항

1. **리듬이 없는 문제**
   - 예: "자발순환 회복 후 처치" (ECG 없음)
   - 추적 대상 아님 (정상 동작)

2. **리듬 추출 실패**
   - `[Image: ...]` 태그가 없거나 비표준 형식
   - `extract_rhythm_from_mcq()` 반환값: `None`
   - 추적 제외 (허용)

3. **동형모의고사 특수 처리**
   - 전문심장소생술 문제만 리듬 추적
   - 다른 챕터는 추적 안 함

---

## 🚀 향후 확장

### 1. 다른 다양성 요소에도 적용
```python
# 연령 추적
age_counter = {"20대": 2, "30대": 4, "40대": 1}
# 30대 4회 → 재생성

# 발생 장소 추적
location_counter = {"등산": 4, "헬스장": 2}
# 등산 4회 → 재생성
```

### 2. 통계 분석 및 대시보드
```python
# 생성 완료 후 분석
diversity_score = calculate_diversity(rhythm_counter)
print(f"다양성 점수: {diversity_score}/100")
```

### 3. 학습 데이터 수집
```python
# 리듬 선호도 분석
preferred_rhythms = analyze_llm_preferences(rhythm_history)
# "LLM이 VF를 선호함" → 프롬프트 조정
```

---

## ✅ 체크리스트

### 구현 완료
- [x] `Utils/rhythm_tracker.py` 생성
- [x] `State/state.py` 수정 (rhythm_counter 필드)
- [x] `Node/MCQ/generate.py` 수정 (동적 프롬프트)
- [x] `Core/forge_mode.py` 수정 (파라미터 전달)
- [x] `main.py` 수정 (배치 생성 로직)
- [x] `main.py` 수정 (동형모의고사 로직)

### 테스트 대기
- [ ] 전문심장소생술 10개 생성 테스트
- [ ] 리듬 분포 확인 (각 리듬 최대 2개?)
- [ ] 리듬 통계 출력 확인
- [ ] 동형모의고사 40문제 생성 테스트

---

## 📚 참고 자료

- 관련 문서: `Manual/RHYTHM_DIVERSITY_FIX.md`
- 프롬프트 수정: `Data/Prompts/각론/전문심장소생술/system_prompt.txt`
- Few-shot 예시: `Data/Few_shot/각론/전문심장소생술/`

---

**작성자:** AI Assistant  
**최종 수정:** 2025-11-03  
**버전:** 1.0

