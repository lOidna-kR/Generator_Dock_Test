"""
Output 노드

최종 결과를 사용자에게 반환할 형식으로 포맷팅하는 노드
"""

import logging

from State import State
from Utils import create_error_handler


def create_format_output_node(logger: logging.Logger):
    """
    출력 포맷팅 노드를 생성하는 팩토리 함수
    
    최종 결과를 사용자에게 반환할 형식으로 포맷팅합니다.
    generation 단계의 후처리로서 논리적으로 연결됩니다.
    
    Args:
        logger: 로거 객체
    
    Returns:
        출력 포맷팅 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def format_output(state: State) -> dict:
        """
        노드 4: 출력 포맷팅
        
        최종 결과를 사용자에게 반환할 형식으로 포맷팅합니다.
        
        Args:
            state: 현재 State
        
        Returns:
            업데이트할 필드만 포함한 딕셔너리
            - source_documents: 출처 문서 정보 리스트
        
        Note:
            generation의 후처리 단계로서, 출처 문서 메타데이터를
            사용자에게 표시할 형식으로 정리합니다.
        """
        try:
            logger.info("출력 포맷팅 시작")
            
            # 출처 문서 정보 생성
            source_documents = []
            for doc in state["context"]:
                source_documents.append({
                    "content": (
                        doc.page_content[:300] + "..."
                        if len(doc.page_content) > 300
                        else doc.page_content
                    ),
                    "metadata": doc.metadata,
                })
            
            logger.debug(f"출처 문서 {len(source_documents)}개 포맷팅 완료")
            
            # 성공 처리
            return error_handler.handle_success(
                node_name="format_output",
                message=f"{len(source_documents)}개 출처 문서 포맷팅 완료",
                return_fields={"source_documents": source_documents}
            )
            
        except Exception as e:
            # 예외 처리 (복구 불가능 - 이미 답변이 생성된 상태)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="format_output",
                recoverable=False,
                custom_message="출력 포맷팅 실패",
                return_fields={
                    "answer": "죄송합니다. 출력 포맷팅 중 오류가 발생했습니다.",
                    "source_documents": []
                }
            )
    
    return format_output

