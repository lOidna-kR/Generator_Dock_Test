"""
Utils 모듈 패키지

이 패키지는 Generator 시스템의 유틸리티 함수와 클래스를 제공합니다.

주요 모듈:
- logging: 로깅 설정
- file: 파일 처리
- document: 문서 포맷팅
- search: 벡터 검색
- system: 시스템 정보 수집
- few_shot: Few-shot Learning 지원
- session: 세션 및 히스토리 관리
"""

# 로깅
from .logging import setup_logging

# 파일 처리
from .file import FileProcessor

# 문서 처리
from .document import format_documents_for_llm, extract_texts_and_metadatas_from_documents

# 벡터 검색
from .search import VectorSearchUtils

# 시스템 정보
from .system import SystemInfoCollector

# Few-shot Learning
from .few_shot import (
    build_few_shot_prompt,
    load_few_shot_examples_from_json,
    load_few_shot_examples_from_folder,
    format_single_example,
    validate_few_shot_example,
    filter_valid_examples,
    create_few_shot_template,
)

# 에러 처리
from .error_handling import (
    NodeErrorHandler,
    create_error_handler,
    should_continue_retry,
    get_retry_info,
)

# 세션 관리
from .session import (
    add_to_history,
    get_recent_history,
    clear_history,
    extract_topic_from_history,
    get_recent_sources_info,
    show_conversation_history,
    save_session,
    load_session,
    get_session_statistics,
)

__all__ = [
    # 로깅
    "setup_logging",
    # 파일 처리
    "FileProcessor",
    # 문서 처리
    "format_documents_for_llm",
    "extract_texts_and_metadatas_from_documents",
    # 벡터 검색
    "VectorSearchUtils",
    # 시스템 정보
    "SystemInfoCollector",
    # Few-shot Learning
    "build_few_shot_prompt",
    "load_few_shot_examples_from_json",
    "load_few_shot_examples_from_folder",
    "format_single_example",
    "validate_few_shot_example",
    "filter_valid_examples",
    "create_few_shot_template",
    # 에러 처리
    "NodeErrorHandler",
    "create_error_handler",
    "should_continue_retry",
    "get_retry_info",
    # 세션 관리
    "add_to_history",
    "get_recent_history",
    "clear_history",
    "extract_topic_from_history",
    "get_recent_sources_info",
    "show_conversation_history",
    "save_session",
    "load_session",
    "get_session_statistics",
]

__version__ = "1.0.0"

