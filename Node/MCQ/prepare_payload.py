"""MCQ 페이로드 준비 노드"""

import logging
from typing import TYPE_CHECKING

from Utils import create_error_handler

if TYPE_CHECKING:  # pragma: no cover
    from State import State


def create_mcq_prepare_payload_node(logger: logging.Logger):
    """LLM 호출 이전에 페이로드를 구성하는 노드"""

    error_handler = create_error_handler(logger)

    def prepare_payload(state: "State") -> dict:
        try:
            formatted_context = state.get("formatted_context", "")
            if not formatted_context.strip():
                return error_handler.handle_error(
                    error=ValueError("생성용 컨텍스트가 비어 있습니다"),
                    state=state,
                    node_name="prepare_generation_payload",
                    recoverable=True,
                    return_fields={"generation_payload": {}},
                )

            payload = {
                "context": formatted_context,
                "instruction": state.get("instruction", ""),
                "selected_topic": state.get("selected_topic_query"),
                "category_weights": state.get("category_weights", {}),
                "few_shot_examples": state.get("few_shot_examples", []),
                "category_examples": state.get("category_examples", {}),
                "max_few_shot_examples": state.get("max_few_shot_examples", 0),
                "selected_section_ids": state.get("selected_section_ids", []),
                "selected_document_ids": state.get("selected_document_ids", []),
            }

            logger.info("LLM 페이로드 구성 완료")

            return error_handler.handle_success(
                node_name="prepare_generation_payload",
                message="페이로드 준비 완료",
                return_fields={"generation_payload": payload},
            )

        except Exception as exc:  # pragma: no cover
            return error_handler.handle_error(
                error=exc,
                state=state,
                node_name="prepare_generation_payload",
                recoverable=True,
                return_fields={"generation_payload": {}},
            )

    return prepare_payload


