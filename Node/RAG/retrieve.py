"""
Retrieve 노드

벡터 스토어에서 관련 문서를 검색하는 노드
"""

import logging
from typing import TYPE_CHECKING

from State import State
from Utils import create_error_handler

if TYPE_CHECKING:
    from langchain_google_vertexai import VectorSearchVectorStore
    from Utils import VectorSearchUtils


def create_retrieve_documents_node(
    vector_store: "VectorSearchVectorStore",
    vector_search_utils: "VectorSearchUtils",
    retriever_config: dict,
    logger: logging.Logger,
):
    """
    문서 검색 노드를 생성하는 팩토리 함수
    
    Args:
        vector_store: 벡터 스토어 객체
        vector_search_utils: 벡터 검색 유틸리티
        retriever_config: Retriever 설정
        logger: 로거 객체
    
    Returns:
        문서 검색 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def retrieve_documents(state: State) -> dict:
        """
        노드 1: 문서 검색
        
        벡터 스토어에서 질문과 관련된 문서를 검색합니다.
        
        Args:
            state: 현재 State
        
        Returns:
            업데이트할 필드만 포함한 딕셔너리
            - context: 검색된 문서 리스트
            - num_sources: 문서 수
            
        Note:
            LangGraph 권장 방식: 노드는 업데이트할 필드만 반환
            - 명확한 업데이트 로직
            - 불변성 유지
            - LangGraph가 자동으로 상태 병합
        """
        try:
            question = state["question"]
            logger.info(f"문서 검색 시작: {question[:50]}...")
            
            # 벡터 검색 수행
            k = retriever_config["k"]
            documents = vector_search_utils.search_similar_documents(
                vector_store, question, k, logger
            )
            
            # 성공 처리
            return error_handler.handle_success(
                node_name="retrieve_documents",
                message=f"{len(documents)}개 문서 검색 완료",
                return_fields={
                    "context": documents,
                    "num_sources": len(documents),
                }
            )
            
        except Exception as e:
            # 예외 처리 (복구 가능)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="retrieve_documents",
                recoverable=True,
                custom_message="문서 검색 실패",
                return_fields={
                    "answer": "죄송합니다. 문서 검색 중 오류가 발생했습니다.",
                    "context": [],
                    "num_sources": 0,
                }
            )
    
    return retrieve_documents

