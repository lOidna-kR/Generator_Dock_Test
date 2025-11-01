"""
파일 처리 유틸리티 모듈

주요 기능:
- FileProcessor: 싱글톤 패턴으로 파일 I/O 최적화, 캐시 지원
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from langchain_core.documents import Document

# config import (fallback 메커니즘 사용)
try:
    from config import FILE_PROCESSING_CONFIG, OUTPUT_CONFIG
except ImportError:
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from config import FILE_PROCESSING_CONFIG, OUTPUT_CONFIG

# logging import
from .logging import setup_logging


class FileProcessor:
    """파일 처리 유틸리티 클래스 (싱글톤)"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(FileProcessor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """FileProcessor 초기화 (싱글톤)"""
        if FileProcessor._initialized:
            return

        self.file_config = FILE_PROCESSING_CONFIG
        self.output_config = OUTPUT_CONFIG
        self.logger = setup_logging(__name__)

        # 성능 최적화를 위한 캐시 설정
        self._file_cache: Dict[str, str] = {}
        self._cache_max_size = 100
        self._cache_enabled = True

        FileProcessor._initialized = True

    def read_file(self, file_path: str, use_cache: bool = True) -> Optional[str]:
        """파일에서 텍스트를 읽어옵니다. (캐시 지원)"""
        try:
            file_path = Path(file_path)
            file_path_str = str(file_path.absolute())

            # 캐시 확인
            if (
                self._cache_enabled
                and use_cache
                and file_path_str in self._file_cache
            ):
                self.logger.debug(f"캐시에서 파일 읽기: {file_path}")
                return self._file_cache[file_path_str]

            # 파일 존재 확인
            if not file_path.exists():
                self.logger.error(f"파일을 찾을 수 없습니다: {file_path}")
                return None

            # 파일 크기 확인
            file_size = file_path.stat().st_size
            if file_size > self.file_config["max_file_size"]:
                self.logger.warning(
                    f"파일이 너무 큽니다 ({file_size} bytes): {file_path}"
                )
                return None

            # 파일 확장자 확인
            if (
                file_path.suffix.lower()
                not in self.file_config["supported_extensions"]
            ):
                self.logger.warning(
                    f"지원하지 않는 파일 형식입니다: {file_path.suffix}"
                )
                return None

            # 파일 읽기
            with open(file_path, "r", encoding=self.file_config["encoding"]) as f:
                text = f.read()

            # 캐시에 저장
            if self._cache_enabled and use_cache:
                self._manage_cache(file_path_str, text)

            self.logger.info(f"파일 읽기 성공: {file_path}")
            return text

        except Exception as e:
            self.logger.error(f"파일 읽기 중 오류 발생 ({file_path}): {e}")
            return None

    def _manage_cache(self, file_path: str, content: str) -> None:
        """캐시 관리를 수행합니다."""
        if len(self._file_cache) >= self._cache_max_size:
            oldest_key = next(iter(self._file_cache))
            del self._file_cache[oldest_key]

        self._file_cache[file_path] = content

    def clear_cache(self) -> None:
        """파일 캐시를 초기화합니다."""
        self._file_cache.clear()
        self.logger.info("파일 캐시가 초기화되었습니다.")

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계를 반환합니다."""
        return {
            "cache_size": len(self._file_cache),
            "cache_max_size": self._cache_max_size,
            "cache_enabled": self._cache_enabled,
            "cached_files": list(self._file_cache.keys()),
        }

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """파일 메타데이터를 생성합니다."""
        try:
            file_path = Path(file_path)

            try:
                file_size = file_path.stat().st_size if file_path.exists() else 0
            except (OSError, PermissionError) as e:
                self.logger.warning(
                    f"파일 크기 정보를 가져올 수 없습니다 ({file_path}): {e}"
                )
                file_size = 0

            return {
                "source_file": str(file_path),
                "file_name": file_path.name,
                "file_size": file_size,
                "file_extension": file_path.suffix,
                "processed_at": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"메타데이터 생성 중 오류 발생 ({file_path}): {e}")
            return {
                "source_file": str(file_path),
                "file_name": Path(file_path).name if file_path else "unknown",
                "file_size": 0,
                "file_extension": Path(file_path).suffix if file_path else "",
                "processed_at": datetime.now().isoformat(),
                "error": str(e),
            }

    def find_files_in_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        file_patterns: Optional[List[str]] = None,
    ) -> List[str]:
        """디렉토리에서 파일 목록을 찾습니다."""
        try:
            directory_path = Path(directory_path)

            if not directory_path.exists():
                self.logger.error(f"디렉토리를 찾을 수 없습니다: {directory_path}")
                return []

            if not directory_path.is_dir():
                self.logger.error(f"디렉토리가 아닙니다: {directory_path}")
                return []

            # 파일 패턴 설정
            if file_patterns is None:
                file_patterns = [
                    f"*{ext}" for ext in self.file_config["supported_extensions"]
                ]

            # 파일 목록 수집
            file_paths = []
            pattern = "**/*" if recursive else "*"

            for pattern_item in file_patterns:
                for file_path in directory_path.glob(f"{pattern}{pattern_item}"):
                    if file_path.is_file():
                        file_paths.append(str(file_path))

            self.logger.info(
                f"디렉토리에서 {len(file_paths)}개 파일을 발견했습니다: "
                f"{directory_path}"
            )
            return file_paths

        except Exception as e:
            self.logger.error(f"파일 검색 중 오류 발생 ({directory_path}): {e}")
            return []

    def save_documents(
        self, documents: List[Document], output_path: Optional[str] = None
    ) -> str:
        """Document 객체들을 파일로 저장합니다."""
        try:
            if not output_path:
                output_dir = Path(self.output_config["chunks_output_dir"])
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"chunks_{len(documents)}.json"

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Document 객체를 딕셔너리로 변환
            chunks_data = []
            for doc in documents:
                chunks_data.append(
                    {"page_content": doc.page_content, "metadata": doc.metadata}
                )

            # JSON 파일로 저장
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(chunks_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"문서가 {output_path}에 저장되었습니다.")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"문서 저장 중 오류 발생: {e}")
            return ""

    def load_json_documents(self, json_path: str) -> List[Document]:
        """
        JSON 파일에서 LangChain Document 객체 리스트를 로드합니다.

        지원 형식:
        1. main.py 형식: {"metadata": {...}, "documents": [...]}
        2. 간단한 형식: [{"page_content": ..., "metadata": {...}}]

        Args:
            json_path: JSON 파일 경로

        Returns:
            Document 객체 리스트
        """
        try:
            json_path = Path(json_path)

            if not json_path.exists():
                self.logger.error(f"JSON 파일을 찾을 수 없습니다: {json_path}")
                return []

            # JSON 파일 읽기
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            documents = []

            # 형식 판별 및 처리
            if isinstance(data, dict) and "documents" in data:
                # main.py 형식: {"metadata": {...}, "documents": [...]}
                docs_data = data["documents"]
                self.logger.debug(
                    f"main.py 형식 JSON 감지: {len(docs_data)}개 문서"
                )
            elif isinstance(data, list):
                # 간단한 형식: [{"page_content": ..., "metadata": {...}}]
                docs_data = data
                self.logger.debug(f"리스트 형식 JSON 감지: {len(docs_data)}개 문서")
            else:
                self.logger.error(f"지원하지 않는 JSON 형식입니다: {json_path}")
                return []

            # Document 객체로 변환
            for doc_dict in docs_data:
                if "page_content" in doc_dict and "metadata" in doc_dict:
                    doc = Document(
                        page_content=doc_dict["page_content"],
                        metadata=doc_dict["metadata"],
                    )
                    documents.append(doc)
                else:
                    self.logger.warning(
                        f"잘못된 문서 형식을 건너뜁니다: {doc_dict.keys()}"
                    )

            self.logger.info(
                f"JSON 파일에서 {len(documents)}개 문서를 로드했습니다: {json_path}"
            )
            return documents

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 오류 ({json_path}): {e}")
            return []
        except Exception as e:
            self.logger.error(f"JSON 문서 로드 중 오류 발생 ({json_path}): {e}")
            return []

    def load_all_json_from_directory(
        self,
        dir_path: str,
        pattern: str = "*_chunks_*.json",
        remove_duplicates: bool = True,
    ) -> List[Document]:
        """
        디렉토리에서 모든 JSON 청크 파일을 로드하여 Document 리스트로 반환합니다.

        Args:
            dir_path: 디렉토리 경로
            pattern: 파일 패턴 (기본값: "*_chunks_*.json")
            remove_duplicates: 중복 제거 여부 (metadata['id'] 기반)

        Returns:
            Document 객체 리스트
        """
        try:
            dir_path = Path(dir_path)

            if not dir_path.exists():
                self.logger.error(f"디렉토리를 찾을 수 없습니다: {dir_path}")
                return []

            if not dir_path.is_dir():
                self.logger.error(f"디렉토리가 아닙니다: {dir_path}")
                return []

            # JSON 파일 목록 수집
            json_files = sorted(dir_path.glob(pattern))

            if not json_files:
                self.logger.warning(
                    f"패턴 '{pattern}'과 일치하는 파일이 없습니다: {dir_path}"
                )
                return []

            self.logger.info(
                f"디렉토리에서 {len(json_files)}개 JSON 파일을 발견했습니다: "
                f"{dir_path}"
            )

            # 모든 JSON 파일에서 문서 로드
            all_documents = []
            for json_file in json_files:
                documents = self.load_json_documents(str(json_file))
                all_documents.extend(documents)

            # 중복 제거 (metadata['id'] 기반)
            if remove_duplicates and all_documents:
                seen_ids = set()
                unique_documents = []

                for doc in all_documents:
                    doc_id = doc.metadata.get("id")
                    if doc_id and doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        unique_documents.append(doc)
                    elif not doc_id:
                        # ID가 없는 문서는 모두 포함
                        unique_documents.append(doc)

                removed_count = len(all_documents) - len(unique_documents)
                if removed_count > 0:
                    self.logger.info(f"중복된 문서 {removed_count}개를 제거했습니다.")

                all_documents = unique_documents

            self.logger.info(f"총 {len(all_documents)}개 문서를 로드했습니다.")
            return all_documents

        except Exception as e:
            self.logger.error(
                f"디렉토리에서 JSON 로드 중 오류 발생 ({dir_path}): {e}"
            )
            return []

    def get_latest_json_file(
        self, dir_path: str, pattern: str = "*_chunks_*.json"
    ) -> Optional[str]:
        """
        디렉토리에서 가장 최근에 생성된 JSON 파일 경로를 반환합니다.

        파일명의 타임스탬프 (YYYYMMDD_HHMMSS) 기반으로 정렬합니다.

        Args:
            dir_path: 디렉토리 경로
            pattern: 파일 패턴 (기본값: "*_chunks_*.json")

        Returns:
            최신 JSON 파일의 전체 경로 (없으면 None)
        """
        try:
            dir_path = Path(dir_path)

            if not dir_path.exists() or not dir_path.is_dir():
                self.logger.error(f"유효하지 않은 디렉토리: {dir_path}")
                return None

            # JSON 파일 목록 수집
            json_files = list(dir_path.glob(pattern))

            if not json_files:
                self.logger.warning(
                    f"패턴 '{pattern}'과 일치하는 파일이 없습니다: {dir_path}"
                )
                return None

            # 수정 시간 기준으로 정렬 (최신순)
            latest_file = max(json_files, key=lambda f: f.stat().st_mtime)

            self.logger.info(f"가장 최근 파일: {latest_file.name}")
            return str(latest_file)

        except Exception as e:
            self.logger.error(
                f"최신 JSON 파일 검색 중 오류 발생 ({dir_path}): {e}"
            )
            return None

