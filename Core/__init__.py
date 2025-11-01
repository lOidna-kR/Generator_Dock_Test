"""
Core 모듈

LangGraph 기반 Generator를 제공합니다.

최신 LangGraph 권장 방식:
- StateGraph를 사용한 명시적 워크플로우
- Annotated State로 확장 가능한 구조
- Checkpointer를 통한 상태 저장/복원
- Streaming 지원

모드:
- AskMode: Ask Mode - RAG 질의응답 (LangGraph)
- ForgeMode: Forge Mode - MCQ 생성 (LangGraph)
"""

# Core 모듈 imports
from Utils import (
    FileProcessor,
    format_documents_for_llm,
    SystemInfoCollector,
    VectorSearchUtils,
)
from .ask_mode import AskMode, create_ask_mode

# ForgeMode (LangGraph 방식)
from .forge_mode import ForgeMode, create_forge_mode

# 전역 설정 imports (fallback 메커니즘 사용)
try:
    from config import (
        get_chunking_config,
        validate_config,
        CHUNKING_CONFIG,
        FILE_PROCESSING_CONFIG,
        OUTPUT_CONFIG,
        LOGGING_CONFIG,
    )
except ImportError:
    # 패키지로 설치된 경우를 위한 fallback
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from config import (
        get_chunking_config,
        validate_config,
        CHUNKING_CONFIG,
        FILE_PROCESSING_CONFIG,
        OUTPUT_CONFIG,
        LOGGING_CONFIG,
    )

# 패키지 메타데이터
__version__ = "1.0.0"
__author__ = "Generator Developer"

# 공개 API 정의
__all__ = [
    # Core 클래스들
    "AskMode",
    "ForgeMode",
    "FileProcessor",
    "SystemInfoCollector",
    "VectorSearchUtils",
    
    # 유틸리티 함수들
    "create_ask_mode",
    "create_forge_mode",
    "format_documents_for_llm",
    
    # 설정 함수들
    "get_chunking_config", 
    "validate_config",
    
    # 설정 상수들
    "CHUNKING_CONFIG",
    "FILE_PROCESSING_CONFIG",
    "OUTPUT_CONFIG",
    "LOGGING_CONFIG"
]
