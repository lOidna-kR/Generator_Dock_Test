"""
MCQ용 컨텍스트 포맷팅 노드

검색된 문서들을 LLM이 이해할 수 있는 형식으로 변환합니다.
"""

import logging
from typing import TYPE_CHECKING

from Utils import format_documents_for_llm, create_error_handler

if TYPE_CHECKING:
    from State import State


def create_mcq_format_context_node(logger: logging.Logger):
    """
    컨텍스트 포맷팅 노드를 생성하는 팩토리 함수
    
    Args:
        logger: 로거 객체
    
    Returns:
        컨텍스트 포맷팅 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def format_context(state: "MCQState") -> dict:
        """
        노드 4: 컨텍스트 포맷팅
        
        검색된 문서들을 LLM이 이해할 수 있는 형식으로 변환합니다.
        
        Args:
            state: State
        
        Returns:
            업데이트할 필드:
            - formatted_context: 포맷팅된 컨텍스트 문자열
            - error: 에러 메시지
            - should_retry: 재시도 여부
        """
        try:
            logger.info("컨텍스트 포맷팅 시작")
            
            documents = state["retrieved_documents"]
            
            if not documents:
                # 문서 없음 에러 (복구 가능)
                return error_handler.handle_error(
                    error=ValueError("포맷팅할 문서가 없습니다"),
                    state=state,
                    node_name="format_context",
                    recoverable=True,
                    return_fields={"formatted_context": ""}
                )
            
            # 문서 포맷팅
            formatted = format_documents_for_llm(documents)
            
            # 성공 처리
            return error_handler.handle_success(
                node_name="format_context",
                message=f"{len(formatted)}자 포맷팅 완료",
                return_fields={"formatted_context": formatted}
            )
            
        except Exception as e:
            # 예외 처리 (복구 가능)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="format_context",
                recoverable=True,
                return_fields={"formatted_context": ""}
            )
    
    return format_context

