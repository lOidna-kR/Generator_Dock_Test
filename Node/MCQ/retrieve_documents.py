"""
MCQ용 문서 검색 노드 (랜덤 주제 선택 + Reranking)

전체 교재 구조에서 랜덤하게 Part와 Chapter를 선택하여 벡터 검색을 수행합니다.
Cross-Encoder Reranking을 통해 가장 관련성 높은 문서만 선택합니다.
"""

import logging
import random
import hashlib
from typing import TYPE_CHECKING, List

from Utils import create_error_handler

if TYPE_CHECKING:
    from langchain_google_vertexai import VectorSearchVectorStore
    from Utils import VectorSearchUtils
    from State import State
    from langchain_core.documents import Document

# Reranking을 위한 Cross-Encoder (lazy loading)
_reranker = None

def get_reranker():
    """Cross-Encoder 모델을 lazy loading으로 가져옵니다."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
        except ImportError as e:
            # sentence-transformers가 없으면 None 반환 (Reranking 건너뜀)
            print(f"⚠️  sentence-transformers 미설치: {e}")
            _reranker = "not_available"
        except Exception as e:
            # 기타 에러 (모델 로드 실패 등)
            print(f"⚠️  Reranker 초기화 실패: {e}")
            _reranker = "not_available"
    
    return _reranker if _reranker != "not_available" else None


def get_document_id(doc: "Document") -> str:
    """
    문서의 고유 ID를 생성합니다.
    
    Args:
        doc: Document 객체
    
    Returns:
        문서 ID (metadata의 고유 ID 또는 내용 해시값)
    """
    # metadata에 고유 ID가 있으면 사용
    if hasattr(doc, 'metadata') and doc.metadata:
        doc_id = doc.metadata.get('id') or doc.metadata.get('document_id')
        if doc_id:
            return str(doc_id)
    
    # metadata에 title과 page_number 조합 사용
    if hasattr(doc, 'metadata') and doc.metadata:
        title = doc.metadata.get('title', '')
        page = doc.metadata.get('page_number', '')
        if title and page:
            return f"{title}_{page}"
    
    # 내용 기반 해시값 생성 (fallback)
    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
    doc_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    return f"hash_{doc_hash}"


def build_section_id(doc: "Document") -> str:
    """문서 메타데이터를 활용해 섹션 ID를 생성합니다."""
    metadata = doc.metadata if hasattr(doc, "metadata") and doc.metadata else {}
    base_id = get_document_id(doc)
    title = metadata.get("title", "")
    chapter = metadata.get("chapter", "")
    section = metadata.get("section", "")
    page = metadata.get("page_number", "")
    part = metadata.get("part", "")
    elements = [base_id, part, chapter, section, str(page), title]
    return "|".join(str(elem).strip() for elem in elements if str(elem).strip())


def rerank_documents(
    query: str,
    documents: List["Document"],
    top_k: int = 3,
    logger: logging.Logger = None
) -> List["Document"]:
    """
    Cross-Encoder를 사용하여 문서를 재순위화합니다.
    
    Args:
        query: 검색 쿼리
        documents: 재순위화할 문서 리스트
        top_k: 반환할 상위 문서 개수
        logger: 로거 객체
    
    Returns:
        재순위화된 상위 문서 리스트
    """
    if not documents:
        return documents
    
    if len(documents) <= top_k:
        return documents
    
    # Reranker 가져오기
    reranker = get_reranker()
    if reranker is None:
        if logger:
            logger.warning("⚠️  sentence-transformers 미설치. Reranking 건너뜀")
        return documents[:top_k]
    
    try:
        # Query-Document 쌍 생성
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Cross-Encoder로 점수 계산
        scores = reranker.predict(pairs)
        
        # 점수 기준 정렬
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 K개 반환
        reranked_docs = [doc for doc, score in doc_scores[:top_k]]
        
        if logger:
            logger.info(f"✅ Reranking 완료: {len(documents)}개 → {len(reranked_docs)}개")
        
        return reranked_docs
        
    except Exception as e:
        if logger:
            logger.error(f"❌ Reranking 실패: {e}. 원본 문서 반환")
        return documents[:top_k]


def create_mcq_retrieve_documents_node(
    vector_store: "VectorSearchVectorStore",
    vector_search_utils: "VectorSearchUtils",
    retriever_config: dict,
    logger: logging.Logger,
):
    """
    MCQ용 문서 검색 노드를 생성하는 팩토리 함수 (랜덤 주제 선택)
    
    Args:
        vector_store: 벡터 스토어 객체
        vector_search_utils: 벡터 검색 유틸리티
        retriever_config: Retriever 설정
        logger: 로거 객체
    
    Returns:
        문서 검색 노드 함수
    """
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger)
    
    # MCQ 설정에서 Part 가중치 가져오기
    from config import get_mcq_generation_config
    mcq_config = get_mcq_generation_config()
    part_weights = mcq_config.get("part_weights", {})
    
    def retrieve_documents(state: "State") -> dict:
        """
        노드 1: 랜덤 주제 선택 및 문서 검색
        
        전체 교재 구조에서 랜덤하게 Part와 Chapter를 선택하여 검색합니다.
        
        Args:
            state: State
        
        Returns:
            업데이트할 필드:
            - selected_part: 선택된 Part
            - selected_chapter: 선택된 Chapter
            - selected_topic_query: 검색 쿼리
            - retrieved_documents: 검색된 문서 리스트
            - num_documents: 문서 수
            - error: 에러 메시지
            - should_retry: 재시도 여부
        """
        try:
            # 0. 사용자 주제 확인 (최우선)
            user_topic = state.get("user_topic")
            
            if user_topic:
                # 사용자가 주제를 입력한 경우
                logger.info(f"사용자 입력 주제로 검색: '{user_topic}'")
                query = user_topic
                
                # 벡터 검색 수행
                initial_k = retriever_config.get("initial_k", 10)
                k = retriever_config.get("k", 3)
                logger.debug(f"주제 기반 검색: '{query}', initial_k={initial_k}, final_k={k}")
                
                documents = vector_search_utils.search_similar_documents(
                    vector_store, query, initial_k, logger
                )
                
                # 주제 기반 필터링 (Part/Chapter 키워드 포함)
                if documents and user_topic:
                    # 사용자 주제에 Part/Chapter 키워드가 있으면 필터링
                    filtered_docs = []
                    for doc in documents:
                        metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                        part = metadata.get('part', '')
                        chapter = metadata.get('chapter', '')
                        
                        # 주제가 Part나 Chapter에 포함되어 있는지 확인
                        if (user_topic.lower() in part.lower() or 
                            user_topic.lower() in chapter.lower()):
                            filtered_docs.append(doc)
                    
                    # 필터링 결과가 있으면 사용
                    if filtered_docs:
                        logger.info(f"주제 필터링: {len(documents)}개 → {len(filtered_docs)}개 ('{user_topic}' 포함)")
                        documents = filtered_docs
                    else:
                        logger.info(f"주제 필터링 결과 없음. 전체 검색 결과 사용")
                
                if not documents:
                    # 주제로 검색 실패 시 랜덤으로 fallback
                    logger.warning(f"'{query}' 주제로 검색 결과 없음. 랜덤 선택으로 전환")
                    user_topic = None  # 랜덤 모드로 전환
                else:
                    # 문서 메타데이터에서 Part/Chapter 추출 (다수결 방식)
                    part_counts = {}
                    chapter_counts = {}
                    
                    for doc in documents:
                        metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                        part = metadata.get('part', 'N/A')
                        chapter = metadata.get('chapter', 'N/A')
                        
                        part_counts[part] = part_counts.get(part, 0) + 1
                        chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
                    
                    # 가장 많이 나온 Part/Chapter 선택
                    selected_part = max(part_counts, key=part_counts.get) if part_counts else 'N/A'
                    selected_chapter = max(chapter_counts, key=chapter_counts.get) if chapter_counts else 'N/A'
                    
                    logger.info(f"주제 검색 성공: {len(documents)}개 문서 발견")
                    logger.info(f"추출된 범위 (다수결): {selected_part} - {selected_chapter}")
                    logger.debug(f"Part 분포: {part_counts}")
                    logger.debug(f"Chapter 분포: {chapter_counts}")
                    
                    # 최근 사용 문서 제외하여 다양성 보장
                    recent_doc_ids = state.get("recent_document_ids", [])
                    if recent_doc_ids:
                        filtered_documents = []
                        for doc in documents:
                            doc_id = get_document_id(doc)
                            if doc_id not in recent_doc_ids:
                                filtered_documents.append(doc)
                        
                        if len(filtered_documents) >= k:
                            documents = filtered_documents
                            logger.info(f"   최근 사용 문서 {len(recent_doc_ids)}개 제외: {len(documents)}개 문서 유지")
                        else:
                            logger.info(f"   최근 사용 문서 제외 후 {len(filtered_documents)}개만 남음, 전체 사용")
                            # 필터링 결과가 k개 미만이면 전체 문서 사용 (다양성보다 품질 우선)
                    
                    # 랜덤 샘플링 (다양성 극대화)
                    if len(documents) > k:
                        original_count = len(documents)
                        documents = random.sample(documents, k)
                        logger.info(f"✅ 랜덤 선택: {original_count}개 → {k}개 (다양성 우선)")
                    else:
                        logger.info(f"   랜덤 선택 건너뜀 (문서 {len(documents)}개 ≤ {k}개)")
                    
                    section_ids = [build_section_id(doc) for doc in documents]
                    document_ids = [get_document_id(doc) for doc in documents]
                    
                    # 중복 방지: 최근 5개만 추적 (완화된 정책)
                    used_sections_all = state.get("used_section_ids", [])
                    used_docs_all = state.get("used_document_ids", [])
                    
                    # 최근 5개만 사용 (나머지는 재사용 허용)
                    used_sections = set(used_sections_all[-5:]) if used_sections_all else set()
                    used_docs = set(used_docs_all[-5:]) if used_docs_all else set()

                    if used_sections or used_docs:
                        filtered_triplets = [
                            (doc, doc_id, section_id)
                            for doc, doc_id, section_id in zip(documents, document_ids, section_ids)
                            if section_id not in used_sections and doc_id not in used_docs
                        ]

                        # 필터링 후 문서가 충분하면 사용, 부족하면 필터링 무시
                        min_required = max(3, k // 2)  # 최소 3개 또는 k의 절반
                        
                        if len(filtered_triplets) >= min_required:
                            documents = [triplet[0] for triplet in filtered_triplets]
                            document_ids = [triplet[1] for triplet in filtered_triplets]
                            section_ids = [triplet[2] for triplet in filtered_triplets]
                            logger.info(f"   중복 제거: {len(documents)}개 (최근 5개 제외)")
                        else:
                            logger.info(f"   중복 제거 건너뜀 (필터링 후 {len(filtered_triplets)}개 < {min_required}개)")
                            # 필터링하지 않고 원본 사용 (다양성보다 문서 수 우선)

                    # recent_document_ids 업데이트
                    return_fields = {
                        "selected_part": selected_part,
                        "selected_chapter": selected_chapter,
                        "selected_topic_query": query,
                        "retrieved_documents": documents,
                        "num_documents": len(documents),
                    }
                    
                    if documents:
                        updated_recent_ids = (recent_doc_ids + document_ids)[-20:]  # 최근 20개만 유지
                        return_fields["recent_document_ids"] = updated_recent_ids
                        return_fields["context_document_ids"] = document_ids
                        return_fields["context_section_ids"] = section_ids
                    else:
                        return_fields["context_document_ids"] = []
                        return_fields["context_section_ids"] = []
                    
                    # 성공 처리 (early return)
                    return error_handler.handle_success(
                        node_name="retrieve_documents",
                        message=f"주제 '{user_topic}' 문서 {len(documents)}개 검색 완료",
                        return_fields=return_fields
                    )
            
            # 1. 교재 구조 가져오기 (랜덤 모드)
            topics_hierarchical = state.get("topics_hierarchical", {})
            
            if not topics_hierarchical:
                raise ValueError("교재 구조가 없습니다 (topics_hierarchical 필요)")
            
            # 2. Chapter 가중치 설정 가져오기
            chapter_weights_config = mcq_config.get("chapter_weights", {})
            
            # 3. Part와 Chapter를 동일한 레벨에서 선택
            # Part/Chapter 통합 선택 목록 생성
            selection_options = {}  # {name: weight, ...}
            part_to_chapters = {}   # {part: [chapters], ...}
            
            for part, chapters in topics_hierarchical.items():
                # Part에 chapter_weights가 정의되어 있는지 확인
                if part in chapter_weights_config:
                    # Chapter별로 개별 가중치 적용 (전체 비율)
                    part_chapter_weights = chapter_weights_config[part]
                    for chapter in chapters:
                        weight = part_chapter_weights.get(chapter, 1.0)
                        selection_options[chapter] = weight
                        if chapter not in part_to_chapters:
                            part_to_chapters[chapter] = part
                    logger.debug(f"Part '{part}': Chapter별 개별 가중치 적용")
                else:
                    # Part 전체 가중치 사용
                    part_weight = part_weights.get(part, 1.0)
                    selection_options[part] = part_weight
                    part_to_chapters[part] = part
                    logger.debug(f"Part '{part}': 전체 가중치 {part_weight}")
            
            if not selection_options:
                raise ValueError("선택 가능한 Part/Chapter가 없습니다")
            
            # 4. 가중치 기반 랜덤 선택
            names = list(selection_options.keys())
            weights = list(selection_options.values())
            
            logger.debug(f"선택 옵션 ({len(names)}개): {dict(zip(names, weights))}")
            
            selected_name = random.choices(names, weights=weights, k=1)[0]
            
            # 5. 선택된 것이 Part인지 Chapter인지 판단
            if selected_name in topics_hierarchical:
                # Part가 선택됨 → Chapter 가중치 기반 선택
                selected_part = selected_name
                chapters = topics_hierarchical[selected_part]
                
                if not chapters:
                    raise ValueError(f"Part '{selected_part}'에 Chapter가 없습니다")
                
                # Chapter 가중치 확인
                chapter_weights_for_part = chapter_weights_config.get(selected_part, {})
                
                if chapter_weights_for_part:
                    # Chapter 가중치 적용
                    recent_chapters = state.get("recent_chapters", [])
                    available_chapters = [ch for ch in chapters if ch not in recent_chapters]
                    
                    if not available_chapters:
                        available_chapters = chapters
                    
                    chapter_weights_list = [
                        chapter_weights_for_part.get(ch, 1.0) for ch in available_chapters
                    ]
                    
                    selected_chapter = random.choices(available_chapters, weights=chapter_weights_list, k=1)[0]
                    logger.info(f"Part '{selected_part}' 선택 → Chapter '{selected_chapter}' (가중치 적용)")
                else:
                    # Chapter 가중치 없으면 균등 선택
                    recent_chapters = state.get("recent_chapters", [])
                    available_chapters = [ch for ch in chapters if ch not in recent_chapters]
                    
                    if available_chapters:
                        selected_chapter = random.choice(available_chapters)
                        logger.info(f"Part '{selected_part}' 선택 → Chapter '{selected_chapter}' (균등 선택)")
                    else:
                        selected_chapter = random.choice(chapters)
                        logger.info(f"Part '{selected_part}' 선택 → Chapter '{selected_chapter}' (전체 재사용)")
            else:
                # Chapter가 직접 선택됨
                selected_chapter = selected_name
                selected_part = part_to_chapters.get(selected_chapter, "N/A")
                logger.info(f"✅ Chapter 직접 선택 (가중치): '{selected_chapter}' (Part: {selected_part})")
            
            # 6. 검색 쿼리 생성
            if selected_part and selected_part != "N/A":
                query = f"{selected_part} - {selected_chapter}"
            else:
                query = selected_chapter
            logger.info(f"검색 쿼리: '{query}'")
            
            # 7. 벡터 검색 수행 (초기 검색)
            initial_k = retriever_config.get("initial_k", 10)  # Reranking 전 초기 검색 개수
            k = retriever_config.get("k", 3)  # 최종 반환할 개수
            logger.debug(f"검색 파라미터: initial_k={initial_k}, final_k={k}")
            
            documents = vector_search_utils.search_similar_documents(
                vector_store, query, initial_k, logger
            )
            
            if not documents:
                # 검색 결과 없음 에러 (복구 가능)
                return error_handler.handle_error(
                    error=ValueError(f"검색 결과 없음: {query}"),
                    state=state,
                    node_name="retrieve_documents",
                    recoverable=True,
                    return_fields={
                        "selected_part": selected_part,
                        "selected_chapter": selected_chapter,
                        "selected_topic_query": query,
                        "retrieved_documents": [],
                        "num_documents": 0,
                                    "context_document_ids": [],
                        "context_document_ids": [],
                        "context_section_ids": [],
                    }
                )
            
            logger.info(f"✅ 초기 문서 검색 완료: {len(documents)}개 문서 발견")
            
            # 7-1. 최근 사용 문서 제외하여 다양성 보장
            recent_doc_ids = state.get("recent_document_ids", [])
            if recent_doc_ids:
                filtered_documents = []
                for doc in documents:
                    doc_id = get_document_id(doc)
                    if doc_id not in recent_doc_ids:
                        filtered_documents.append(doc)
                
                if len(filtered_documents) >= k:
                    documents = filtered_documents
                    logger.info(f"   최근 사용 문서 {len(recent_doc_ids)}개 제외: {len(documents)}개 문서 유지")
                else:
                    logger.info(f"   최근 사용 문서 제외 후 {len(filtered_documents)}개만 남음, 전체에서 재검색")
                    # 필터링 결과가 k개 미만이면 전체 문서 사용 (다양성보다 품질 우선)
            
            # 8. 랜덤 샘플링 (다양성 극대화)
            if len(documents) > k:
                original_count = len(documents)
                documents = random.sample(documents, k)
                logger.info(f"✅ 랜덤 선택: {original_count}개 → {k}개 (다양성 우선)")
            else:
                logger.info(f"   랜덤 선택 건너뜀 (문서 {len(documents)}개 ≤ {k}개)")
            
            section_ids = [build_section_id(doc) for doc in documents]
            document_ids = [get_document_id(doc) for doc in documents]
            
            # 중복 방지: 최근 5개만 추적 (완화된 정책)
            used_sections_all = state.get("used_section_ids", [])
            used_docs_all = state.get("used_document_ids", [])
            
            # 최근 5개만 사용 (나머지는 재사용 허용)
            used_sections = set(used_sections_all[-5:]) if used_sections_all else set()
            used_docs = set(used_docs_all[-5:]) if used_docs_all else set()

            if used_sections or used_docs:
                filtered_triplets = [
                    (doc, doc_id, section_id)
                    for doc, doc_id, section_id in zip(documents, document_ids, section_ids)
                    if section_id not in used_sections and doc_id not in used_docs
                ]

                # 필터링 후 문서가 충분하면 사용, 부족하면 필터링 무시
                min_required = max(3, k // 2)  # 최소 3개 또는 k의 절반
                
                if len(filtered_triplets) >= min_required:
                    documents = [triplet[0] for triplet in filtered_triplets]
                    document_ids = [triplet[1] for triplet in filtered_triplets]
                    section_ids = [triplet[2] for triplet in filtered_triplets]
                    logger.info(f"   중복 제거: {len(documents)}개 (최근 5개 제외)")
                else:
                    logger.info(f"   중복 제거 건너뜀 (필터링 후 {len(filtered_triplets)}개 < {min_required}개)")
                    # 필터링하지 않고 원본 사용 (다양성보다 문서 수 우선)

            # 8-1. 검색된 문서 ID를 recent_document_ids에 추가 (순환 큐 방식, 최대 20개)
            return_fields = {
                "selected_part": selected_part,
                "selected_chapter": selected_chapter,
                "selected_topic_query": query,
                "retrieved_documents": documents,
                "num_documents": len(documents),
            }
            
            if documents:
                updated_recent_ids = (recent_doc_ids + document_ids)[-20:]  # 최근 20개만 유지
                return_fields["recent_document_ids"] = updated_recent_ids
                return_fields["context_document_ids"] = document_ids
                return_fields["context_section_ids"] = section_ids
            else:
                return_fields["context_document_ids"] = []
                return_fields["context_section_ids"] = []
            
            return error_handler.handle_success(
                node_name="retrieve_documents",
                message=f"'{selected_chapter}' 문서 {len(documents)}개 검색 완료",
                return_fields=return_fields
            )
            
        except Exception as e:
            # 예외 처리 (복구 가능)
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="retrieve_documents",
                recoverable=True,
                custom_message="문서 검색 실패",
                return_fields={
                    "retrieved_documents": [],
                    "num_documents": 0,
                    "context_document_ids": [],
                    "context_section_ids": [],
                }
            )
    
    return retrieve_documents

