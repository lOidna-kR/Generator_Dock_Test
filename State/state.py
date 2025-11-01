"""
통합 State 정의 (Ask + Forge 모드)

전역으로 관리되는 통합 State로 모든 모드에서 공유됩니다.

특징:
- Ask Mode와 Forge Mode 필드 통합
- 대화 히스토리 자동 관리
- 세션 정보 포함
- 모드 간 데이터 공유 용이
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict, Literal
from datetime import datetime
import operator

from langchain_core.documents import Document
from langgraph.graph.message import add_messages


class State(TypedDict):
    """
    통합 State (Ask Mode + Forge Mode)
    
    전역으로 관리되며 모든 모드에서 공유하는 상태입니다.
    
    구조:
        - 세션 관리: session_id, execution_mode, conversation_history
        - 공통 필드: error, should_retry, messages
        - Ask Mode 필드: question, context, answer 등
        - Forge Mode 필드: user_topic, generated_mcq 등
    
    사용 예시:
        >>> global_state = create_unified_state()
        >>> global_state["execution_mode"] = "ask"
        >>> rag_generator.process(question, state=global_state)
    """
    
    # ===== 세션 관리 =====
    session_id: str  # 세션 고유 ID
    execution_mode: Literal["ask", "forge"]  # 현재 실행 모드
    pipeline: Literal["rag", "chat"]  # Ask 모드 세부 파이프라인
    conversation_history: Annotated[List[Dict[str, Any]], operator.add]  # 전체 대화 히스토리
    
    # ===== 공통 필드 =====
    error: Optional[str]  # 에러 메시지
    should_retry: bool  # 재시도 여부
    messages: Annotated[list, add_messages]  # LangGraph 메시지 히스토리
    
    # ===== Ask Mode 필드 (RAG 질의응답) =====
    question: Optional[str]  # 현재 질문
    context: Annotated[List[Document], operator.add]  # 검색된 문서
    formatted_context: Optional[str]  # LLM용 포맷팅된 컨텍스트
    answer: Optional[str]  # 생성된 답변
    num_sources: int  # 출처 문서 수
    source_documents: Annotated[List[Dict[str, Any]], operator.add]  # 출처 메타데이터
    
    # ===== Forge Mode 필드 (MCQ 생성) =====
    # 입력 파라미터
    user_topic: Optional[str]  # 사용자 입력 주제
    topics_hierarchical: Optional[Dict[str, List[str]]]  # 교재 구조
    topics_nested: Optional[Dict[str, Dict[str, Any]]]  # 중첩 선택 구조
    part_weights: Optional[Dict[str, float]]  # Part별 가중치
    
    # 선택 결과
    selected_part: Optional[str]  # 선택된 Part
    selected_chapter: Optional[str]  # 선택된 Chapter
    selected_topic_query: Optional[str]  # 검색 쿼리
    available_chapters: List[str]  # 사용 가능한 Chapter 리스트
    recent_chapters: List[str]  # 최근 선택된 Chapter (중복 방지)

    # 라우팅 메타데이터
    routing_reason: Optional[str]  # 파이프라인 결정 사유 (디버깅용)
    
    # 문서 검색
    retrieved_documents: List[Document]  # 검색된 문서 (MCQ용)
    num_documents: int  # 문서 수 (MCQ용)
    recent_document_ids: List[str]  # 최근 사용된 문서 ID (문서 다양성 보장용, 최대 20개)
    
    # MCQ 생성
    instruction: str  # MCQ 생성 지침
    few_shot_examples: List[Dict[str, Any]]  # Few-shot 예시
    category_examples: Dict[str, List[Dict[str, Any]]]  # 카테고리별 예시
    category_weights: Dict[str, float]  # 카테고리별 가중치
    max_few_shot_examples: int  # Few-shot 예시 최대 개수
    recent_few_shot_indices: List[int]  # 최근 사용된 Few-shot 예시 인덱스 (다양성 보장용, 최대 10개)
    generated_mcq: Optional[Dict[str, Any]]  # 생성된 MCQ
    
    # 검증
    is_valid: bool  # 유효성 검증 결과
    validation_errors: List[str]  # 검증 오류 목록
    
    # 재시도 로직
    retry_count: int  # 현재 재시도 횟수
    max_retries: int  # 최대 재시도 횟수
    
    # 출력
    final_mcq: Optional[Dict[str, Any]]  # 최종 MCQ (메타데이터 포함)


# ==================== Helper 함수 ====================


def create_state(
    session_id: str = None,
    execution_mode: Literal["ask", "forge"] = "ask",
    # MCQ 생성용 파라미터들
    user_topic: Optional[str] = None,
    topics_hierarchical: Optional[Dict[str, List[str]]] = None,
    topics_nested: Optional[Dict[str, Dict[str, Any]]] = None,
    instruction: str = "",
    few_shot_examples: Optional[List[Dict[str, Any]]] = None,
    category_examples: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    category_weights: Optional[Dict[str, float]] = None,
    max_few_shot_examples: int = 5,
    max_retries: int = 6,
    recent_chapters: Optional[List[str]] = None,
) -> State:
    """
    통합 State 초기화 함수
    
    Args:
        session_id: 세션 ID (None이면 자동 생성)
        execution_mode: 실행 모드 ("ask" 또는 "forge")
        user_topic: MCQ 사용자 주제
        topics_hierarchical: MCQ 교재 구조
        topics_nested: MCQ 중첩 선택 구조
        instruction: MCQ 생성 지침
        few_shot_examples: MCQ Few-shot 예시
        category_examples: MCQ 카테고리별 예시
        category_weights: MCQ 카테고리별 가중치
        max_few_shot_examples: MCQ Few-shot 최대 개수
        max_retries: MCQ 최대 재시도 횟수
        recent_chapters: MCQ 최근 선택 Chapter
    
    Returns:
        초기화된 UnifiedState
    
    Example:
        >>> # 기본 사용 (main.py)
        >>> state = create_unified_state()
        
        >>> # MCQ 워크플로우용
        >>> state = create_unified_state(
        ...     execution_mode="forge",
        ...     topics_hierarchical=structure,
        ...     instruction="...",
        ...     max_retries=6
        ... )
    """
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return State(
        # 세션 관리
        session_id=session_id,
        execution_mode=execution_mode,
        pipeline="rag",
        conversation_history=[],
        
        # 공통
        error=None,
        should_retry=False,
        messages=[],
        
        # Ask Mode
        question=None,
        context=[],
        formatted_context=None,
        answer=None,
        num_sources=0,
        source_documents=[],
        
        # Forge Mode - 입력
        user_topic=user_topic,
        topics_hierarchical=topics_hierarchical,
        topics_nested=topics_nested,
        part_weights=None,
        
        # Forge Mode - 선택
        selected_part=None,
        selected_chapter=None,
        selected_topic_query=None,
        available_chapters=[],
        recent_chapters=recent_chapters or [],
        
        routing_reason=None,

        # Forge Mode - 문서
        retrieved_documents=[],
        num_documents=0,
        recent_document_ids=[],  # 최근 사용된 문서 ID (문서 다양성 보장용)
        
        # Forge Mode - 생성
        instruction=instruction,
        few_shot_examples=few_shot_examples or [],
        category_examples=category_examples or {},
        category_weights=category_weights or {},
        max_few_shot_examples=max_few_shot_examples,
        recent_few_shot_indices=[],  # 최근 사용된 Few-shot 예시 인덱스 (다양성 보장용)
        generated_mcq=None,
        
        # Forge Mode - 검증
        is_valid=False,
        validation_errors=[],
        
        # Forge Mode - 재시도
        retry_count=0,
        max_retries=max_retries,
        
        # Forge Mode - 출력
        final_mcq=None,
    )


def reset_ask_fields(state: State) -> None:
    """
    Ask Mode 필드 초기화 (다음 질문 준비)
    
    Args:
        state: State (in-place 수정)
    """
    state["question"] = None
    state["context"] = []
    state["formatted_context"] = None
    state["answer"] = None
    state["num_sources"] = 0
    state["source_documents"] = []
    state["pipeline"] = "rag"
    state["routing_reason"] = None
    state["error"] = None
    state["should_retry"] = False


def reset_forge_fields(state: State) -> None:
    """
    Forge Mode 필드 초기화 (다음 MCQ 생성 준비)
    
    Args:
        state: State (in-place 수정)
    """
    state["user_topic"] = None
    state["selected_part"] = None
    state["selected_chapter"] = None
    state["selected_topic_query"] = None
    state["available_chapters"] = []
    # recent_chapters는 유지 (중복 방지)
    
    state["retrieved_documents"] = []
    state["num_documents"] = 0
    state["formatted_context"] = None
    
    state["generated_mcq"] = None
    state["is_valid"] = False
    state["validation_errors"] = []
    state["retry_count"] = 0
    state["final_mcq"] = None
    state["error"] = None
    state["should_retry"] = False


# 히스토리 관리 함수들은 Utils/session.py로 이동되었습니다.
# - add_to_history()
# - get_recent_history()
# - clear_history()
# - extract_topic_from_history()
# - show_conversation_history()
# - save_session()
# - load_session()

