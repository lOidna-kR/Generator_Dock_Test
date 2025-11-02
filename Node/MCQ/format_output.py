"""
MCQ 출력 포맷팅 노드

메타데이터를 추가하여 최종 MCQ를 생성합니다.
"""

import logging
import hashlib
from datetime import datetime
from typing import TYPE_CHECKING

from Utils import create_error_handler

if TYPE_CHECKING:
    from State import State


def create_mcq_format_output_node(logger: logging.Logger):
    """
    출력 포맷팅 노드를 생성하는 팩토리 함수
    
    Args:
        logger: 로거 객체
    
    Returns:
        출력 포맷팅 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def format_output(state: "MCQState") -> dict:
        """
        노드 7: 출력 포맷팅
        
        메타데이터를 추가하여 최종 MCQ를 생성합니다.
        
        추가되는 메타데이터:
        - timestamp: 생성 시각
        - selected_part: 선택된 Part
        - selected_chapter: 선택된 Chapter
        - selected_topic: 검색 쿼리
        
        Args:
            state: State
        
        Returns:
            업데이트할 필드:
            - final_mcq: 메타데이터 포함 최종 MCQ
            - error: 에러 메시지
        """
        try:
            logger.info("MCQ 출력 포맷팅 시작")
            
            mcq = state["generated_mcq"].copy()
            
            # 기본 메타데이터 추가
            mcq["timestamp"] = datetime.now().isoformat()
            mcq["selected_part"] = state["selected_part"]
            mcq["selected_chapter"] = state["selected_chapter"]
            mcq["selected_topic"] = state["selected_topic_query"]
            mcq["available_chapters"] = state.get("available_chapters", [])
            
            # 검색된 문서의 메타데이터 추가
            documents = state.get("retrieved_documents", [])
            if documents:
                # 첫 번째 문서의 메타데이터 사용 (대표값)
                first_doc = documents[0]
                metadata = first_doc.metadata if hasattr(first_doc, 'metadata') else {}
                
                mcq["doc_title"] = metadata.get("title", "N/A")
                mcq["doc_part"] = metadata.get("part", state["selected_part"])
                mcq["doc_chapter"] = metadata.get("chapter", state["selected_chapter"])
                mcq["doc_section"] = metadata.get("section", "N/A")
                mcq["doc_page_number"] = metadata.get("page_number", "N/A")

                section_ids = (
                    state.get("selected_section_ids")
                    or state.get("context_section_ids")
                    or []
                )
                document_ids = (
                    state.get("selected_document_ids")
                    or state.get("context_document_ids")
                    or []
                )
            else:
                mcq["doc_title"] = "N/A"
                mcq["doc_part"] = state["selected_part"]
                mcq["doc_chapter"] = state["selected_chapter"]
                mcq["doc_section"] = "N/A"
                mcq["doc_page_number"] = "N/A"

                section_ids = []
                document_ids = []

            mcq["doc_section_ids"] = section_ids
            mcq["doc_section_id"] = section_ids[0] if section_ids else None
            mcq["doc_document_ids"] = document_ids
            mcq["doc_document_id"] = document_ids[0] if document_ids else None

            question_signature = "||".join([
                mcq.get("question", "").strip(),
                *[opt.strip() for opt in mcq.get("options", [])],
            ])
            mcq["question_hash"] = hashlib.sha256(question_signature.encode("utf-8")).hexdigest()
            
            # 성공 처리
            return error_handler.handle_success(
                node_name="format_output",
                message="MCQ 출력 포맷팅 완료",
                return_fields={"final_mcq": mcq}
            )
            
        except Exception as e:
            # 예외 처리 (복구 불가능 - 이미 MCQ가 생성된 상태)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="format_output",
                recoverable=False,
                custom_message="출력 포맷팅 실패",
                return_fields={"final_mcq": None}
            )
    
    return format_output

