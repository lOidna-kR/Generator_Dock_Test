"""
Answer 노드

LLM을 사용하여 답변을 생성하는 노드
"""

import logging
from typing import TYPE_CHECKING

from langchain_core.output_parsers import StrOutputParser
from State import State
from Utils import create_error_handler

if TYPE_CHECKING:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_google_vertexai import VertexAI


def create_generate_answer_node(
    llm: "VertexAI",
    rag_prompt: "ChatPromptTemplate",
    chat_prompt: "ChatPromptTemplate",
    logger: logging.Logger,
):
    """
    답변 생성 노드를 생성하는 팩토리 함수
    
    LangChain 체인 방식을 사용하여 프롬프트 -> LLM -> 문자열 변환을
    파이프라인으로 처리합니다.
    
    Args:
        llm: VertexAI LLM 객체
        prompt: 프롬프트 템플릿
        logger: 로거 객체
    
    Returns:
        답변 생성 노드 함수
    """
    # LangChain 체인 생성 (prompt | llm | output_parser)
    rag_chain = rag_prompt | llm | StrOutputParser()
    chat_chain = None
    if chat_prompt is not None:
        chat_chain = chat_prompt | llm | StrOutputParser()
    
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def generate_answer(state: State) -> dict:
        """
        노드 3: 답변 생성
        
        LLM을 사용하여 질문에 대한 답변을 생성합니다.
        
        Args:
            state: 현재 State
        
        Returns:
            업데이트할 필드만 포함한 딕셔너리
            - answer: 생성된 답변
        
        Note:
            StrOutputParser를 사용하여 LLM 응답을 자동으로 문자열로 변환합니다.
            이를 통해 AIMessage 객체가 아닌 순수 텍스트를 반환받습니다.
        """
        try:
            question = state.get("question", "")
            pipeline = state.get("pipeline", "rag")
            context = state.get("formatted_context") or ""
            
            logger.info("답변 생성 시작")
            logger.debug(f"질문: {question[:100]}...")
            if pipeline == "chat":
                logger.debug("파이프라인: chat (컨텍스트 없이 응답)")
                if chat_chain is None:
                    answer = "죄송합니다. 현재 일반 대화를 처리할 수 없습니다."
                else:
                    answer = chat_chain.invoke({"question": question})
            else:
                logger.debug(f"파이프라인: rag (컨텍스트 길이: {len(context)}자)")
                answer = rag_chain.invoke({
                    "question": question,
                    "context": context,
                })
            
            # 성공 처리
            return error_handler.handle_success(
                node_name="generate_answer",
                message=f"{len(answer)}자 답변 생성 완료",
                return_fields={"answer": answer}
            )
            
        except Exception as e:
            # 예외 처리 (복구 가능)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="generate_answer",
                recoverable=True,
                custom_message="답변 생성 실패",
                return_fields={"answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다."}
            )
    
    return generate_answer

