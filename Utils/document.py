"""
문서 처리 유틸리티 모듈

주요 기능:
- format_documents_for_llm: 문서를 LLM이 이해하기 쉽게 포맷팅
- extract_texts_and_metadatas_from_documents: 문서에서 텍스트와 메타데이터 추출
"""

from typing import List, Dict, Any, Tuple

from langchain_core.documents import Document


def format_documents_for_llm(
    docs: List[Document], include_metadata: bool = True
) -> str:
    """
    검색된 문서들을 LLM이 이해하기 쉽게 포맷팅합니다.

    Args:
        docs: Document 객체 리스트
        include_metadata: 메타데이터 포함 여부

    Returns:
        포맷팅된 문서 문자열

    예제:
        formatted = format_documents_for_llm(documents)
        print(formatted)
    """
    if not docs:
        return ""

    formatted = []
    for i, doc in enumerate(docs):
        if include_metadata:
            metadata = doc.metadata
            source = (
                f"{metadata.get('chapter', 'N/A')} > "
                f"{metadata.get('section', 'N/A')}"
            )
            page = metadata.get("page_number", "N/A")

            formatted.append(
                f"[문서 {i+1}] (출처: {source}, 페이지: {page})\n"
                f"{doc.page_content}"
            )
        else:
            formatted.append(f"[문서 {i+1}]\n{doc.page_content}")

    return "\n\n".join(formatted)


def extract_texts_and_metadatas_from_documents(
    documents: List[Document],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    문서 리스트에서 텍스트와 메타데이터를 추출합니다.

    Args:
        documents: Document 객체 리스트

    Returns:
        (texts, metadatas) 튜플

    예제:
        texts, metadatas = extract_texts_and_metadatas_from_documents(docs)
    """
    texts = [doc.page_content for doc in documents]
    metadatas = [doc.metadata or {} for doc in documents]
    return texts, metadatas

