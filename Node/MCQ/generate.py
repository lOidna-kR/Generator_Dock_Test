"""
MCQ 생성 노드 (LLM 호출)

Few-shot 프롬프트를 구성하고 LLM을 호출하여 MCQ를 생성합니다.
"""

import logging
from typing import TYPE_CHECKING, List, Union

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from Utils.few_shot import build_few_shot_prompt
from Utils import create_error_handler

if TYPE_CHECKING:
    from langchain_google_vertexai import VertexAI
    from State import State


# ==================== MCQ 생성용 Pydantic 모델 ====================

class MultipleChoiceQuestion(BaseModel):
    """4지선다형 객관식 문제의 표준 구조
    
    Attributes:
        question: 교재 Context를 기반으로 생성된 최종 질문 텍스트
        options: 4개의 보기 리스트 (길이는 반드시 4)
        answer_index: 정답 보기의 인덱스 (1-4 사이)
        explanation: 해설 (문자열 또는 4개 항목 리스트)
            - str: 전체 해설 (기존 방식)
            - List[str]: 각 보기별 해설 (1번 해설, 2번 해설, 3번 해설, 4번 해설)
    """
    question: str = Field(
        description=(
            "교재 Context를 기반으로 생성된 4지선다형 질문 텍스트. 반드시 문자열이어야 하며, 질문 형식으로 작성되어야 함.\n"
            "**중요:** Few-shot 예시에 ㉠㉡㉢㉣이 포함된 경우, ㉠㉡㉢㉣ 항목을 질문 본문에 반드시 포함해야 합니다.\n"
            "예시:\n"
            "  - 일반형: \"심폐소생술에 대한 설명으로 옳은 것은?\"\n"
            "  - ㉠㉡㉢형: \"다음 중 응급의료체계에 대한 설명으로 옳은 것을 모두 고르시오.\\n\\n㉠ ... \\n㉡ ... \\n㉢ ... \\n㉣ ...\""
        )
    )
    options: List[str] = Field(
        description=(
            "4개의 보기 리스트. 반드시 정확히 4개의 문자열을 포함해야 하며, 각 보기는 명확하고 구분되어야 함.\n"
            "**중요:** 반드시 정확히 4개여야 합니다. 3개나 5개는 허용되지 않습니다.\n"
            "예: ['보기1', '보기2', '보기3', '보기4']"
        )
    )
    answer_index: int = Field(
        description=(
            "정답 보기의 인덱스. 반드시 1, 2, 3, 4 중 하나의 정수여야 하며, options 리스트의 인덱스와 일치해야 함.\n"
            "**중요:** 반드시 1, 2, 3, 4 중 하나입니다. 0이나 5 이상은 허용되지 않습니다."
        )
    )
    explanation: Union[str, List[str]] = Field(
        description=(
            "해설. 두 가지 형식 지원:\n"
            "1. 문자열 형식: 전체 해설을 하나의 문자열로 작성. 예: '정답은 3번입니다. 왜냐하면...'\n"
            "2. 리스트 형식: 각 보기별 해설을 4개의 문자열 리스트로 작성. "
            "예: ['1번은 틀렸습니다. 왜냐하면...', '2번은 틀렸습니다. 왜냐하면...', '3번이 정답입니다. 왜냐하면...', '4번은 틀렸습니다. 왜냐하면...']"
        )
    )


def create_mcq_generate_node(
    llm: "VertexAI",
    prompt_templates: dict,
    logger: logging.Logger,
):
    """
    MCQ 생성 노드를 생성하는 팩토리 함수
    
    Args:
        llm: VertexAI LLM 객체
        prompt_templates: 프롬프트 템플릿 딕셔너리
        logger: 로거 객체
    
    Returns:
        MCQ 생성 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def generate_mcq(state: "MCQState") -> dict:
        """
        노드 5: MCQ 생성 (LLM 호출)
        
        Few-shot 프롬프트를 구성하고 LLM을 호출하여 MCQ를 생성합니다.
        
        Args:
            state: State
        
        Returns:
            업데이트할 필드:
            - generated_mcq: 생성된 MCQ
            - error: 에러 메시지
            - should_retry: 재시도 여부
        """
        try:
            logger.info("MCQ 생성 시작 (LLM 호출)")
            
            # JSON 파서 생성
            parser = JsonOutputParser(pydantic_object=MultipleChoiceQuestion)
            
            # 프롬프트 템플릿
            system_template = prompt_templates["mcq_generation_system"]
            human_template = prompt_templates["mcq_generation_human_retriever"]
            
            # Few-shot 예시 추가
            few_shot_examples = state.get("few_shot_examples", [])
            max_few_shot_examples = state.get("max_few_shot_examples", 5)
            category_examples = state.get("category_examples", {})
            category_weights = state.get("category_weights", {})
            
            logger.debug(f"Few-shot 설정: max={max_few_shot_examples}, 카테고리={len(category_examples)}개")
            
            recent_indices = state.get("recent_few_shot_indices", [])
            if few_shot_examples:
                human_template, selected_indices = build_few_shot_prompt(
                    human_template, 
                    few_shot_examples,
                    max_examples=max_few_shot_examples,
                    category_examples=category_examples,
                    category_weights=category_weights,
                    recent_few_shot_indices=recent_indices
                )
                # 선택된 인덱스를 recent_few_shot_indices에 추가 (최대 10개 유지)
                updated_indices = (recent_indices + selected_indices)[-10:]
                logger.info(f"Few-shot 예시 {max_few_shot_examples}개 적용 (카테고리 가중치 선택)")
            else:
                selected_indices = []
                updated_indices = recent_indices
            
            # format_instructions 강화
            base_format_instructions = parser.get_format_instructions()
            enhanced_format_instructions = (
                base_format_instructions + "\n\n"
                "**중요: JSON 형식 준수 규칙**\n"
                "- 반드시 유효한 JSON 형식으로 응답하세요. 마크다운 코드블록(```json ... ```) 없이 순수 JSON만 응답하세요.\n"
                "- options는 반드시 정확히 4개의 문자열 리스트입니다. 3개나 5개는 허용되지 않습니다.\n"
                "- answer_index는 반드시 1, 2, 3, 4 중 하나입니다. 0이나 5 이상은 허용되지 않습니다.\n"
                "- 모든 필드는 필수이며 누락되어서는 안 됩니다."
            )
            
            # 프롬프트 생성
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_template),
                ("human", human_template),
            ]).partial(format_instructions=enhanced_format_instructions)
            
            # LLM 체인 실행
            chain = prompt | llm | parser
            
            # LLM 호출 전 로깅
            logger.debug(f"LLM 호출: 쿼리='{state['selected_topic_query'][:50]}...', 컨텍스트={len(state['formatted_context'])}자")
            
            generated_mcq = chain.invoke({
                "context": state["formatted_context"],
                "question": state["selected_topic_query"],
                "instruction": state["instruction"],
            })
            
            # 리스트로 반환된 경우 첫 번째 항목 사용 (방어 코드)
            if isinstance(generated_mcq, list):
                if generated_mcq:
                    generated_mcq = generated_mcq[0]
                    logger.warning("⚠️ LLM이 리스트를 반환했습니다. 첫 번째 항목을 사용합니다.")
                else:
                    raise ValueError("LLM이 빈 리스트를 반환했습니다")
            
            # 성공 처리
            question_preview = generated_mcq.get('question', 'N/A')[:50] if isinstance(generated_mcq, dict) else 'N/A'
            
            return_fields = {"generated_mcq": generated_mcq}
            # recent_few_shot_indices 업데이트
            if few_shot_examples:
                return_fields["recent_few_shot_indices"] = updated_indices
            
            return error_handler.handle_success(
                node_name="generate_mcq",
                message=f"MCQ 생성 완료: '{question_preview}...'",
                return_fields=return_fields
            )
            
        except Exception as e:
            # 예외 처리 (복구 가능)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="generate_mcq",
                recoverable=True,
                custom_message="MCQ 생성 실패",
                return_fields={"generated_mcq": None}
            )
    
    return generate_mcq

