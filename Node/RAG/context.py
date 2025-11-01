"""
Context 노드

검색된 문서들을 LLM이 이해할 수 있는 형식으로 포맷팅하는 노드
"""

import logging

from State import State
from Utils import format_documents_for_llm, create_error_handler


def create_format_context_node(logger: logging.Logger):
    """
    컨텍스트 포맷팅 노드를 생성하는 팩토리 함수
    
    검색된 문서들을 LLM이 이해할 수 있는 형식으로 포맷팅합니다.
    retrieval 단계의 후처리로서 논리적으로 연결됩니다.
    
    Args:
        logger: 로거 객체
    
    Returns:
        컨텍스트 포맷팅 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def format_context(state: State) -> dict:
        """
        노드 2: 컨텍스트 포맷팅
        
        검색된 문서들을 LLM이 이해할 수 있는 형식으로 포맷팅합니다.
        
        Args:
            state: 현재 State
        
        Returns:
            업데이트할 필드만 포함한 딕셔너리
            - formatted_context: 포맷팅된 컨텍스트 문자열
        
        Note:
            retrieval의 후처리 단계로서, 검색된 문서를
            LLM 프롬프트에 사용할 수 있는 형식으로 변환합니다.
        """
        try:
            logger.info("컨텍스트 포맷팅 시작")
            
            documents = state["context"]
            logger.debug(f"포맷팅할 문서 수: {len(documents)}개")
            
            if not documents:
                # 문서 없음 에러 (복구 가능)
                return error_handler.handle_error(
                    error=ValueError("검색된 문서가 없습니다"),
                    state=state,
                    node_name="format_context",
                    recoverable=True,
                    return_fields={"formatted_context": "관련 문서를 찾을 수 없습니다."}
                )
            
            # 문서 포맷팅
            formatted = format_documents_for_llm(documents)
            
            # 성공 처리
            return error_handler.handle_success(
                node_name="format_context",
                message=f"{len(formatted)}자 컨텍스트 포맷팅 완료",
                return_fields={"formatted_context": formatted}
            )
            
        except Exception as e:
            # 예외 처리 (복구 가능)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="format_context",
                recoverable=True,
                custom_message="컨텍스트 포맷팅 실패",
                return_fields={
                    "answer": "죄송합니다. 컨텍스트 포맷팅 중 오류가 발생했습니다.",
                    "formatted_context": ""
                }
            )
    
    return format_context

