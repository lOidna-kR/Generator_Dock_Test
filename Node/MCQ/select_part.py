"""
Part 선택 노드 (중첩 선택 지원)

MCQ 생성을 위해 Part를 선택하는 노드입니다.
중첩 선택 구조와 기존 단순 구조를 모두 지원합니다.
"""

import logging
import random
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from State import MCQState


def create_mcq_select_part_node(logger: logging.Logger):
    """
    Part 선택 노드를 생성하는 팩토리 함수
    
    중첩 선택 구조를 우선 사용하고, 없으면 기존 구조를 사용합니다.
    
    Args:
        logger: 로거 객체
    
    Returns:
        Part 선택 노드 함수
    """
    
    def select_part(state: "MCQState") -> dict:
        """
        노드 1: Part 선택 (단순/중첩 통합 처리)
        
        단순 구조와 중첩 구조를 통합하여 처리합니다.
        
        Args:
            state: MCQState
        
        Returns:
            업데이트할 필드:
            - selected_part: 선택된 Part 이름
            - error: 에러 메시지 (없으면 None)
        """
        try:
            logger.info("Part 선택 시작")
            
            topics_hierarchical = state.get("topics_hierarchical", {})
            topics_nested = state.get("topics_nested")
            part_weights = state.get("part_weights")
            
            if not topics_hierarchical:
                raise ValueError("주제 설정이 없습니다 (topics_hierarchical 필요)")
            
            parts = list(topics_hierarchical.keys())
            
            # ===== 가중치 추출 (중첩 구조 우선, 없으면 part_weights 사용) =====
            if topics_nested:
                # 중첩 구조에서 가중치 추출
                weights = [
                    topics_nested.get(p, {}).get("weight", 1.0) 
                    for p in parts
                ]
                logger.info(f"중첩 구조 사용 (가중치: {dict(zip(parts, weights))})")
            elif part_weights:
                # part_weights 사용
                weights = [part_weights.get(p, 1.0) for p in parts]
                logger.info(f"part_weights 사용 (가중치: {dict(zip(parts, weights))})")
            else:
                # 균등 확률
                weights = [1.0] * len(parts)
                logger.info("균등 확률 선택")
            
            # ===== 가중치 기반 선택 (통합) =====
            selected_part = random.choices(parts, weights=weights, k=1)[0]
            
            logger.info(f"✅ 선택된 Part: '{selected_part}'")
            
            return {
                "selected_part": selected_part,
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"❌ Part 선택 실패: {e}", exc_info=True)
            return {
                "error": f"Part 선택 실패: {e}",
                "should_retry": False,
            }
    
    return select_part

