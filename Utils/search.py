"""
벡터 검색 유틸리티 모듈

주요 기능:
- VectorSearchUtils: 벡터 검색 유틸리티 및 통계 수집
"""

from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

# logging import
from .logging import setup_logging


class VectorSearchUtils:
    """벡터 검색 유틸리티 클래스"""

    def __init__(self):
        """VectorSearchUtils 초기화"""
        self.logger = setup_logging(__name__)

    def search_similar_documents(
        self, vector_store, query: str, k: int = 5, logger=None
    ) -> List[Document]:
        """
        벡터 스토어에서 유사한 문서를 검색합니다.

        Args:
            vector_store: 벡터 스토어 객체
            query: 검색 쿼리
            k: 반환할 문서 수
            logger: 로거 객체 (선택사항)

        Returns:
            유사 문서 리스트

        Raises:
            RuntimeError: 벡터 스토어가 설정되지 않은 경우
        """
        if logger is None:
            logger = self.logger

        if not vector_store:
            error_msg = "벡터 스토어가 설정되지 않았습니다."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            results = vector_store.similarity_search(query, k=k)
            logger.info(f"'{query}'에 대해 {len(results)}개 문서를 찾았습니다.")
            return results

        except Exception as e:
            error_msg = f"벡터 검색 실패: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def search_with_score_threshold(
        self,
        vector_store,
        query: str,
        k: int = 5,
        score_threshold: float = 0.7,
        logger=None,
    ) -> List[Document]:
        """
        점수 임계값을 적용하여 벡터 검색을 수행합니다.

        Args:
            vector_store: 벡터 스토어 객체
            query: 검색 쿼리
            k: 반환할 문서 수
            score_threshold: 점수 임계값 (0.0 ~ 1.0)
            logger: 로거 객체 (선택사항)

        Returns:
            임계값을 통과한 유사 문서 리스트
        """
        if logger is None:
            logger = self.logger

        if not vector_store:
            error_msg = "벡터 스토어가 설정되지 않았습니다."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # similarity_search_with_score 사용 (지원되는 경우)
            if hasattr(vector_store, "similarity_search_with_score"):
                results_with_scores = vector_store.similarity_search_with_score(
                    query, k=k
                )

                # 점수 임계값 필터링
                filtered_results = [
                    doc for doc, score in results_with_scores if score >= score_threshold
                ]

                logger.info(
                    f"'{query}'에 대해 {len(filtered_results)}개 문서를 찾았습니다. "
                    f"(임계값: {score_threshold})"
                )
                return filtered_results
            else:
                # fallback: 일반 검색 후 상위 결과만 반환
                results = self.search_similar_documents(vector_store, query, k, logger)
                return results

        except Exception as e:
            error_msg = f"점수 임계값 벡터 검색 실패: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def validate_vector_store(self, vector_store, logger=None) -> Dict[str, Any]:
        """
        벡터 스토어의 상태를 검증합니다.

        Args:
            vector_store: 검증할 벡터 스토어 객체
            logger: 로거 객체 (선택사항)

        Returns:
            검증 결과 딕셔너리
        """
        if logger is None:
            logger = self.logger

        validation_result = {
            "is_valid": False,
            "error": None,
            "test_query": None,
            "test_results_count": 0,
        }

        try:
            if not vector_store:
                validation_result["error"] = "벡터 스토어가 None입니다."
                return validation_result

            # 테스트 검색 수행
            test_query = "test validation query"
            test_results = vector_store.similarity_search(test_query, k=1)

            validation_result.update(
                {
                    "is_valid": True,
                    "test_query": test_query,
                    "test_results_count": len(test_results),
                }
            )

            logger.debug("벡터 스토어 검증 성공")

        except Exception as e:
            validation_result["error"] = str(e)
            logger.error(f"벡터 스토어 검증 실패: {e}")

        return validation_result

    def get_search_statistics(
        self, vector_store, queries: List[str], k: int = 5, logger=None
    ) -> Dict[str, Any]:
        """
        여러 쿼리에 대한 검색 통계를 수집합니다.

        Args:
            vector_store: 벡터 스토어 객체
            queries: 검색할 쿼리 리스트
            k: 각 쿼리당 반환할 문서 수
            logger: 로거 객체 (선택사항)

        Returns:
            검색 통계 딕셔너리
        """
        if logger is None:
            logger = self.logger

        stats = {
            "total_queries": len(queries),
            "successful_queries": 0,
            "failed_queries": 0,
            "total_documents_found": 0,
            "average_documents_per_query": 0,
            "query_results": [],
        }

        try:
            for i, query in enumerate(queries):
                try:
                    results = self.search_similar_documents(vector_store, query, k, logger)
                    stats["successful_queries"] += 1
                    stats["total_documents_found"] += len(results)

                    stats["query_results"].append(
                        {
                            "query": query,
                            "result_count": len(results),
                            "status": "success",
                        }
                    )

                except Exception as e:
                    stats["failed_queries"] += 1
                    stats["query_results"].append(
                        {
                            "query": query,
                            "result_count": 0,
                            "status": "failed",
                            "error": str(e),
                        }
                    )

            # 평균 계산
            if stats["successful_queries"] > 0:
                stats["average_documents_per_query"] = (
                    stats["total_documents_found"] / stats["successful_queries"]
                )

            logger.info(
                f"검색 통계 수집 완료: "
                f"{stats['successful_queries']}/{stats['total_queries']} 성공"
            )

        except Exception as e:
            logger.error(f"검색 통계 수집 실패: {e}")
            stats["error"] = str(e)

        return stats

