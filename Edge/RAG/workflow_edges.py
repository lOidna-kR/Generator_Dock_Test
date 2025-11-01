"""
워크플로우 엣지 정의

모든 노드 간 연결을 중앙에서 관리합니다.
- 단순 엣지 (선형 연결)
- 조건부 엣지 (분기 로직)

설계 철학:
- 엣지는 워크플로우의 제어 흐름을 명확하게 표현
- 확장 가능한 구조로 조건부 로직 추가 가능
- Generator.py의 복잡도를 낮추고 엣지 로직 중앙 관리
"""

from typing import TYPE_CHECKING, Literal
from langgraph.graph import END, START

from State import State

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


# ==================== 조건 함수 ====================


def should_retry(state: "State") -> Literal["retry", "continue"]:
    """
    재시도 조건 체크
    
    에러가 발생했고 재시도 횟수가 남아있으면 재시도합니다.
    
    Args:
        state: 현재 State
    
    Returns:
        "retry": 재시도 필요 (retrieve_documents부터 다시 시작)
        "continue": 계속 진행 (다음 노드로)
    
    사용 예시:
        workflow.add_conditional_edges(
            "generate_answer",
            should_retry,
            {"retry": "retrieve_documents", "continue": "format_output"}
        )
    """
    has_error = state.get("error") is not None
    should_retry_flag = state.get("should_retry", False)
    retry_count = state.get("retry_count", 0)
    max_retries = 3
    
    if has_error and should_retry_flag and retry_count < max_retries:
        return "retry"
    return "continue"


def should_use_cache(state: "State") -> Literal["cached", "retrieve"]:
    """
    캐시 사용 여부 결정
    
    이전에 동일한 질문을 처리한 적이 있으면 캐시를 사용합니다.
    
    Args:
        state: 현재 State
    
    Returns:
        "cached": 캐시된 결과 사용
        "retrieve": 새로 검색
    
    Note:
        향후 캐시 기능 구현 시 활성화
    """
    # 캐시 기능은 향후 구현 예정
    # 현재는 항상 새로 검색
    return "retrieve"


# ==================== 엣지 빌더 ====================


def route_pipeline(state: "State") -> Literal["rag", "chat"]:
    """파이프라인 라우팅 결과를 반환합니다."""

    return "rag" if state.get("pipeline", "rag") == "rag" else "chat"


def build_workflow_edges(workflow: "StateGraph") -> None:
    """
    워크플로우의 모든 엣지를 구성합니다.
    
    현재 구조 (선형):
        START -> route_question -> (조건부) retrieve_documents -> format_context 
              -> generate_answer -> format_output -> END
    
    향후 확장 가능:
        - 재시도 로직 (조건부 엣지)
          generate_answer -> [should_retry] -> retrieve_documents or format_output
        
        - 캐시 활용 (조건부 엣지)
          START -> [should_use_cache] -> use_cache or retrieve_documents
        
        - 병렬 검색 (멀티 소스)
          START -> [retrieve_source1, retrieve_source2] -> merge -> format_context
        
        - 답변 품질 체크 (조건부 엣지)
          generate_answer -> [check_quality] -> improve or format_output
    
    Args:
        workflow: StateGraph 객체
    
    Example:
        workflow = StateGraph(State)
        workflow.add_node("retrieve_documents", retrieve_func)
        workflow.add_node("format_context", format_func)
        # ... 다른 노드들
        
        build_workflow_edges(workflow)  # 엣지 자동 구성
    """
    # 1. 시작 엣지
    workflow.add_edge(START, "route_question")

    workflow.add_conditional_edges(
        "route_question",
        route_pipeline,
        {
            "rag": "retrieve_documents",
            "chat": "generate_answer",
        },
    )

    workflow.add_edge("retrieve_documents", "format_context")
    workflow.add_edge("format_context", "generate_answer")
    workflow.add_edge("generate_answer", "format_output")
    workflow.add_edge("format_output", END)
    
    # 3. 조건부 엣지 (향후 활성화)
    # 재시도 로직이 필요한 경우 아래 주석 해제
    # workflow.add_conditional_edges(
    #     "generate_answer",
    #     should_retry,
    #     {
    #         "retry": "retrieve_documents",
    #         "continue": "format_output",
    #     }
    # )


# ==================== 엣지 설정 ====================


class WorkflowEdgeConfig:
    """
    워크플로우 엣지 설정
    
    엣지 동작을 제어하는 플래그와 설정값들을 관리합니다.
    향후 기능 추가 시 여기서 활성화/비활성화 가능.
    """
    
    # 재시도 설정
    ENABLE_RETRY = False
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 1.0
    
    # 캐시 설정
    ENABLE_CACHE = False
    CACHE_TTL_SECONDS = 3600  # 1시간
    
    # 병렬 처리 설정
    ENABLE_PARALLEL_RETRIEVAL = False
    PARALLEL_SOURCE_COUNT = 2
    
    # 품질 체크 설정
    ENABLE_QUALITY_CHECK = False
    MIN_QUALITY_SCORE = 0.7


# ==================== 헬퍼 함수 ====================


def get_workflow_description() -> str:
    """
    현재 워크플로우 구조를 텍스트로 반환
    
    디버깅이나 문서화에 유용합니다.
    
    Returns:
        워크플로우 구조 설명 문자열
    """
    return """
워크플로우 구조:

START
  ↓
route_question (질문 라우팅)
  ↓
조건부 분기
  ↙︎           ↘︎
retrieve_documents   generate_answer (일반 대화)
  ↓
format_context (검색 결과 포맷팅)
  ↓
generate_answer (LLM 답변 생성)
  ↓
format_output (최종 출력 포맷팅)
  ↓
END

각 노드는 자체적으로 에러를 처리하며,
route_question 이후 파이프라인에 따라 RAG 또는 일반 대화 경로로 분기합니다.
"""

