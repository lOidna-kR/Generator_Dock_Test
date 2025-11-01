"""
Chapter 선택 노드 (중첩 선택 지원)

선택된 Part 내에서 Chapter를 선택하는 노드입니다.
와일드카드(*), 특정 Chapter 지정, 모드(single/all) 등을 지원합니다.
"""

import logging
import random
from typing import TYPE_CHECKING, Dict, Any, List

if TYPE_CHECKING:
    from State import MCQState


def create_mcq_select_chapter_node(logger: logging.Logger):
    """
    Chapter 선택 노드를 생성하는 팩토리 함수
    
    Args:
        logger: 로거 객체
    
    Returns:
        Chapter 선택 노드 함수
    """
    
    def select_chapter(state: "MCQState") -> dict:
        """
        노드 2: Chapter 선택 (단순/중첩 통합 처리)
        
        단순 구조와 중첩 구조를 통합하여 처리합니다.
        
        Args:
            state: MCQState
        
        Returns:
            업데이트할 필드:
            - selected_chapter: 선택된 Chapter 이름
            - selected_topic_query: 검색용 쿼리
            - available_chapters: 사용 가능한 Chapter 리스트
            - error: 에러 메시지
        """
        try:
            logger.info("Chapter 선택 시작")
            
            selected_part = state["selected_part"]
            topics_hierarchical = state.get("topics_hierarchical", {})
            topics_nested = state.get("topics_nested")
            
            # 전체 Chapter 리스트
            all_chapters = topics_hierarchical.get(selected_part, [])
            
            if not all_chapters:
                raise ValueError(f"Part '{selected_part}'에 Chapter가 없습니다")
            
            # ===== 설정 가져오기 (중첩 구조 우선, 없으면 기본값) =====
            if topics_nested and selected_part in topics_nested:
                part_config = topics_nested[selected_part]
                chapters_config = part_config.get("chapters", ["*"])
                mode = part_config.get("mode", "single")
                logger.info(f"중첩 구조 사용 (모드: {mode})")
            else:
                # 기본값: 모든 Chapter, 단일 선택
                chapters_config = ["*"]
                mode = "single"
                logger.info("기본 설정 사용 (모든 Chapter, 단일 선택)")
            
            # ===== Chapter 필터링 (통합) =====
            if chapters_config == ["*"] or "*" in chapters_config:
                # 와일드카드: 모든 Chapter 사용
                available_chapters = all_chapters
                logger.info(f"와일드카드: {len(available_chapters)}개 Chapter 모두 사용")
            else:
                # 명시적 Chapter 리스트만 사용
                available_chapters = [
                    ch for ch in chapters_config 
                    if ch in all_chapters
                ]
                logger.info(
                    f"명시적 Chapter: {len(available_chapters)}개 사용 "
                    f"(전체 {len(all_chapters)}개 중)"
                )
            
            if not available_chapters:
                raise ValueError(
                    f"Part '{selected_part}'에서 선택 가능한 Chapter가 없습니다 "
                    f"(설정: {chapters_config})"
                )
            
            # ===== Mode에 따라 선택 (통합) =====
            if mode == "all":
                # 전체 Chapter를 쿼리로 사용
                selected_chapter = "전체"
                selected_topic_query = selected_part
                logger.info(
                    f"모드 'all': Part '{selected_part}' 전체 사용 "
                    f"({len(available_chapters)}개 Chapter)"
                )
            else:  # mode == "single" (기본값)
                # 하나만 랜덤 선택
                selected_chapter = random.choice(available_chapters)
                selected_topic_query = f"{selected_part} - {selected_chapter}"
                logger.info(
                    f"모드 'single': '{selected_chapter}' 선택 "
                    f"(총 {len(available_chapters)}개 중)"
                )
            
            logger.info(f"✅ 최종 쿼리: '{selected_topic_query}'")
            
            return {
                "selected_chapter": selected_chapter,
                "selected_topic_query": selected_topic_query,
                "available_chapters": available_chapters,
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"❌ Chapter 선택 실패: {e}", exc_info=True)
            return {
                "error": f"Chapter 선택 실패: {e}",
                "should_retry": False,
            }
    
    return select_chapter

