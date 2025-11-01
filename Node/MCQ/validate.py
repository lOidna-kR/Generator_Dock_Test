"""
MCQ 유효성 검증 노드

생성된 MCQ가 기준을 만족하는지 검증합니다.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, List

from Utils import create_error_handler

if TYPE_CHECKING:
    from State import State


def create_mcq_validate_node(logger: logging.Logger):
    """
    유효성 검증 노드를 생성하는 팩토리 함수
    
    Args:
        logger: 로거 객체
    
    Returns:
        유효성 검증 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    def validate_mcq(state: "MCQState") -> dict:
        """
        노드 6: MCQ 유효성 검증
        
        생성된 MCQ가 기준을 만족하는지 검증합니다.
        
        검증 항목:
        - 필수 필드 존재 (question, options, answer_index, explanation)
        - options가 정확히 4개
        - answer_index가 1-4 범위
        - 옵션 중복 없음
        - 빈 필드 없음
        
        Args:
            state: State
        
        Returns:
            업데이트할 필드:
            - is_valid: 유효성 검증 결과
            - validation_errors: 검증 오류 목록
            - should_retry: 재시도 여부
            - retry_count: 재시도 횟수 (증가)
        """
        try:
            logger.info("MCQ 유효성 검증 시작")
            
            mcq = state.get("generated_mcq")
            if not mcq:
                # MCQ 없음 에러 (검증 실패 처리)
                return error_handler.handle_validation_error(
                    errors=["생성된 MCQ가 없습니다"],
                    state=state,
                    node_name="validate_mcq"
                )
            
            # MCQ 구조 검증
            errors = _validate_mcq_structure(mcq, logger)
            
            # 검증 성공
            if len(errors) == 0:
                logger.info("✅ MCQ 유효성 검증 성공")
                return {
                    "is_valid": True,
                    "validation_errors": [],
                }
            
            # 검증 실패 (표준화된 처리)
            return error_handler.handle_validation_error(
                errors=errors,
                state=state,
                node_name="validate_mcq"
            )
            
        except Exception as e:
            # 예외 발생 시 (복구 가능한 에러로 처리)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="validate_mcq",
                recoverable=True,
                custom_message="유효성 검증 중 오류",
                return_fields={
                    "is_valid": False,
                    "validation_errors": [f"검증 오류: {str(e)}"]
                }
            )
    
    def _validate_mcq_structure(
        mcq: Dict[str, Any], 
        logger: logging.Logger
    ) -> List[str]:
        """
        MCQ 구조 검증
        
        Args:
            mcq: 검증할 MCQ
            logger: 로거
        
        Returns:
            오류 목록 (빈 리스트면 유효)
        """
        errors = []
        
        # 1. 필수 필드 확인
        required_fields = ["question", "options", "answer_index", "explanation"]
        for field in required_fields:
            if field not in mcq:
                errors.append(f"필수 필드 '{field}' 누락")
        
        if errors:
            return errors
        
        # 2. options 개수 확인
        if len(mcq["options"]) != 4:
            errors.append(
                f"options 개수가 4개가 아님 (현재: {len(mcq['options'])})"
            )
        
        # 3. answer_index 범위 확인
        if not (1 <= mcq["answer_index"] <= 4):
            errors.append(
                f"answer_index가 1-4 범위를 벗어남 (현재: {mcq['answer_index']})"
            )
        
        # 4. 옵션 중복 확인
        if len(set(mcq["options"])) != len(mcq["options"]):
            errors.append("옵션에 중복이 존재")
        
        # 5. 빈 필드 확인
        if not mcq["question"].strip():
            errors.append("question이 비어있음")
        
        # explanation 검증 (문자열 또는 리스트)
        explanation = mcq["explanation"]
        if isinstance(explanation, str):
            # 문자열 형식
            if not explanation.strip():
                errors.append("explanation이 비어있음")
        elif isinstance(explanation, list):
            # 리스트 형식: 4개 항목이어야 함
            if len(explanation) != 4:
                errors.append(
                    f"explanation 리스트가 4개가 아님 (현재: {len(explanation)})"
                )
            # 각 항목이 비어있지 않은지 확인
            for i, expl in enumerate(explanation):
                if not expl.strip():
                    errors.append(f"explanation[{i}]가 비어있음")
        else:
            errors.append(
                f"explanation이 문자열도 리스트도 아님 (타입: {type(explanation).__name__})"
            )
        
        for i, option in enumerate(mcq["options"]):
            if not option.strip():
                errors.append(f"options[{i}]가 비어있음")
        
        return errors
    
    return validate_mcq

