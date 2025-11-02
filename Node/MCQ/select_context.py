"""
MCQ 컨텍스트 선택 노드

검색된 문서 중 중복 섹션을 제거하고, LLM에 전달할 핵심 컨텍스트를 선택합니다.
"""

import logging
from typing import TYPE_CHECKING, List

from Utils import create_error_handler

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.documents import Document
    from State import State


def _build_section_id_from_metadata(doc: "Document") -> str:
    """문서 메타데이터로부터 섹션 ID를 생성합니다."""
    metadata = doc.metadata or {}
    parts: List[str] = []
    for key in ("part", "chapter", "section", "subsection", "page_number", "title"):
        value = metadata.get(key)
        if value is None:
            continue
        candidate = str(value).strip()
        if candidate:
            parts.append(candidate)
    if not parts:
        parts.append(str(id(doc)))
    return "|".join(parts)


def create_mcq_select_context_node(logger: logging.Logger):
    """컨텍스트 선택 노드 팩토리"""

    error_handler = create_error_handler(logger)

    def select_context(state: "State") -> dict:
        try:
            documents = state.get("retrieved_documents", [])
            if not documents:
                return error_handler.handle_error(
                    error=ValueError("선택할 문서가 없습니다"),
                    state=state,
                    node_name="select_context_chunk",
                    recoverable=True,
                    return_fields={
                        "selected_documents": [],
                        "selected_section_ids": [],
                    },
                )

            max_docs = state.get("max_context_docs", 3) or 1
            context_section_ids = state.get("context_section_ids", [])
            context_document_ids = state.get("context_document_ids", [])

            selected_documents: List["Document"] = []
            selected_section_ids: List[str] = []
            selected_document_ids: List[str] = []
            seen_sections = set()

            for idx, doc in enumerate(documents):
                section_id = context_section_ids[idx] if idx < len(context_section_ids) else None
                if not section_id:
                    section_id = _build_section_id_from_metadata(doc)

                document_id = context_document_ids[idx] if idx < len(context_document_ids) else None
                if not document_id:
                    document_id = str(id(doc))

                if section_id in seen_sections:
                    continue

                selected_documents.append(doc)
                selected_section_ids.append(section_id)
                selected_document_ids.append(document_id)
                seen_sections.add(section_id)

                if len(selected_documents) >= max_docs:
                    break

            if not selected_documents:
                first_doc = documents[0]
                selected_documents = [first_doc]
                primary_section = context_section_ids[0] if context_section_ids else _build_section_id_from_metadata(first_doc)
                selected_section_ids = [primary_section]
                fallback_document_id = context_document_ids[0] if context_document_ids else str(id(first_doc))
                selected_document_ids = [fallback_document_id]

            logger.info(
                "컨텍스트 선택 완료: %s개 문서 (요청 최대 %s개)",
                len(selected_documents),
                max_docs,
            )

            return error_handler.handle_success(
                node_name="select_context_chunk",
                message=f"컨텍스트 문서 {len(selected_documents)}개 선택",
                return_fields={
                    "selected_documents": selected_documents,
                    "selected_section_ids": selected_section_ids,
                    "selected_document_ids": selected_document_ids,
                },
            )

        except Exception as exc:  # pragma: no cover - 방어 구문
            return error_handler.handle_error(
                error=exc,
                state=state,
                node_name="select_context_chunk",
                recoverable=True,
                return_fields={
                    "selected_documents": [],
                        "selected_section_ids": [],
                        "selected_document_ids": [],
                },
            )

    return select_context


