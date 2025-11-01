"""Route 노드

현재는 질문 라우팅을 비활성화하고 모든 요청을 RAG 파이프라인으로 보냅니다.
"""

import logging
from typing import Optional

from State import State
from Utils import create_error_handler


def create_route_question_node(
    llm,
    logger: logging.Logger,
    prompt_template: Optional[str] = None,
):
    """질문 라우팅 노드를 생성합니다 (하지만 현재는 RAG로 고정)."""

    error_handler = create_error_handler(logger)
    _ = llm, prompt_template

    def route_question(state: State) -> dict:
        """모든 질문을 RAG 파이프라인으로 보냅니다."""

        logger.info("라우팅 비활성화 - 항상 RAG 파이프라인 사용")

        return error_handler.handle_success(
            node_name="route_question",
            message="질문 라우팅 생략, RAG 파이프라인 적용",
            return_fields={
                "pipeline": "rag",
                "routing_reason": "라우팅 기능 비활성화",
            },
        )

    return route_question


