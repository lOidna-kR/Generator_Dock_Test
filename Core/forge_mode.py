"""
Forge Mode - MCQ 생성 모드

주요 기능:
- LangGraph StateGraph를 사용한 명시적 워크플로우
- 전체 범위에서 랜덤 주제 선택
- 자동 재시도 로직
- Few-shot Learning 지원
- MCQ 생성 히스토리 추적

최신 LangGraph 권장 방식 100% 준수
"""

import logging
from typing import Any, Dict, List, Optional

# LangChain & LangGraph
from langchain_google_vertexai import VertexAI, VectorSearchVectorStore
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Config
from config import get_retriever_config

try:
    from config import (
        get_mcq_generation_config,
        get_mcq_types,
        get_prompt_templates,
    )
except ImportError:
    # config에 없으면 기본값 사용
    def get_mcq_generation_config():
        return {}
    
    def get_mcq_types():
        return {
            "MCQ_GENERAL": {
                "instruction": "교재 내용을 기반으로 4지선다형 문제를 생성하세요.",
                "few_shot_examples": []
            }
        }
    
    def get_prompt_templates():
        return {
            "mcq_generation_system": "당신은 교육 전문가입니다. 주어진 교재 내용을 바탕으로 4지선다형 문제를 생성합니다.",
            "mcq_generation_human_retriever": "다음 내용을 바탕으로 4지선다형 문제를 만들어주세요:\n\n{context}\n\n주제: {question}\n\n{instruction}\n\n{format_instructions}",
        }

# State & Nodes
from State import State, create_state
from Node.MCQ import (
    create_mcq_retrieve_documents_node,
    create_mcq_format_context_node,
    create_mcq_generate_node,
    create_mcq_validate_node,
    create_mcq_format_output_node,
)

# Edge & Utils
from Edge import build_mcq_workflow_edges
from Utils import VectorSearchUtils, setup_logging


class ForgeMode:
    """
    Forge Mode - MCQ 생성 모드
    
    특징:
    - LangGraph StateGraph 사용
    - 5개 노드로 구성된 간소화 워크플로우
    - 전체 범위에서 랜덤 주제 선택
    - 자동 재시도 로직 (설정 가능)
    - Few-shot Learning 지원
    - Checkpointer로 상태 저장/복원
    
    사용 예제:
        # 1. 초기화
        generator = MCQ_Generator(
            vector_store=vector_store,
            llm=llm
        )
        
        # 2. 교재 구조 설정
        topics_hierarchical = {
            "Part 1": ["Ch1", "Ch2", "Ch3"],
            "Part 2": ["Ch1", "Ch2"],
        }
        
        # 3. MCQ 생성 (랜덤 주제 자동 선택)
        mcq = generator.generate_mcq(
            topics_hierarchical=topics_hierarchical,
            topics_nested=None,  # 사용 안 함
            max_retries=6
        )
    """
    
    def __init__(
        self,
        vector_store: VectorSearchVectorStore,
        llm: VertexAI,
        custom_config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        MCQ_Generator 초기화
        
        Args:
            vector_store: 벡터 스토어 객체
            llm: VertexAI LLM 객체
            custom_config: 사용자 정의 설정 (선택사항)
            logger: 로거 객체 (선택사항)
        """
        # 로깅
        self.logger = logger or setup_logging("Core.MCQ_Generator")
        
        # 설정
        self.retriever_config = get_retriever_config()
        self.mcq_config = get_mcq_generation_config()
        self.mcq_types = get_mcq_types()
        self.prompt_templates = get_prompt_templates()
        
        if custom_config:
            self.retriever_config.update(custom_config)
        
        # 벡터 스토어 및 LLM
        self.vector_store = vector_store
        self.llm = llm
        
        # 유틸리티
        self.vector_search_utils = VectorSearchUtils()
        
        # 노드 초기화
        self._initialize_nodes()
        
        # 워크플로우 빌드
        self.workflow = self._build_workflow()
        
        # 히스토리
        self.mcq_history: List[Dict[str, Any]] = []
        
        self.logger.info("✅ ForgeMode 초기화 완료")
    
    def _initialize_nodes(self) -> None:
        """노드 함수 초기화 (팩토리 패턴)"""
        
        # select_part와 select_chapter 노드는 제거됨
        self.retrieve_documents = create_mcq_retrieve_documents_node(
            vector_store=self.vector_store,
            vector_search_utils=self.vector_search_utils,
            retriever_config=self.retriever_config,
            logger=self.logger,
        )
        self.format_context = create_mcq_format_context_node(self.logger)
        self.generate_mcq_node = create_mcq_generate_node(
            llm=self.llm,
            prompt_templates=self.prompt_templates,
            logger=self.logger,
        )
        self.validate_mcq = create_mcq_validate_node(self.logger)
        self.format_output = create_mcq_format_output_node(self.logger)
        
        self.logger.info("노드 함수 초기화 완료")
    
    def _build_workflow(self):
        """
        LangGraph 워크플로우 빌드 (간소화 버전)
        
        Returns:
            컴파일된 워크플로우
        """
        try:
            self.logger.info("MCQ 워크플로우 빌드 시작 (간소화 버전)")
            
            # 1. StateGraph 생성
            workflow = StateGraph(State)
            
            # 2. 노드 추가 (명시적 정의) - select_part와 select_chapter 제거됨
            workflow.add_node("retrieve_documents", self.retrieve_documents)
            workflow.add_node("format_context", self.format_context)
            workflow.add_node("generate_mcq", self.generate_mcq_node)
            workflow.add_node("validate_mcq", self.validate_mcq)
            workflow.add_node("format_output", self.format_output)
            
            # 3. 엣지 추가 (Edge 모듈에서 관리)
            build_mcq_workflow_edges(workflow)
            
            # 4. Checkpointer 생성 (상태 저장/복원 지원)
            checkpointer = MemorySaver()
            
            # 5. 워크플로우 컴파일 (Checkpointer 포함)
            compiled_workflow = workflow.compile(checkpointer=checkpointer)
            
            self.logger.info("✅ MCQ 워크플로우 빌드 완료 (간소화 버전, Checkpointer 활성화)")
            return compiled_workflow
            
        except Exception as e:
            self.logger.error(f"워크플로우 빌드 실패: {e}")
            raise RuntimeError(f"워크플로우 빌드 실패: {e}")
    
    # ==================== 공개 메서드 ====================
    
    def generate_mcq(
        self,
        topics_hierarchical: Dict[str, List[str]],
        topics_nested: Optional[Dict[str, Dict[str, Any]]] = None,
        user_topic: Optional[str] = None,
        max_retries: int = 6,
        category_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        MCQ 생성 (주제 기반 또는 랜덤)
        
        Args:
            topics_hierarchical: 전체 교재 구조
                예: {"Part 1": ["Ch1", "Ch2"], "Part 2": ["Ch1"]}
            topics_nested: 사용되지 않음 (하위 호환성 유지)
            user_topic: 사용자 입력 주제 (선택사항)
                예: "심폐소생술", "외상처치"
                None이면 랜덤 선택
            max_retries: 최대 재시도 횟수 (기본값: 6)
            category_weights: 카테고리별 가중치 (선택사항)
                예: {"SIMPLE": 0.3, "CASE_BASED": 0.4, "IMAGE_BASED": 0.3}
                None이면 기본값 사용
        
        Returns:
            생성된 MCQ (메타데이터 포함):
            - question: 질문
            - options: 4개의 보기
            - answer_index: 정답 인덱스 (1-4)
            - explanation: 해설
            - timestamp: 생성 시각
            - selected_part: 선택된 Part (주제 또는 랜덤)
            - selected_chapter: 선택된 Chapter
            - selected_topic: 검색 쿼리
        
        Raises:
            RuntimeError: MCQ 생성 실패 시
        
        예제:
            >>> # 주제 기반 생성
            >>> mcq = generator.generate_mcq(
            ...     topics_hierarchical=structure,
            ...     user_topic="심폐소생술"
            ... )
            
            >>> # 랜덤 생성
            >>> mcq = generator.generate_mcq(
            ...     topics_hierarchical=structure
            ... )
            
            >>> # 주제별 카테고리 가중치 적용
            >>> mcq = generator.generate_mcq(
            ...     topics_hierarchical=structure,
            ...     category_weights={"SIMPLE": 0.3, "CASE_BASED": 0.4}
            ... )
        """
        try:
            self.logger.info("MCQ 생성 시작 (LangGraph 워크플로우)")
            
            # Few-shot 예시 가져오기
            mcq_type = self.mcq_types.get("MCQ_GENERAL", {})
            few_shot_examples = mcq_type.get("few_shot_examples", [])
            category_examples = mcq_type.get("category_examples", {})
            instruction = mcq_type.get("instruction", "")
            max_few_shot = self.mcq_config.get("few_shot_max_examples", 5)
            
            # 카테고리 가중치: 전달받은 것이 있으면 사용, 없으면 기본값 사용
            if category_weights is not None:
                final_category_weights = category_weights
                self.logger.info(f"사용자 지정 카테고리 가중치 사용: {final_category_weights}")
            else:
                final_category_weights = self.mcq_config.get("default_category_weights", {})
                self.logger.info(f"기본 카테고리 가중치 사용: {final_category_weights}")
            
            # 초기 상태 생성
            initial_state = create_state(
                execution_mode="forge",
                user_topic=user_topic,  # 사용자 주제 전달
                topics_nested=topics_nested,
                topics_hierarchical=topics_hierarchical,
                instruction=instruction,
                few_shot_examples=few_shot_examples,
                category_examples=category_examples,
                category_weights=final_category_weights,
                max_few_shot_examples=max_few_shot,
                max_retries=max_retries,
            )
            
            # 워크플로우 실행
            config = {
                "configurable": {"thread_id": "mcq_generation"},
                "recursion_limit": 50  # 재시도를 고려하여 충분히 높게 설정
            }
            final_state = self.workflow.invoke(initial_state, config)
            
            # 결과 확인
            if final_state.get("final_mcq"):
                mcq = final_state["final_mcq"]
                
                # 히스토리에 추가
                self.mcq_history.append({
                    "timestamp": mcq["timestamp"],
                    "mcq": mcq.copy(),
                    "part": mcq["selected_part"],
                    "chapter": mcq["selected_chapter"],
                    "available_chapters": final_state.get("available_chapters", []),
                })
                
                self.logger.info("✅ MCQ 생성 완료")
                return mcq
            else:
                error_msg = final_state.get("error", "알 수 없는 오류")
                raise RuntimeError(f"MCQ 생성 실패: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"❌ MCQ 생성 실패: {e}", exc_info=True)
            raise RuntimeError(f"MCQ 생성 실패: {e}") from e
    
    def generate_mcq_batch(
        self,
        topics_hierarchical: Dict[str, List[str]],
        topics_nested: Optional[Dict[str, Dict[str, Any]]] = None,
        count: int = 5,
        max_retries: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        MCQ 배치 생성 (랜덤 주제, 중복 방지)
        
        Args:
            topics_hierarchical: 전체 교재 구조
            topics_nested: 사용되지 않음 (하위 호환성 유지)
            count: 생성할 MCQ 개수
            max_retries: 각 MCQ당 최대 재시도 횟수
        
        Returns:
            생성된 MCQ 리스트 (각각 랜덤 주제로 생성, 중복 최소화)
        
        예제:
            >>> # 전체 범위에서 랜덤하게 10개 생성 (중복 방지)
            >>> mcqs = generator.generate_mcq_batch(
            ...     topics_hierarchical=textbook_structure,
            ...     count=10
            ... )
            >>> for i, mcq in enumerate(mcqs, 1):
            ...     print(f"{i}. [{mcq['selected_part']}] {mcq['question']}")
        """
        mcqs = []
        recent_chapters = []  # 최근 생성된 Chapter 추적
        max_recent = 3  # 최근 3개 Chapter는 중복 방지
        
        # 진행 상황 헤더 출력
        self.logger.info("━" * 70)
        self.logger.info(f"MCQ 생성 진행 중... (0/{count})")
        self.logger.info("━" * 70)
        
        for i in range(count):
            try:
                # Few-shot 예시 가져오기
                mcq_type = self.mcq_types.get("MCQ_GENERAL", {})
                few_shot_examples = mcq_type.get("few_shot_examples", [])
                category_examples = mcq_type.get("category_examples", {})
                instruction = mcq_type.get("instruction", "")
                max_few_shot = self.mcq_config.get("few_shot_max_examples", 5)
                category_weights = self.mcq_config.get("category_weights", {})
                
                # 초기 상태 생성 (recent_chapters 포함)
                initial_state = create_state(
                    execution_mode="forge",
                    topics_nested=topics_nested,
                    topics_hierarchical=topics_hierarchical,
                    instruction=instruction,
                    few_shot_examples=few_shot_examples,
                    category_examples=category_examples,
                    category_weights=category_weights,
                    max_few_shot_examples=max_few_shot,
                    max_retries=max_retries,
                    recent_chapters=recent_chapters,  # 중복 방지용
                )
                
                # 워크플로우 실행
                config = {
                    "configurable": {"thread_id": f"mcq_batch_{i}"},
                    "recursion_limit": 50
                }
                final_state = self.workflow.invoke(initial_state, config)
                
                # 결과 확인
                if final_state.get("final_mcq"):
                    mcq = final_state["final_mcq"]
                    mcqs.append(mcq)
                    
                    # 생성된 Chapter 기록 (최근 N개만 유지)
                    chapter = mcq.get("selected_chapter", "")
                    part = mcq.get("selected_part", "")
                    
                    # Part 이름 간소화
                    part_short = part.replace("Part 0", "P").replace(": ", " ")
                    chapter_short = chapter.replace("Chapter ", "Ch")
                    
                    # Few-shot 카테고리 추정 (문제 형태)
                    question = mcq.get("question", "")
                    if "㉠" in question or "㉡" in question:
                        category = "복수형"
                    elif "<보기>" in question or "보기>" in question:
                        category = "보기형"
                    elif "「" in question and "」" in question:
                        category = "법률형"
                    elif len(question) > 200:
                        category = "상황형"
                    else:
                        category = "단순형"
                    
                    if chapter:
                        recent_chapters.append(chapter)
                        if len(recent_chapters) > max_recent:
                            recent_chapters.pop(0)  # 가장 오래된 것 제거
                    
                    # 진행 상황 로깅
                    self.logger.info("━" * 70)
                    self.logger.info(f"MCQ 생성 진행 중... ({len(mcqs)}/{count})")
                    self.logger.info("━" * 70)
                    
                    # 완료된 항목 로깅
                    for idx, completed_mcq in enumerate(mcqs, 1):
                        c_part = completed_mcq.get("selected_part", "").replace("Part 0", "P").replace(": ", " ")
                        c_chapter = completed_mcq.get("selected_chapter", "").replace("Chapter ", "Ch")
                        
                        # 카테고리 추정
                        c_q = completed_mcq.get("question", "")
                        if "㉠" in c_q or "㉡" in c_q:
                            c_cat = "복수형"
                        elif "<보기>" in c_q or "보기>" in c_q:
                            c_cat = "보기형"
                        elif "「" in c_q and "」" in c_q:
                            c_cat = "법률형"
                        elif len(c_q) > 200:
                            c_cat = "상황형"
                        else:
                            c_cat = "단순형"
                        
                        self.logger.info(f"✓ [{idx}] {c_cat:6s} | {c_part} - {c_chapter}")
                        self.logger.debug(f"   질문: {c_q[:80]}...")
                    
                    # 진행 중 표시
                    if len(mcqs) < count:
                        self.logger.info(f"□ [{len(mcqs)+1}] 생성 중...")
                    
                else:
                    error_msg = final_state.get("error", "알 수 없는 오류")
                    raise RuntimeError(f"MCQ 생성 실패: {error_msg}")
                    
            except Exception as e:
                self.logger.error(f"MCQ {i+1}/{count} 생성 실패: {e}")
                self.logger.warning(f"✗ [{i+1}] 생성 실패: {str(e)[:50]}...")
                # 실패해도 계속 진행
        
        # 완료 메시지
        self.logger.info("━" * 70)
        self.logger.info(f"✅ 배치 MCQ 생성 완료: {len(mcqs)}/{count}개 성공")
        self.logger.info("━" * 70)
        
        return mcqs
    
    def get_mcq_history(self) -> List[Dict[str, Any]]:
        """
        MCQ 생성 히스토리 반환
        
        Returns:
            MCQ 생성 히스토리 리스트 (최신순)
        
        예제:
            >>> history = generator.get_mcq_history()
            >>> print(f"총 {len(history)}개의 MCQ 생성됨")
        """
        return self.mcq_history.copy()
    
    def clear_mcq_history(self) -> None:
        """
        MCQ 생성 히스토리 초기화
        
        예제:
            >>> generator.clear_mcq_history()
            >>> print("히스토리가 초기화되었습니다")
        """
        count = len(self.mcq_history)
        self.mcq_history.clear()
        self.logger.info(f"MCQ 히스토리 초기화 완료 (총 {count}개 항목 삭제)")
    
    def get_mcq_statistics(self) -> Dict[str, Any]:
        """
        MCQ 생성 통계 반환
        
        Returns:
            통계 정보 딕셔너리:
            - total_count: 총 생성된 MCQ 개수
            - part_distribution: Part별 분포
            - latest_generation: 최근 생성 시각
        
        예제:
            >>> stats = generator.get_mcq_statistics()
            >>> print(f"총 {stats['total_count']}개 생성됨")
            >>> print(f"Part 분포: {stats['part_distribution']}")
        """
        total_count = len(self.mcq_history)
        
        # Part별 분포 계산
        part_distribution = {}
        for entry in self.mcq_history:
            part = entry.get("part", "Unknown")
            part_distribution[part] = part_distribution.get(part, 0) + 1
        
        # 최근 생성 시각
        latest_generation = None
        if self.mcq_history:
            latest_generation = self.mcq_history[-1]["timestamp"]
        
        return {
            "total_count": total_count,
            "part_distribution": part_distribution,
            "latest_generation": latest_generation,
        }


# ==================== 유틸리티 함수 ====================


def create_forge_mode(
    vector_store: VectorSearchVectorStore,
    llm: VertexAI,
    custom_config: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
) -> ForgeMode:
    """
    ForgeMode 생성 헬퍼 함수
    
    Args:
        vector_store: 벡터 스토어 객체
        llm: VertexAI LLM 객체
        custom_config: 사용자 정의 설정
        logger: 로거 객체
    
    Returns:
        초기화된 ForgeMode 인스턴스
    
    예제:
        >>> forge = create_forge_mode(
        ...     vector_store=my_vector_store,
        ...     llm=my_llm
        ... )
        >>> mcq = forge.generate_mcq(topics_hierarchical=topics)
    """
    return ForgeMode(
        vector_store=vector_store,
        llm=llm,
        custom_config=custom_config,
        logger=logger,
    )
