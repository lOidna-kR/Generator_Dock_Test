# Generator 프로젝트 문서

이 폴더는 Generator 프로젝트의 설계, 사용법, MCQ 생성 가이드를 담고 있습니다.

## 📚 문서 목록

### 🎯 시작 가이드

#### 1. PROJECT_README.md
**프로젝트 메인 문서**

Generator 프로젝트의 전체 개요와 빠른 시작 가이드입니다.

**내용:**
- 프로젝트 소개
- 주요 기능
- 빠른 시작 가이드
- 워크플로우 구조

---

### 📖 RAG 시스템 문서

#### 2. FINAL_PROJECT_STRUCTURE.md
**최종 프로젝트 구조 완전 가이드**

RAG 시스템의 전체 구조와 모든 리팩토링 내용이 정리된 **메인 문서**입니다.

**내용:**
- 최종 디렉토리 구조
- 모든 요구사항 적용 내역
- 각 모듈별 역할 및 책임
- 사용 방법 및 확장 가이드

---

#### 3. CONVERSATION_EXAMPLE.md
**대화형 RAG 시스템 사용 가이드**

`add_messages`를 활용한 대화 이력 관리 방법을 설명합니다.

**내용:**
- State에 messages 필드 활용법
- Multi-turn 대화 구현 방법
- Helper 함수 사용 예제
- 노드에서 대화 이력 활용법

**읽어야 하는 경우:**
- 대화형 챗봇으로 확장하고 싶을 때
- messages 필드를 활용하고 싶을 때
- 대화 맥락을 고려한 답변을 구현하고 싶을 때

---

### 🎓 MCQ 생성 시스템 문서

#### 4. MCQ_LANGGRAPH_README.md ⭐
**MCQ Generator 완전 가이드**

LangGraph 기반 MCQ 자동 생성 시스템의 전체 설명서입니다.

**내용:**
- MCQ Generator 개요 및 특징
- 파일 구조 및 워크플로우
- 중첩 선택 방식 설명
- 사용 예시
- 기존 Generator_MCQ와 비교

**읽어야 하는 경우:**
- MCQ 생성 시스템을 처음 사용할 때
- 중첩 선택 구조를 이해하고 싶을 때
- LangGraph 방식의 MCQ 생성을 배우고 싶을 때

---

#### 5. FEW_SHOT_GUIDE.md
**Few-shot Learning 완전 가이드**

Few-shot 예시 관리 및 프롬프트 통합 시스템 설명서입니다.

**내용:**
- Few-shot JSON 파일 형식
- 자동 로드 시스템
- 프롬프트 빌드 과정
- 예시 작성 가이드
- 유틸리티 함수 설명

**읽어야 하는 경우:**
- Few-shot 예시를 추가/수정하고 싶을 때
- MCQ 품질을 향상시키고 싶을 때
- JSON 파일 관리 방법을 알고 싶을 때

---

#### 6. EXAMPLE_MCQ_LANGGRAPH.md
**MCQ Generator 사용 예시**

다양한 MCQ 생성 시나리오의 실제 코드 예시입니다.

**내용:**
- 기본 사용법
- 중첩 선택 예시
- 배치 생성
- 통계 및 히스토리
- 와일드카드 사용

**읽어야 하는 경우:**
- MCQ 생성 코드 예시를 보고 싶을 때
- 다양한 선택 전략을 알고 싶을 때
- 실전 활용법을 배우고 싶을 때

---

#### 7. HYBRID_RETRY_STRATEGY.md
**하이브리드 재시도 전략 가이드**

MCQ 생성 실패 시 지능형 재시도 시스템 설명서입니다.

**내용:**
- 재시도 전략 개요 (1-5회: retrieve, 6회: select_part)
- 재시도 흐름 및 시뮬레이션
- 왜 하이브리드 방식인가?
- 설정 방법

**읽어야 하는 경우:**
- 재시도 로직을 이해하고 싶을 때
- max_retries 값을 조정하고 싶을 때
- 검증 실패 처리를 알고 싶을 때

---

#### 8. PROJECT_STRUCTURE.md
**프로젝트 구조 요약**

전체 프로젝트의 파일 구조와 역할을 요약한 문서입니다.

**내용:**
- 전체 디렉토리 구조
- 파일별 역할 설명
- 사용 방법
- 통계

---

### 🔧 리팩토링 가이드

#### 9. REFACTORING_NODE_STRUCTURE.md
**Node 모듈 리팩토링 가이드**

formatting.py를 제거하고 기능별로 병합한 과정을 설명합니다.

**내용:**
- formatting.py 제거 이유
- retrieval.py, generation.py로 병합 과정
- 기능별 그룹화의 장점
- Before/After 비교

**읽어야 하는 경우:**
- Node 모듈 구조를 이해하고 싶을 때
- 왜 포맷팅 노드가 분산되어 있는지 궁금할 때
- 새로운 노드 추가 시 어디에 배치할지 결정할 때

---

#### 10. REMOVE_ERROR_HANDLER.md
**Error Handler 노드 제거 가이드**

복잡한 에러 처리 구조를 단순화한 과정을 설명합니다.

**내용:**
- error_handler.py 제거 이유
- 각 노드의 자체 에러 처리 방식
- 조건부 엣지 제거 과정
- 선형 워크플로우의 장점

**읽어야 하는 경우:**
- 에러 처리 방식을 이해하고 싶을 때
- 왜 조건부 엣지가 없는지 궁금할 때
- 새로운 에러 처리 로직 추가 시 참고

---

#### 11. EDGE_MODULE_RESTRUCTURE.md
**Edge 모듈 재구성 가이드**

엣지 로직을 중앙에서 관리하도록 재구성한 과정을 설명합니다.

**내용:**
- Edge 모듈의 역할
- build_workflow_edges() 함수 설명
- 조건부 엣지 확장 방법
- WorkflowEdgeConfig 사용법

**읽어야 하는 경우:**
- 워크플로우 엣지를 수정하고 싶을 때
- 조건부 분기를 추가하고 싶을 때
- 재시도/캐싱 등 확장 기능을 구현하고 싶을 때

---

## 📖 읽기 순서 (권장)

### 🎯 처음 프로젝트를 접하는 경우
1. **PROJECT_README.md** (프로젝트 소개)
2. **FINAL_PROJECT_STRUCTURE.md** ⭐ (전체 구조 파악)
3. **PROJECT_STRUCTURE.md** (구조 요약)

### 🎓 MCQ 시스템을 사용하는 경우
1. **MCQ_LANGGRAPH_README.md** ⭐ (MCQ 시스템 전체)
2. **FEW_SHOT_GUIDE.md** (Few-shot 설정)
3. **HYBRID_RETRY_STRATEGY.md** (재시도 전략)
4. **EXAMPLE_MCQ_LANGGRAPH.md** (코드 예시)

### 🔧 특정 기능을 추가하고 싶은 경우
- MCQ 생성 → **MCQ_LANGGRAPH_README.md**
- Few-shot 예시 추가 → **FEW_SHOT_GUIDE.md**
- 대화형 기능 → **CONVERSATION_EXAMPLE.md**
- 에러 처리 수정 → **REMOVE_ERROR_HANDLER.md**
- 워크플로우 수정 → **EDGE_MODULE_RESTRUCTURE.md**

### 📋 유지보수 시
- **INDEX.md** (이 파일)에서 관련 문서 찾기
- 해당 문서의 가이드 참고

---

## 🎯 문서 작성 배경

이 문서들은 프로젝트 리팩토링 과정에서 작성되었습니다:

1. **State 타입 정확성 개선**
   - 실제 사용과 일치하도록 수정
   - messages 필드 추가 (대화형 확장 대비)

2. **Node 모듈 구조 개선**
   - formatting.py 제거 및 기능별 병합
   - 높은 응집도, 낮은 결합도 달성

3. **에러 처리 단순화**
   - error_handler.py 제거
   - 각 노드의 자체 완결성 강화

4. **Edge 모듈 중앙화**
   - 엣지 로직 중앙 관리
   - 향후 조건부 확장 준비

---

## 🔗 관련 코드

각 문서에서 설명하는 실제 코드 위치:

| 문서 | 관련 코드 |
|------|----------|
| FINAL_PROJECT_STRUCTURE.md | 전체 프로젝트 |
| CONVERSATION_EXAMPLE.md | State/state.py, Node/generation.py |
| REFACTORING_NODE_STRUCTURE.md | Node/retrieval.py, Node/generation.py |
| REMOVE_ERROR_HANDLER.md | Core/Generator.py, Node/* |
| EDGE_MODULE_RESTRUCTURE.md | Edge/workflow_edges.py, Core/Generator.py |

---

## 📝 문서 업데이트 정책

이 문서들은 프로젝트의 설계 결정과 구조를 기록한 것입니다.

- 코드 변경 시 관련 문서도 업데이트하세요
- 새로운 기능 추가 시 문서에 예제 추가하세요
- 설계 변경 시 해당 가이드 문서 수정하세요

---

**작성일: 2025-10-18**
**프로젝트: LangGraph Generator**

