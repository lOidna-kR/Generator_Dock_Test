"""
MCQ 워크플로우 엣지 정의 (중첩 선택 지원)

MCQ 생성 워크플로우의 모든 노드 간 연결을 관리합니다.
"""

from typing import TYPE_CHECKING, Literal
from langgraph.graph import END, START
from State import State

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


# ==================== 조건 함수 ====================


def should_retry_after_validation(
    state: State
) -> Literal["retry_retrieve", "format_output", "end"]:
    """
    유효성 검증 후 재시도 전략 결정 (단순화 버전)
    
    재시도 전략:
    - 유효하면: format_output으로
    - 최대 재시도 미만: retrieve_documents로 재시도
    - 최대 재시도 초과: 종료
    
    Args:
        state: State
    
    Returns:
        "retry_retrieve": retrieve_documents로 재시도
        "format_output": 성공 (다음 노드로)
        "end": 최대 재시도 초과
    """
    if state["is_valid"]:
        return "format_output"
    
    if not state["should_retry"]:
        return "end"
    
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 6)
    
    # 재시도 전략
    if retry_count < max_retries:
        # retrieve로 재시도
        return "retry_retrieve"
    else:
        # 최대 재시도 초과: 종료
        return "end"


def should_retry_after_retrieve(
    state: State
) -> Literal["format_context", "retry"]:
    """
    문서 검색 후 재시도 여부 결정
    
    Args:
        state: State
    
    Returns:
        "format_context": 검색 성공
        "retry": 검색 실패, 재시도
    """
    # retry_count 확인 추가 (무한 루프 방지)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 6)
    
    # 재시도 횟수 초과 시 강제로 진행
    if retry_count >= max_retries:
        return "format_context"
    
    if state.get("error") and state.get("should_retry"):
        return "retry"
    
    return "format_context"


# ==================== 엣지 빌더 ====================


def build_mcq_workflow_edges(workflow: "StateGraph") -> None:
    """
    MCQ 워크플로우의 모든 엣지를 구성합니다. (간소화 버전)
    
    워크플로우 구조:
        START 
          ↓
        retrieve_documents (문서 검색, 랜덤 주제)
          ↓ [조건부]
        format_context (컨텍스트 포맷팅)
          ↓
        generate_mcq (MCQ 생성)
          ↓
        validate_mcq (유효성 검증)
          ↓ [조건부]
          - 유효 → format_output
          - 재시도 → retrieve_documents
          - 최대 재시도 초과 → END
          ↓
        format_output (출력 포맷팅)
          ↓
        END
    
    Args:
        workflow: StateGraph 객체
    
    Example:
        workflow = StateGraph(MCQState)
        workflow.add_node("retrieve_documents", retrieve_func)
        # ... 다른 노드들
        
        build_mcq_workflow_edges(workflow)  # 엣지 자동 구성
    """
    # 1. 시작 엣지 - 바로 retrieve_documents로
    workflow.add_edge(START, "retrieve_documents")
    
    # 2. 조건부 엣지: 문서 검색 후
    workflow.add_conditional_edges(
        "retrieve_documents",
        should_retry_after_retrieve,
        {
            "format_context": "format_context",
            "retry": "retrieve_documents",  # 실패 시 재시도
        }
    )
    
    # 3. MCQ 생성 흐름 (선형)
    workflow.add_edge("format_context", "generate_mcq")
    workflow.add_edge("generate_mcq", "validate_mcq")
    
    # 4. 조건부 엣지: 유효성 검증 후
    workflow.add_conditional_edges(
        "validate_mcq",
        should_retry_after_validation,
        {
            "format_output": "format_output",        # 유효 → 다음
            "retry_retrieve": "retrieve_documents",  # 재시도 → retrieve
            "end": END,                              # 최대 재시도 초과 → 종료
        }
    )
    
    # 5. 종료 엣지
    workflow.add_edge("format_output", END)


# ==================== 헬퍼 함수 ====================


def get_mcq_workflow_description() -> str:
    """
    MCQ 워크플로우 구조를 텍스트로 반환 (간소화 버전)
    
    디버깅이나 문서화에 유용합니다.
    
    Returns:
        워크플로우 구조 설명 문자열
    """
    return """
MCQ 생성 워크플로우 구조 (간소화 버전 - 랜덤 주제):

START
  ↓
retrieve_documents (랜덤 주제 선택 및 문서 검색)
  - 전체 교재 구조에서 랜덤 Part 선택
  - 랜덤 Chapter 선택
  - 선택된 주제로 벡터 검색
  ↓ [조건부]
  - 성공 → format_context
  - 실패 → retrieve_documents (재시도)
  ↓
format_context (컨텍스트 포맷팅)
  - 문서를 LLM용 형식으로 변환
  ↓
generate_mcq (MCQ 생성)
  - Few-shot 프롬프트 구성
  - LLM 호출
  - JSON 파싱
  ↓
validate_mcq (유효성 검증)
  - 5가지 검증 항목 확인
  ↓ [조건부]
  - 유효 → format_output
  - 재시도 가능 → retrieve_documents (다른 랜덤 주제로)
  - 최대 재시도 초과 → END (종료)
  ↓
format_output (출력 포맷팅)
  - 메타데이터 추가
  ↓
END

특징:
- 랜덤 주제 선택: 전체 범위에서 자동 선택
- 재시도 시마다 새로운 랜덤 주제 선택
- 최대 재시도: 설정 가능 (기본 6회)
- Few-shot Learning: JSON 기반 예시 로드
"""

