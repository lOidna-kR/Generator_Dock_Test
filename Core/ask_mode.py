"""
Ask Mode - RAG 질의응답 모드

주요 기능:
- LangGraph StateGraph를 사용한 명시적 워크플로우 정의
- 노드 기반 아키텍처 (retrieval, generation, formatting)
- 조건부 엣지를 통한 에러 핸들링
- Annotated State로 확장 가능한 구조
- Checkpointer를 통한 상태 저장/복원
- Streaming 지원

최신 LangGraph 권장 방식 100% 준수
"""

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Optional

from google.cloud import aiplatform
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import (
    VertexAI,
    VertexAIEmbeddings,
    VectorSearchVectorStore,
)
from langgraph.graph import END, START, StateGraph  # type: ignore
from langgraph.checkpoint.memory import MemorySaver  # type: ignore

# CompiledGraph 타입 정의 (LangGraph 0.2.0+)
try:
    from langgraph.graph import CompiledGraph  # type: ignore
except ImportError:
    # 구버전 또는 타입 미지원 시 Any 사용
    CompiledGraph = Any

# 로컬 모듈 import
try:
    from config import (  # type: ignore
        VERTEX_AI_CONFIG,
        get_gemini_model_config,
        get_generation_config,
        get_retriever_config,
    )
except ImportError:
    # 패키지로 설치된 경우를 위한 fallback
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from config import (  # type: ignore
        VERTEX_AI_CONFIG,
        get_gemini_model_config,
        get_generation_config,
        get_retriever_config,
    )

from Utils import (
    SystemInfoCollector,
    VectorSearchUtils,
    setup_logging,
)

# State, Node, Edge 모듈 import
from State import State
from Node import (
    create_route_question_node,
    create_retrieve_documents_node,
    create_format_context_node,
    create_generate_answer_node,
    create_format_output_node,
)
from Edge import build_workflow_edges


# ==================== LangGraph Generator ====================


class AskMode:
    """
    Ask Mode - RAG 질의응답
    
    특징:
    - StateGraph를 사용한 명시적 워크플로우
    - 노드 기반 아키텍처 (retrieval, generation, formatting)
    - 조건부 엣지를 통한 에러 핸들링
    - Annotated State로 멀티 소스 검색, 반복 개선 지원
    - Checkpointer로 상태 저장/복원
    - Streaming으로 실시간 응답
    
    사용 예제:
        # 기본 사용
        ask_mode = AskMode(vector_store=vector_store)
        result = ask_mode.process("응급의료기관의 종류는 무엇인가요?")
        print(result["answer"])
        
        # 스트리밍
        async for event in ask_mode.process_stream("질문"):
            print(event["node"], event["output"])
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorSearchVectorStore] = None,
        llm: Optional[VertexAI] = None,
        embeddings: Optional[VertexAIEmbeddings] = None,
        custom_config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        AskMode 초기화
        
        Args:
            vector_store: 벡터 스토어 객체
            llm: VertexAI LLM 객체 (선택사항)
            embeddings: VertexAIEmbeddings 객체 (선택사항)
            custom_config: 사용자 정의 설정
            logger: 로거 객체 (선택사항)
        """
        # 로깅 초기화
        self.logger = logger or setup_logging("Core.AskMode")
        
        # 설정 초기화
        self.retriever_config = get_retriever_config()
        if custom_config:
            self.retriever_config.update(custom_config)
        
        self.vertex_config = VERTEX_AI_CONFIG
        self.gemini_config = get_gemini_model_config()
        self.generation_config = get_generation_config()
        
        # Vertex AI 초기화
        self._initialize_vertex_ai(llm, embeddings)
        
        # 벡터 스토어 초기화
        self._initialize_vector_store(vector_store)
        
        # 유틸리티 클래스 초기화
        self.vector_search_utils = VectorSearchUtils()
        self.system_info_collector = SystemInfoCollector()
        
        # 프롬프트 템플릿 초기화
        self._initialize_prompt()
        
        # 노드 및 엣지 초기화
        self._initialize_nodes_and_edges()
        
        # LangGraph 워크플로우 빌드
        self.workflow = self._build_workflow()
        
        self.logger.info("✅ AskMode 초기화 완료")
    
    def _initialize_vertex_ai(
        self,
        llm: Optional[VertexAI] = None,
        embeddings: Optional[VertexAIEmbeddings] = None,
    ) -> None:
        """Vertex AI 초기화"""
        try:
            aiplatform.init(
                project=self.vertex_config["project"],
                location=self.vertex_config["location"],
            )
            
            # LLM 초기화
            if llm is not None:
                self.llm = llm
                self.logger.info("외부 LLM을 사용합니다.")
            else:
                self.llm = VertexAI(
                    model_name=self.gemini_config["model_name"],
                    project=self.vertex_config["project"],
                    location=self.vertex_config["location"],
                    temperature=self.retriever_config["llm_temperature"],
                    max_output_tokens=self.retriever_config["max_output_tokens"],
                )
                self.logger.info(f"LLM 초기화 완료: {self.gemini_config['model_name']}")
            
            # Embeddings 초기화
            self.embeddings = embeddings
            
            self.logger.info(
                f"Vertex AI 초기화 완료 (프로젝트: {self.vertex_config['project']})"
            )
            
        except Exception as e:
            self.logger.error(f"Vertex AI 초기화 실패: {e}")
            raise RuntimeError(f"Vertex AI 초기화 실패: {e}")
    
    def _initialize_vector_store(
        self, vector_store: Optional[VectorSearchVectorStore]
    ) -> None:
        """벡터 스토어 초기화"""
        if vector_store is not None:
            self.vector_store = vector_store
            self.logger.info("외부 벡터 스토어를 사용합니다.")
        else:
            self.logger.info("config 설정으로 벡터 스토어 생성 중...")
            
            # Embeddings 초기화 (아직 없다면)
            if not self.embeddings:
                embedding_dims = self.retriever_config.get("embedding_dimensions", 768)
                self.embeddings = VertexAIEmbeddings(
                    model_name=self.retriever_config["embedding_model"],
                    project=self.vertex_config["project"],
                    location=self.vertex_config["location"],
                )
                self.logger.info(f"Embeddings 초기화 완료 (차원: {embedding_dims})")
            
            # 설정에서 ID 가져오기
            index_id = self.retriever_config.get("index_id")
            endpoint_id = self.retriever_config.get("endpoint_id")
            gcs_bucket = self.retriever_config.get("gcs_bucket_name")
            
            if not all([index_id, endpoint_id, gcs_bucket]):
                raise ValueError(
                    "벡터 스토어 생성에 필요한 설정이 없습니다. "
                    "config.py에서 index_id, endpoint_id, gcs_bucket_name을 확인하세요."
                )
            
            # 벡터 스토어 생성
            self.vector_store = VectorSearchVectorStore.from_components(
                project_id=self.vertex_config["project"],
                region=self.vertex_config["region"],
                gcs_bucket_name=gcs_bucket,
                index_id=index_id,
                endpoint_id=endpoint_id,
                embedding=self.embeddings,
                stream_update=self.retriever_config.get("stream_update", False),
            )
            
            self.logger.info("벡터 스토어 자동 생성 완료")
    
    def _initialize_prompt(self) -> None:
        """프롬프트 템플릿 초기화"""
        rag_template = """당신은 응급의료 전문가입니다. 다음 참고 문서들을 바탕으로 질문에 정확하고 상세하게 답변해주세요.

참고 문서:
{context}

질문: {question}

답변 요구사항:
- 참고 문서의 내용을 기반으로 정확하게 답변하세요
- 출처를 명확히 밝혀주세요 (예: "문서의 X장 Y절에 따르면...")
- 불확실한 내용은 추측하지 말고 "문서에서 찾을 수 없습니다"라고 명시하세요
- 응급의료 분야의 전문성을 고려하여 답변하세요

답변:"""

        chat_template = """당신은 친절한 전문 어시스턴트입니다. 사용자의 질문에 자연스럽고 정확하게 답변하세요.

질문: {question}

원칙:
- 문서 검색 결과가 없으므로 일반 지식과 상식에 기반해 답변합니다.
- 불확실한 정보는 추측하지 말고 모른다고 답하세요.
"""

        self.prompt = ChatPromptTemplate.from_template(rag_template)
        self.chat_prompt = ChatPromptTemplate.from_template(chat_template)
        self.logger.info("프롬프트 템플릿 초기화 완료")
    
    # ==================== 노드 및 엣지 초기화 ====================
    
    def _initialize_nodes_and_edges(self) -> None:
        """
        노드 함수들을 초기화합니다.
        
        팩토리 패턴을 사용하여 각 노드를 생성합니다.
        각 노드는 자체적으로 에러를 처리하여 구조를 단순화합니다.
        
        엣지는 Edge 모듈에서 관리됩니다.
        """
        # 노드 함수 생성
        self.route_question = create_route_question_node(
            llm=self.llm,
            logger=self.logger,
        )

        self.retrieve_documents = create_retrieve_documents_node(
            vector_store=self.vector_store,
            vector_search_utils=self.vector_search_utils,
            retriever_config=self.retriever_config,
            logger=self.logger,
        )
        
        self.format_context = create_format_context_node(
            logger=self.logger,
        )
        
        self.generate_answer = create_generate_answer_node(
            llm=self.llm,
            rag_prompt=self.prompt,
            chat_prompt=self.chat_prompt,
            logger=self.logger,
        )
        
        self.format_output = create_format_output_node(
            logger=self.logger,
        )
        
        self.logger.info("노드 함수 초기화 완료")
    
    # ==================== 워크플로우 빌드 ====================
    
    def _build_workflow(self) -> CompiledGraph:
        """
        LangGraph 워크플로우를 빌드합니다.
        
        워크플로우 구조:
        START -> route_question -> (조건부) retrieve_documents -> format_context 
              -> generate_answer -> format_output -> END
        
        각 노드는 자체적으로 에러를 처리하여 
        조건부 분기 없이 선형적으로 진행합니다.
        
        엣지는 Edge 모듈에서 중앙 관리됩니다.
        
        Returns:
            컴파일된 CompiledGraph (상태 저장 지원)
            
        Note:
            최신 LangGraph 권장 방식:
            - START 사용 (set_entry_point 대신)
            - Checkpointer 추가 (상태 저장)
            - CompiledGraph 타입 명시
            - 각 노드의 자체 에러 처리로 구조 단순화
            - 엣지 로직을 Edge 모듈로 분리하여 중앙 관리
        """
        try:
            self.logger.info("LangGraph 워크플로우 빌드 시작")
            
            # 1. StateGraph 생성
            workflow = StateGraph(State)
            
            # 2. 노드 추가 (명시적 정의)
            workflow.add_node("route_question", self.route_question)
            workflow.add_node("retrieve_documents", self.retrieve_documents)
            workflow.add_node("format_context", self.format_context)
            workflow.add_node("generate_answer", self.generate_answer)
            workflow.add_node("format_output", self.format_output)
            
            # 3. 엣지 추가 (Edge 모듈에서 관리)
            build_workflow_edges(workflow)
            
            # 4. Checkpointer 생성 (상태 저장/복원 지원)
            checkpointer = MemorySaver()
            
            # 5. 워크플로우 컴파일 (Checkpointer 포함)
            compiled_workflow = workflow.compile(checkpointer=checkpointer)
            
            self.logger.info("✅ LangGraph 워크플로우 빌드 완료 (Checkpointer 활성화)")
            return compiled_workflow
            
        except Exception as e:
            self.logger.error(f"워크플로우 빌드 실패: {e}")
            raise RuntimeError(f"워크플로우 빌드 실패: {e}")
    
    # ==================== 공개 메서드 ====================
    
    def process(
        self, question: str, return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        질문 처리 통합 메서드
        
        Args:
            question: 처리할 질문
            return_sources: 출처 문서 포함 여부 (기본값: True)
        
        Returns:
            답변 및 출처 정보를 담은 딕셔너리:
            - question: 입력된 질문
            - answer: 생성된 답변
            - source_documents: 출처 문서 리스트 (return_sources=True인 경우)
            - num_sources: 출처 문서 수 (return_sources=True인 경우)
        
        예제:
            ask_mode = AskMode(vector_store=vector_store)
            result = ask_mode.process("응급의료기관의 종류는 무엇인가요?")
            print(result["answer"])
        """
        try:
            question_preview = (
                f"{question[:50]}..." if len(question) > 50 else question
            )
            self.logger.info(f"질문 처리 시작: '{question_preview}'")
            
            # 초기 상태 생성
            initial_state: State = {
                "question": question,
                "context": [],
                "formatted_context": "",
                "answer": "",
                "source_documents": [],
                "num_sources": 0,
                "error": None,
                "should_retry": False,
                "messages": [],
                "pipeline": "rag",
                "routing_reason": None,
            }
            
            # LangGraph 워크플로우 실행 (Checkpointer를 위한 config 추가)
            config = {"configurable": {"thread_id": "default"}}
            final_state = self.workflow.invoke(initial_state, config)
            
            # 결과 딕셔너리 생성
            result = {
                "question": final_state["question"],
                "answer": final_state["answer"],
                "pipeline": final_state.get("pipeline", "rag"),
                "routing_reason": final_state.get("routing_reason"),
            }
            
            # 출처 정보 포함
            if return_sources:
                result["source_documents"] = final_state["source_documents"]
                result["num_sources"] = final_state["num_sources"]
            
            self.logger.info(
                f"질문 처리 완료: {len(result['answer'])}자 답변 생성"
            )
            return result
            
        except Exception as e:
            self.logger.error(f"질문 처리 실패: {e}")
            raise RuntimeError(f"질문 처리 실패: {e}")
    
    async def process_stream(
        self, 
        question: str,
        thread_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        질문 처리 스트리밍 메서드 (실시간 응답)
        
        각 노드의 실행 결과를 실시간으로 스트리밍합니다.
        프론트엔드에서 진행 상황을 표시하거나, 
        긴 처리 시간에 대응할 때 유용합니다.
        
        Args:
            question: 처리할 질문
            thread_id: 대화 스레드 ID (상태 저장용, 선택사항)
        
        Yields:
            각 노드의 실행 결과를 포함한 딕셔너리:
            - node: 실행된 노드 이름
            - output: 노드의 출력 결과
            
        예제:
            async for event in ask_mode.process_stream("질문"):
                node = event.get("node")
                if node == "generate_answer":
                    answer = event["output"].get("answer")
                    print(f"답변: {answer}")
        
        Note:
            최신 LangGraph 권장 방식:
            - astream으로 실시간 스트리밍
            - thread_id로 대화 세션 관리
        """
        try:
            question_preview = (
                f"{question[:50]}..." if len(question) > 50 else question
            )
            self.logger.info(f"스트리밍 처리 시작: '{question_preview}'")
            
            # 초기 상태 생성
            initial_state: State = {
                "question": question,
                "context": [],
                "formatted_context": "",
                "answer": "",
                "source_documents": [],
                "num_sources": 0,
                "error": None,
                "should_retry": False,
                "messages": [],
                "pipeline": "rag",
                "routing_reason": None,
            }
            
            # config 설정 (thread_id가 있으면 상태 저장)
            config = {"configurable": {"thread_id": thread_id or "default"}}
            
            # LangGraph 워크플로우 스트리밍 실행
            async for event in self.workflow.astream(initial_state, config):
                # 각 노드의 실행 결과를 실시간으로 반환
                for node_name, node_output in event.items():
                    self.logger.debug(f"노드 '{node_name}' 실행 완료")
                    yield {
                        "node": node_name,
                        "output": node_output,
                    }
            
            self.logger.info("스트리밍 처리 완료")
            
        except Exception as e:
            self.logger.error(f"스트리밍 처리 실패: {e}")
            yield {
                "node": "error",
                "output": {
                    "error": f"스트리밍 처리 실패: {e}",
                    "answer": "",
                },
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        현재 시스템 정보를 반환합니다.
        
        Returns:
            시스템 정보 딕셔너리
        """
        return self.system_info_collector.get_system_info(
            vector_store=self.vector_store,
            workflow=self.workflow,
            llm_model=self.gemini_config["model_name"],
            config={
                "search_type": self.retriever_config["search_type"],
                "k": self.retriever_config["k"],
                "similarity_threshold": self.retriever_config[
                    "similarity_threshold"
                ],
            },
        )


# ==================== 유틸리티 함수 ====================


def create_ask_mode(
    vector_store: VectorSearchVectorStore,
    llm: Optional[VertexAI] = None,
    embeddings: Optional[VertexAIEmbeddings] = None,
    custom_config: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
) -> AskMode:
    """
    AskMode 생성 헬퍼 함수
    
    Args:
        vector_store: 사용할 벡터 스토어 객체
        llm: VertexAI LLM 객체 (선택사항)
        embeddings: VertexAIEmbeddings 객체 (선택사항)
        custom_config: 사용자 정의 설정
        logger: 로거 객체 (선택사항)
    
    Returns:
        초기화된 AskMode 인스턴스
    
    예제:
        ask_mode = create_ask_mode(vector_store)
        result = ask_mode.process("응급의료기관의 종류는?")
        print(result["answer"])
    """
    ask_mode = AskMode(
        vector_store=vector_store,
        llm=llm,
        embeddings=embeddings,
        custom_config=custom_config,
        logger=logger,
    )
    return ask_mode

