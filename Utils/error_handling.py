"""
노드 에러 처리 표준화 모듈

모든 LangGraph 노드에서 일관된 에러 처리를 제공합니다.

특징:
- 표준화된 에러 응답 형식
- 자동 재시도 로직
- 상세한 로깅
- State 타입별 대응
"""

import logging
from typing import Any, Dict, Optional


class NodeErrorHandler:
    """
    노드 에러 처리 표준화 클래스
    
    모든 LangGraph 노드에서 일관된 방식으로 에러를 처리합니다.
    
    사용 예제:
        >>> handler = NodeErrorHandler(logger, max_retries=6)
        >>> 
        >>> try:
        >>>     # 노드 로직
        >>>     result = do_something()
        >>> except Exception as e:
        >>>     return handler.handle_error(
        >>>         error=e,
        >>>         state=state,
        >>>         node_name="retrieve_documents",
        >>>         recoverable=True
        >>>     )
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        max_retries: int = 6,
        log_traceback: bool = True
    ):
        """
        초기화
        
        Args:
            logger: 로거 객체
            max_retries: 최대 재시도 횟수 (기본값: 6)
            log_traceback: 스택 트레이스 로깅 여부 (기본값: True)
        """
        self.logger = logger
        self.max_retries = max_retries
        self.log_traceback = log_traceback
    
    def handle_error(
        self,
        error: Exception,
        state: Dict[str, Any],
        node_name: str,
        recoverable: bool = True,
        custom_message: Optional[str] = None,
        return_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        에러를 표준화된 방식으로 처리합니다.
        
        Args:
            error: 발생한 예외 객체
            state: 현재 State
            node_name: 노드 이름 (로깅용)
            recoverable: 복구 가능한 에러인지 여부
                - True: 재시도 가능
                - False: 즉시 실패 처리
            custom_message: 사용자 정의 에러 메시지 (선택사항)
            return_fields: 추가로 반환할 필드들 (선택사항)
        
        Returns:
            State 업데이트용 딕셔너리:
            - error: 에러 메시지
            - should_retry: 재시도 여부
            - retry_count: 업데이트된 재시도 횟수
            - (추가 필드들)
        
        예제:
            >>> # 복구 가능한 에러
            >>> return handler.handle_error(
            ...     error=e,
            ...     state=state,
            ...     node_name="retrieve_documents",
            ...     recoverable=True,
            ...     return_fields={"retrieved_documents": [], "num_documents": 0}
            ... )
            
            >>> # 복구 불가능한 에러
            >>> return handler.handle_error(
            ...     error=e,
            ...     state=state,
            ...     node_name="validate_mcq",
            ...     recoverable=False,
            ...     custom_message="MCQ 검증 실패 (치명적 오류)"
            ... )
        """
        # 재시도 횟수 계산
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", self.max_retries)
        
        # 재시도 가능 여부 결정
        should_retry = recoverable and (retry_count < max_retries)
        
        # 에러 메시지 생성
        if custom_message:
            error_message = f"{custom_message}: {str(error)}"
        else:
            error_message = f"{node_name} 실패: {str(error)}"
        
        # 로깅
        log_msg = f"❌ {error_message}"
        if should_retry:
            log_msg += f" (재시도 {retry_count + 1}/{max_retries})"
        else:
            log_msg += " (재시도 불가)"
        
        if self.log_traceback:
            self.logger.error(log_msg, exc_info=True)
        else:
            self.logger.error(log_msg)
        
        # 기본 반환 필드
        result: Dict[str, Any] = {
            "error": error_message,
            "should_retry": should_retry,
            "retry_count": retry_count + 1 if recoverable else retry_count,
        }
        
        # 추가 필드 병합
        if return_fields:
            result.update(return_fields)
        
        return result
    
    def handle_validation_error(
        self,
        errors: list,
        state: Dict[str, Any],
        node_name: str = "validation"
    ) -> Dict[str, Any]:
        """
        검증 에러를 처리합니다 (MCQ 검증 등)
        
        Args:
            errors: 검증 오류 리스트
            state: 현재 State
            node_name: 노드 이름 (로깅용)
        
        Returns:
            State 업데이트용 딕셔너리
        
        예제:
            >>> errors = ["필수 필드 누락", "옵션 개수 부족"]
            >>> return handler.handle_validation_error(
            ...     errors=errors,
            ...     state=state,
            ...     node_name="validate_mcq"
            ... )
        """
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", self.max_retries)
        should_retry = retry_count < max_retries
        
        # 로깅
        error_summary = "; ".join(errors[:3])  # 처음 3개만 표시
        if len(errors) > 3:
            error_summary += f" (외 {len(errors) - 3}개)"
        
        log_msg = f"⚠️  {node_name} 검증 실패: {error_summary}"
        if should_retry:
            log_msg += f" (재시도 {retry_count + 1}/{max_retries})"
        
        self.logger.warning(log_msg)
        
        return {
            "is_valid": False,
            "validation_errors": errors,
            "should_retry": should_retry,
            "retry_count": retry_count + 1,
        }
    
    def handle_success(
        self,
        node_name: str,
        message: Optional[str] = None,
        return_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        성공 케이스를 처리합니다 (로깅 포함)
        
        Args:
            node_name: 노드 이름 (로깅용)
            message: 성공 메시지 (선택사항)
            return_fields: 반환할 필드들
        
        Returns:
            State 업데이트용 딕셔너리
        
        예제:
            >>> return handler.handle_success(
            ...     node_name="retrieve_documents",
            ...     message=f"{len(docs)}개 문서 검색 완료",
            ...     return_fields={
            ...         "retrieved_documents": docs,
            ...         "num_documents": len(docs),
            ...         "error": None
            ...     }
            ... )
        """
        # 로깅
        if message:
            self.logger.info(f"✅ {node_name}: {message}")
        else:
            self.logger.info(f"✅ {node_name} 완료")
        
        # 기본 반환 필드
        result: Dict[str, Any] = {
            "error": None,
        }
        
        # 추가 필드 병합
        if return_fields:
            result.update(return_fields)
        
        return result


# ==================== 헬퍼 함수 ====================


def create_error_handler(
    logger: logging.Logger,
    max_retries: int = 6,
    log_traceback: bool = True
) -> NodeErrorHandler:
    """
    NodeErrorHandler 인스턴스를 생성하는 헬퍼 함수
    
    Args:
        logger: 로거 객체
        max_retries: 최대 재시도 횟수
        log_traceback: 스택 트레이스 로깅 여부
    
    Returns:
        NodeErrorHandler 인스턴스
    
    예제:
        >>> from Utils import create_error_handler
        >>> 
        >>> def create_my_node(logger):
        >>>     handler = create_error_handler(logger, max_retries=3)
        >>>     
        >>>     def my_node(state):
        >>>         try:
        >>>             # ... 로직 ...
        >>>         except Exception as e:
        >>>             return handler.handle_error(e, state, "my_node")
        >>>     
        >>>     return my_node
    """
    return NodeErrorHandler(
        logger=logger,
        max_retries=max_retries,
        log_traceback=log_traceback
    )


def should_continue_retry(state: Dict[str, Any], max_retries: int = 6) -> bool:
    """
    재시도를 계속해야 하는지 판단하는 헬퍼 함수
    
    조건부 엣지에서 사용할 수 있습니다.
    
    Args:
        state: 현재 State
        max_retries: 최대 재시도 횟수
    
    Returns:
        True: 재시도 가능
        False: 재시도 불가 (최대 횟수 도달 또는 should_retry=False)
    
    예제:
        >>> # Edge 정의
        >>> workflow.add_conditional_edges(
        ...     "my_node",
        ...     lambda state: "retry" if should_continue_retry(state) else "continue",
        ...     {"retry": "my_node", "continue": "next_node"}
        ... )
    """
    retry_count = state.get("retry_count", 0)
    should_retry = state.get("should_retry", False)
    max_retries_from_state = state.get("max_retries", max_retries)
    
    return should_retry and (retry_count < max_retries_from_state)


def get_retry_info(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    현재 재시도 정보를 반환하는 헬퍼 함수
    
    Args:
        state: 현재 State
    
    Returns:
        재시도 정보 딕셔너리:
        - retry_count: 현재 재시도 횟수
        - max_retries: 최대 재시도 횟수
        - remaining_retries: 남은 재시도 횟수
        - should_retry: 재시도 가능 여부
    
    예제:
        >>> info = get_retry_info(state)
        >>> print(f"재시도 {info['retry_count']}/{info['max_retries']}")
        >>> print(f"남은 재시도: {info['remaining_retries']}회")
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 6)
    should_retry = state.get("should_retry", False)
    
    return {
        "retry_count": retry_count,
        "max_retries": max_retries,
        "remaining_retries": max(0, max_retries - retry_count),
        "should_retry": should_retry,
    }

