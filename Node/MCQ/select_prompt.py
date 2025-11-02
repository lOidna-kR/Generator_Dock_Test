"""
프롬프트 선택 노드 (범위별 동적 로딩)

선택된 Part/Chapter에 맞는 프롬프트를 동적으로 로드하는 노드입니다.

프롬프트 우선순위:
1. Chapter별 프롬프트 (가장 구체적) - Data/Prompts/{Part}/{Chapter}/*.txt
2. Part별 프롬프트 - Data/Prompts/{Part}/*.txt
3. 기본 프롬프트 (fallback) - Data/Prompts/*.txt

이 노드는 select_chapter 노드 이후, retrieve_documents 노드 이전에 실행됩니다.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from State import State


def create_mcq_select_prompt_node(logger: logging.Logger):
    """
    프롬프트 선택 노드를 생성하는 팩토리 함수
    
    선택된 Part/Chapter에 맞는 프롬프트를 동적으로 로드합니다.
    
    Args:
        logger: 로거 객체
    
    Returns:
        프롬프트 선택 노드 함수
    
    Example:
        >>> from Utils import setup_logging
        >>> logger = setup_logging("Node.SelectPrompt")
        >>> select_prompt_node = create_mcq_select_prompt_node(logger)
        >>> result = select_prompt_node(state)
    """
    
    def select_prompt(state: "State") -> Dict[str, Optional[str]]:
        """
        노드: 프롬프트 선택 (범위별 동적 로딩)
        
        선택된 Part/Chapter에 맞는 프롬프트를 로드하여 State에 저장합니다.
        프롬프트 파일이 없으면 상위 레벨 또는 기본 프롬프트로 fallback합니다.
        
        Args:
            state: State 객체
        
        Returns:
            업데이트할 State 필드 딕셔너리:
            - system_prompt: 로드된 시스템 프롬프트
            - retriever_prompt: 로드된 retriever 프롬프트
            - error: 에러 메시지 (오류 발생 시)
        
        Raises:
            FileNotFoundError: 기본 프롬프트 파일이 없는 경우
        
        Example:
            >>> state = {"selected_part": "각론", "selected_chapter": "전문심장소생술"}
            >>> result = select_prompt(state)
            >>> print(result["system_prompt"][:50])
        """
        try:
            logger.info("=" * 60)
            logger.info("프롬프트 선택 시작")
            
            # State에서 선택된 범위 가져오기
            selected_part = state.get("selected_part")
            selected_chapter = state.get("selected_chapter")
            
            logger.info(f"선택된 범위: Part={selected_part}, Chapter={selected_chapter}")
            
            # 프롬프트 디렉토리 경로 (절대 경로)
            base_path = Path(__file__).resolve().parent.parent.parent
            prompt_dir = base_path / "Data" / "Prompts"
            
            if not prompt_dir.exists():
                raise FileNotFoundError(
                    f"프롬프트 디렉토리가 존재하지 않습니다: {prompt_dir}"
                )
            
            # 기본 프롬프트 파일 경로
            default_system_file = prompt_dir / "system_prompt.txt"
            default_retriever_file = prompt_dir / "retriever_prompt.txt"
            
            # 기본 프롬프트 로드 (필수)
            if not default_system_file.exists():
                raise FileNotFoundError(
                    f"기본 시스템 프롬프트가 없습니다: {default_system_file}"
                )
            if not default_retriever_file.exists():
                raise FileNotFoundError(
                    f"기본 retriever 프롬프트가 없습니다: {default_retriever_file}"
                )
            
            system_prompt = default_system_file.read_text(encoding="utf-8")
            retriever_prompt = default_retriever_file.read_text(encoding="utf-8")
            
            prompt_source = "기본"
            logger.info(f"기본 프롬프트 로드 완료")
            
            # Part별 프롬프트 확인 및 오버라이드
            if selected_part:
                part_dir = prompt_dir / selected_part
                
                if part_dir.exists():
                    # Part별 시스템 프롬프트
                    part_system_file = part_dir / "system_prompt.txt"
                    if part_system_file.exists():
                        system_prompt = part_system_file.read_text(encoding="utf-8")
                        prompt_source = f"Part({selected_part})"
                        logger.info(f"Part별 시스템 프롬프트 적용: {selected_part}")
                    
                    # Part별 retriever 프롬프트
                    part_retriever_file = part_dir / "retriever_prompt.txt"
                    if part_retriever_file.exists():
                        retriever_prompt = part_retriever_file.read_text(encoding="utf-8")
                        logger.info(f"Part별 retriever 프롬프트 적용: {selected_part}")
                else:
                    logger.debug(f"Part 디렉토리 없음: {part_dir}")
            
            # Chapter별 프롬프트 확인 및 오버라이드 (최우선)
            if selected_part and selected_chapter:
                chapter_dir = prompt_dir / selected_part / selected_chapter
                
                if chapter_dir.exists():
                    # Chapter별 시스템 프롬프트
                    chapter_system_file = chapter_dir / "system_prompt.txt"
                    if chapter_system_file.exists():
                        system_prompt = chapter_system_file.read_text(encoding="utf-8")
                        prompt_source = f"Chapter({selected_part}/{selected_chapter})"
                        logger.info(
                            f"Chapter별 시스템 프롬프트 적용: "
                            f"{selected_part}/{selected_chapter}"
                        )
                    
                    # Chapter별 retriever 프롬프트
                    chapter_retriever_file = chapter_dir / "retriever_prompt.txt"
                    if chapter_retriever_file.exists():
                        retriever_prompt = chapter_retriever_file.read_text(
                            encoding="utf-8"
                        )
                        logger.info(
                            f"Chapter별 retriever 프롬프트 적용: "
                            f"{selected_part}/{selected_chapter}"
                        )
                else:
                    logger.debug(f"Chapter 디렉토리 없음: {chapter_dir}")
            
            # 프롬프트 크기 정보
            system_size = len(system_prompt)
            retriever_size = len(retriever_prompt)
            
            logger.info(
                f"프롬프트 선택 완료: {prompt_source} "
                f"(시스템: {system_size}자, retriever: {retriever_size}자)"
            )
            logger.info("=" * 60)
            
            return {
                "system_prompt": system_prompt,
                "retriever_prompt": retriever_prompt,
                "error": None,
            }
            
        except FileNotFoundError as e:
            error_msg = f"프롬프트 파일을 찾을 수 없습니다: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "system_prompt": None,
                "retriever_prompt": None,
                "error": error_msg,
            }
            
        except Exception as e:
            error_msg = f"프롬프트 선택 실패: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "system_prompt": None,
                "retriever_prompt": None,
                "error": error_msg,
            }
    
    return select_prompt

