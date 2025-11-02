"""
설정 관리 모듈

환경 변수 기반 설정을 중앙에서 관리합니다.
민감한 정보는 .env 파일에 저장하고, 이 모듈을 통해 접근합니다.

주요 기능:
    - 환경 변수 로드 (python-dotenv 사용)
    - Vertex AI 설정 관리
    - MCQ 생성 설정 (가중치, Few-shot 예시)
    - 프롬프트 템플릿 로드 (Data/Prompts/)
    - 설정 검증 및 로깅

사용 방법:
    1. .env 파일 생성
       cp .env.example .env
    
    2. .env 파일 수정
       - GCP_PROJECT_ID: GCP 프로젝트 ID
       - VERTEX_AI_INDEX_ID: Vector Search Index ID
       - VERTEX_AI_ENDPOINT_ID: Vector Search Endpoint ID
       - GCS_BUCKET_NAME: Cloud Storage 버킷 이름
       - GOOGLE_APPLICATION_CREDENTIALS: 서비스 계정 키 경로
    
    3. 설정 검증
       python -c "from config import validate_config; validate_config()"
       또는
       python config.py

예제 .env 파일:
    GCP_PROJECT_ID=yang-first-aid
    VERTEX_AI_INDEX_ID=8376679913746333696
    VERTEX_AI_ENDPOINT_ID=1234567890123456789
    GCS_BUCKET_NAME=rag-cloud-run-test
    GOOGLE_APPLICATION_CREDENTIALS=C:/keys/service-account.json
    LOG_LEVEL=INFO
    LOG_FILE=true
"""

import os
import logging
from typing import Dict, Any, List
from pathlib import Path

# config 모듈용 간단한 로거 설정
_config_logger = logging.getLogger("config")
_config_logger.setLevel(logging.INFO)
if not _config_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    _config_logger.addHandler(_handler)

# python-dotenv 사용 (없으면 설치: pip install python-dotenv)
try:
    from dotenv import load_dotenv
    
    # .env 파일 로드
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        _config_logger.info(f"✅ .env 파일 로드 완료: {env_path}")
    else:
        _config_logger.warning(f"⚠️  .env 파일이 없습니다. .env.example을 복사하여 .env를 생성하세요.")
except ImportError:
    _config_logger.warning("⚠️  python-dotenv가 설치되지 않았습니다. 환경 변수를 직접 설정하세요.")
    _config_logger.warning("   설치: pip install python-dotenv")


# ==================== Vertex AI 기본 설정 ====================

VERTEX_AI_CONFIG = {
    "project": os.getenv("GCP_PROJECT_ID"),
    "location": os.getenv("GCP_LOCATION", "us-central1"),
    "region": os.getenv("GCP_REGION", "us-central1"),
}


# ==================== 모델 설정 ====================


def get_gemini_model_config() -> Dict[str, Any]:
    """
    Gemini 모델 설정을 반환합니다.
    
    Returns:
        Dict[str, Any]: Gemini 모델 설정
            - model_name: Gemini 모델 이름 (기본값: gemini-1.5-flash-002)
    
    Example:
        >>> config = get_gemini_model_config()
        >>> model_name = config["model_name"]
    """
    return {
        "model_name": os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-002"),
    }


def get_retriever_config() -> Dict[str, Any]:
    """
    Retriever 설정을 반환합니다.
    
    Returns:
        Dict[str, Any]: Retriever 설정
            - embedding_model: 임베딩 모델명 (기본: gemini-embedding-001)
            - embedding_dimensions: 임베딩 차원수 (기본: 3072)
            - index_id: Vertex AI Vector Search Index ID
            - endpoint_id: Vertex AI Endpoint ID
            - gcs_bucket_name: Cloud Storage 버킷 이름
            - k: 최종 반환할 문서 수 (기본: 3, Reranking 후)
            - initial_k: 초기 검색 문서 수 (기본: 10, Reranking 전)
            - search_type: 검색 타입 (기본: similarity)
            - similarity_threshold: 유사도 임계값 (기본: 0.7)
            - llm_temperature: LLM Temperature (기본: 0.7)
            - max_output_tokens: 최대 출력 토큰 (기본: 2048)
            - stream_update: Stream Update 사용 여부 (기본: false)
    
    Example:
        >>> config = get_retriever_config()
        >>> k = config["k"]
        >>> initial_k = config["initial_k"]
    """
    return {
        "embedding_model": os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
        "embedding_dimensions": int(os.getenv("EMBEDDING_DIMENSIONS", "3072")),
        "index_id": os.getenv("VERTEX_AI_INDEX_ID"),
        "endpoint_id": os.getenv("VERTEX_AI_ENDPOINT_ID"),
        "gcs_bucket_name": os.getenv("GCS_BUCKET_NAME"),
        "k": int(os.getenv("RETRIEVAL_K", "3")),  # 최종 반환할 문서 개수
        "initial_k": int(os.getenv("RETRIEVAL_INITIAL_K", "10")),  # Reranking 전 초기 검색 개수
        "search_type": os.getenv("SEARCH_TYPE", "similarity"),
        "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
        "llm_temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "max_output_tokens": int(os.getenv("MAX_OUTPUT_TOKENS", "2048")),
        "stream_update": os.getenv("STREAM_UPDATE", "false").lower() == "true",
    }


def get_generation_config() -> Dict[str, Any]:
    """
    Generation 설정 반환
    
    Returns:
        Generation 설정 딕셔너리
    """
    return {
        "temperature": float(os.getenv("GENERATION_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("GENERATION_MAX_TOKENS", "2048")),
    }


# ==================== 문서 처리 설정 ====================

def get_chunking_config() -> Dict[str, Any]:
    """
    청킹 설정 반환
    
    Returns:
        청킹 설정 딕셔너리
    """
    return {
        "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "200")),
    }


CHUNKING_CONFIG = get_chunking_config()


# ==================== 파일 처리 설정 ====================

FILE_PROCESSING_CONFIG = {
    "supported_extensions": [".pdf", ".txt", ".docx", ".md"],
}


# ==================== 출력 설정 ====================

OUTPUT_CONFIG = {
    "max_source_preview": int(os.getenv("MAX_SOURCE_PREVIEW", "300")),
}


# ==================== 로깅 설정 ====================

LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "console": os.getenv("LOG_CONSOLE", "true").lower() == "true",
    "file_logging": os.getenv("LOG_FILE", "true").lower() == "true",  # 기본값 true로 변경
    "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
}


def get_logging_config() -> Dict[str, Any]:
    """
    로깅 설정 반환
    
    Returns:
        로깅 설정 딕셔너리
    """
    return LOGGING_CONFIG


def get_paths() -> Dict[str, Path]:
    """
    프로젝트 경로 설정 반환
    
    Returns:
        경로 설정 딕셔너리
        - project_root: 프로젝트 루트 디렉토리
        - logs: 로그 디렉토리 (Logs/)
    """
    project_root = Path(__file__).parent
    return {
        "project_root": project_root,
        "logs": project_root / "Logs",  # 대문자 Logs로 변경
    }


# ==================== 설정 검증 ====================

def validate_config() -> bool:
    """
    필수 환경 변수가 모두 설정되었는지 검증합니다.
    
    검증 대상:
        - GCP_PROJECT_ID: GCP 프로젝트 ID
        - VERTEX_AI_INDEX_ID: Vector Search Index ID
        - VERTEX_AI_ENDPOINT_ID: Vector Search Endpoint ID
        - GCS_BUCKET_NAME: Cloud Storage 버킷 이름
    
    Returns:
        bool: 
            - True: 모든 필수 설정 존재
            - False: 누락된 설정 있음
    
    Example:
        >>> if not validate_config():
        ...     raise ValueError("설정을 확인하세요!")
    """
    required_vars = [
        "GCP_PROJECT_ID",
        "VERTEX_AI_INDEX_ID",
        "VERTEX_AI_ENDPOINT_ID",
        "GCS_BUCKET_NAME",
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f"your-{var.lower().replace('_', '-')}-here":
            missing.append(var)
    
    if missing:
        _config_logger.error("=" * 60)
        _config_logger.error("❌ 환경 변수 설정 오류")
        _config_logger.error("=" * 60)
        _config_logger.error(f"누락된 환경 변수: {', '.join(missing)}")
        _config_logger.error("해결 방법:")
        _config_logger.error("1. .env.example을 복사하여 .env 파일 생성")
        _config_logger.error("   cp .env.example .env")
        _config_logger.error("2. .env 파일을 열어서 실제 값으로 수정")
        _config_logger.error(f"   편집: {missing[0]}=your-actual-value")
        _config_logger.error("3. 각 값을 확인하는 방법은 .env.example 주석 참고")
        _config_logger.error("=" * 60)
        return False
    
    _config_logger.info("✅ 모든 필수 환경 변수가 설정되었습니다.")
    return True


def log_config_status():
    """
    현재 설정 상태를 로깅합니다 (민감정보 제외).
    
    디버깅이나 설정 확인용으로 사용합니다.
    
    Example:
        >>> from config import log_config_status
        >>> log_config_status()
    """
    separator = "=" * 60
    _config_logger.info(separator)
    _config_logger.info("현재 설정 상태")
    _config_logger.info(separator)
    
    # 프로젝트 정보
    project_id = os.getenv("GCP_PROJECT_ID", "미설정")
    _config_logger.info(f"📌 프로젝트: {project_id[:20]}...")
    
    # 모델 설정
    _config_logger.info("🤖 모델:")
    _config_logger.info(f"  - Gemini: {os.getenv('GEMINI_MODEL_NAME', 'gemini-1.5-flash-002')}")
    _config_logger.info(f"  - Embedding: {os.getenv('EMBEDDING_MODEL', 'gemini-embedding-001')}")
    _config_logger.info(f"  - Embedding 차원: {os.getenv('EMBEDDING_DIMENSIONS', '3072')}")
    
    # Retrieval 설정
    _config_logger.info("🔍 Retrieval:")
    _config_logger.info(f"  - K: {os.getenv('RETRIEVAL_K', '3')}")
    _config_logger.info(f"  - Initial K: {os.getenv('RETRIEVAL_INITIAL_K', '10')}")
    _config_logger.info(f"  - Search Type: {os.getenv('SEARCH_TYPE', 'similarity')}")
    _config_logger.info(f"  - Threshold: {os.getenv('SIMILARITY_THRESHOLD', '0.7')}")
    
    # LLM 설정
    _config_logger.info("⚙️  LLM:")
    _config_logger.info(f"  - Temperature: {os.getenv('LLM_TEMPERATURE', '0.7')}")
    _config_logger.info(f"  - Max Tokens: {os.getenv('MAX_OUTPUT_TOKENS', '2048')}")
    
    # 로깅 설정
    _config_logger.info("📝 로깅:")
    _config_logger.info(f"  - Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    _config_logger.info(f"  - Console: {os.getenv('LOG_CONSOLE', 'true')}")
    _config_logger.info(f"  - File: {os.getenv('LOG_FILE', 'true')}")
    
    _config_logger.info(separator)


# ==================== MCQ 관련 설정 ====================


def get_mcq_generation_config() -> Dict[str, Any]:
    """
    MCQ 생성 설정을 반환합니다.
    
    Returns:
        Dict[str, Any]: MCQ 생성 설정
            - random_sample_max: 랜덤 샘플링 최대 개수 (기본: 1000)
            - few_shot_max_examples: Few-shot 예시 최대 개수 (기본: 1)
            - few_shot_folder_path: Few-shot 폴더 경로 (기본: Data/Few_Shot)
            - part_weights: Part별 가중치 (교재 비중 반영)
            - category_weights: 카테고리별 가중치 (문제 형태 비율)
    
    Example:
        >>> config = get_mcq_generation_config()
        >>> part_weights = config["part_weights"]
        >>> category_weights = config["category_weights"]
    """
    return {
        "random_sample_max": int(os.getenv("MCQ_RANDOM_SAMPLE_MAX", "1000")),
        "few_shot_max_examples": int(os.getenv("MCQ_FEW_SHOT_MAX_EXAMPLES", "1")),  # 1개 예시 (명확한 형식 지시)
        "few_shot_folder_path": os.getenv("MCQ_FEW_SHOT_FOLDER_PATH", "Data/Few_Shot"),
        "max_context_docs": int(os.getenv("MCQ_MAX_CONTEXT_DOCS", "3")),
        
        # Part별 가중치 (전체 비율, 실제 메타데이터 형식 사용)
        # 주의: 메타데이터는 짧은 형식 ("총론", "법령", "각론")
        "part_weights": {
            "총론": 22.5,      # 전체 22.5% - 기초 이론
            "법령": 10,        # 전체 10% - 법규
            "각론": 67.5,      # 전체 67.5% - 각론 (하위 주제들로 분배됨)
        },
        
        # Chapter별 가중치 (전체 비율로 직접 지정)
        # 각론의 Chapter들을 Part와 동일한 레벨에서 가중치 적용
        "chapter_weights": {
            "총론": {
                "응급의료체계의개요": 4.5,       # 총론 22.5%를 5개 Chapter로 균등 분배
                "환자이송및구급차운용": 4.5,
                "대량재난": 4.5,
                "환자평가": 4.5,
                "구급장비": 4.5,
                # 합계: 22.5% (총론 전체)
            },
            "법령": {
                "구조구급에관한법률": 5,         # 법령 10%를 2개 Chapter로 균등 분배
                "응급의료에관한법률": 5,
                # 합계: 10% (법령 전체)
            },
            "각론": {
                "전문심장소생술": 25,      # 전체 25%
                "전문외상처치술": 22.5,    # 전체 22.5%
                "내과응급": 15,             # 전체 15%
                "특수응급": 5,              # 전체 5%
                # 합계: 67.5% (각론 전체)
            }
        },
        
        # 주제별 카테고리 가중치 (문제 형태 비율) - Few_Shot 분석 결과 반영
        "topic_category_weights": {
            "총론": {
                "SIMPLE": 0.45,      # 45% (기초 이론은 단순형 위주)
                "MULTIPLE": 0.15,    # 15% (복수 선택형 적음)
                "CASE_BASED": 0.30, # 30% (케이스 기반형)
                "IMAGE_BASED": 0.10, # 15% (이미지 기반)
                "ECG_BASED": 0.00,  # 0% (심전도 관련 적음)
            },
            # 총론 - Chapter 단위 가중치 (Part 가중치 복제, 필요 시 챕터별로 조정 가능)
            "응급의료체계의개요": {
                "SIMPLE": 0.45,
                "MULTIPLE": 0.15,
                "CASE_BASED": 0.30,
                "IMAGE_BASED": 0.10,
                "ECG_BASED": 0.00,
            },
            "환자이송및구급차운용": {
                "SIMPLE": 0.45,
                "MULTIPLE": 0.15,
                "CASE_BASED": 0.30,
                "IMAGE_BASED": 0.10,
                "ECG_BASED": 0.00,
            },
            "대량재난": {
                "SIMPLE": 0.45,
                "MULTIPLE": 0.15,
                "CASE_BASED": 0.30,
                "IMAGE_BASED": 0.10,
                "ECG_BASED": 0.00,
            },
            "환자평가": {
                "SIMPLE": 0.45,
                "MULTIPLE": 0.15,
                "CASE_BASED": 0.30,
                "IMAGE_BASED": 0.10,
                "ECG_BASED": 0.00,
            },
            "구급장비": {
                "SIMPLE": 0.45,
                "MULTIPLE": 0.15,
                "CASE_BASED": 0.30,
                "IMAGE_BASED": 0.10,
                "ECG_BASED": 0.00,
            },
            "법령": {
                "SIMPLE": 0.60,      # 60% (법규는 단순형 위주)
                "MULTIPLE": 0.20,    # 20% (복수 선택형)
                "CASE_BASED": 0.20, # 20% (케이스 기반형)
                "IMAGE_BASED": 0.00, # 0% (이미지 기반 적음)
                "ECG_BASED": 0.00,  # 0% (심전도 관련 없음)
            },
            # 각론 Part 전체 선택 시 사용할 대표 가중치 (하위 챕터 비율 가중 평균)
            "각론": {
                "SIMPLE": 0.20,
                "MULTIPLE": 0.1167,
                "CASE_BASED": 0.3130,
                "IMAGE_BASED": 0.1111,
                "ECG_BASED": 0.2593,
            },
            # 법령 - Chapter 단위 가중치 (Part 가중치 복제, 필요 시 챕터별로 조정 가능)
            "구조구급에관한법률": {
                "SIMPLE": 0.60,
                "MULTIPLE": 0.20,
                "CASE_BASED": 0.20,
                "IMAGE_BASED": 0.00,
                "ECG_BASED": 0.00,
            },
            "응급의료에관한법률": {
                "SIMPLE": 0.60,
                "MULTIPLE": 0.20,
                "CASE_BASED": 0.20,
                "IMAGE_BASED": 0.00,
                "ECG_BASED": 0.00,
            },
            "전문심장소생술": {
                "SIMPLE": 0.05,      # 5% (단순형 적음)
                "MULTIPLE": 0.05,    # 5% (복수 선택형 적음)
                "CASE_BASED": 0.20, # 20% (케이스 기반형)
                "IMAGE_BASED": 0.00, # 0% (이미지 기반)
                "ECG_BASED": 0.70,  # 70% (심전도 관련 강화)
            },
            "전문외상처치술": {
                "SIMPLE": 0.30,      # 25% (단순형)
                "MULTIPLE": 0.15,    # 15% (복수 선택형)
                "CASE_BASED": 0.35, # 35% (케이스 기반형 강화)
                "IMAGE_BASED": 0.20, # 20% (이미지 기반)
                "ECG_BASED": 0.00,  # 5% (심전도 관련 적음)
            },
            "내과응급": {
                "SIMPLE": 0.25,      # 25% (단순형)
                "MULTIPLE": 0.15,    # 15% (복수 선택형)
                "CASE_BASED": 0.45, # 40% (케이스 기반형 강화)
                "IMAGE_BASED": 0.15, # 15% (이미지 기반)
                "ECG_BASED": 0.00,  # 5% (심전도 관련 적음)
            },
            "특수응급": {
                "SIMPLE": 0.35,      # 30% (단순형)
                "MULTIPLE": 0.20,    # 20% (복수 선택형)
                "CASE_BASED": 0.30, # 30% (케이스 기반형)
                "IMAGE_BASED": 0.15, # 15% (이미지 기반)
                "ECG_BASED": 0.00,  # 5% (심전도 관련 적음)
            }
        },
        
        # 기본 카테고리 가중치 (주제별 설정이 없을 때 사용)
        "default_category_weights": {
            "SIMPLE": 0.25,      # 25% (단순 선택형)
            "MULTIPLE": 0.20,    # 20% (복수 선택형: ㉠㉡㉢ 모두 고르시오)
            "CASE_BASED": 0.25,  # 25% (케이스 기반형)
            "IMAGE_BASED": 0.20, # 20% (이미지/그래프 참조형)
            "ECG_BASED": 0.10,   # 10% (심전도 관련형)
        }
    }


def get_category_weights_by_topic(topic_name: str) -> Dict[str, float]:
    """
    주제별 카테고리 가중치를 반환합니다.
    
    Args:
        topic_name: 주제 이름 (총론, 법령, 전문심장소생술, 전문외상처치술, 내과응급, 특수응급)
    
    Returns:
        Dict[str, float]: 카테고리별 가중치
    """
    config = get_mcq_generation_config()
    topic_weights = config.get("topic_category_weights", {})
    
    # 주제별 가중치가 있으면 사용, 없으면 기본값 사용
    return topic_weights.get(topic_name, config.get("default_category_weights", {}))


def get_mcq_types() -> Dict[str, Any]:
    """
    MCQ 유형 설정을 반환합니다.
    
    Few-shot 예시를 Data/Few_Shot/ 폴더에서 카테고리별로 로드합니다.
    
    Returns:
        Dict[str, Any]: MCQ 유형 딕셔너리
            - MCQ_GENERAL: 일반 MCQ 설정
                - name: 유형 이름
                - instruction: 생성 지침
                - few_shot_examples: 전체 Few-shot 예시
                - category_examples: 카테고리별 예시
    
    Example:
        >>> mcq_types = get_mcq_types()
        >>> general_config = mcq_types["MCQ_GENERAL"]
        >>> examples = general_config["few_shot_examples"]
    """
    from Utils.few_shot import load_few_shot_examples_from_folder
    
    config = get_mcq_generation_config()
    folder_path = config["few_shot_folder_path"]
    
    # 카테고리 정의 (새로운 파일 구조에 맞게 수정)
    categories = {
        "SIMPLE": "단순형",
        "MULTIPLE": "복수형", 
        "CASE_BASED": "케이스형",
        "IMAGE_BASED": "이미지형",
        "ECG_BASED": "심전도형"
    }
    
    all_examples = []
    category_examples = {}
    
    try:
        few_shot_dict = load_few_shot_examples_from_folder(folder_path)
        
        # 카테고리별 파일 로드 (새로운 파일명 구조에 맞게 수정)
        file_mapping = {
            "SIMPLE": "Single_Type",
            "MULTIPLE": "Multiple_Type",
            "CASE_BASED": "Case_Type", 
            "IMAGE_BASED": "Image_Type",
            "ECG_BASED": "ECG_Type"
        }
        
        for cat_key, cat_name in categories.items():
            file_name = file_mapping.get(cat_key)
            if file_name and file_name in few_shot_dict:
                examples = few_shot_dict[file_name]
                category_examples[cat_key] = examples
                all_examples.extend(examples)
        
        # MCQ_GENERAL도 있으면 추가 (호환성)
        if "MCQ_GENERAL" in few_shot_dict:
            general_examples = few_shot_dict["MCQ_GENERAL"]
            all_examples.extend(general_examples)
        
        if not all_examples:
            raise ValueError("Few-shot 예시가 로드되지 않았습니다")
        
        # 간결한 로드 완료 메시지
        _config_logger.info(f"✓ Few-shot 로드 완료 ({len(all_examples)}개, {len(category_examples)} 카테고리)")
        
    except (FileNotFoundError, Exception) as e:
        _config_logger.error(f"❌ Few-shot 폴더 로드 실패: {e}")
        _config_logger.warning(f"   기본 예시를 사용합니다.")
        # Fallback: 기본 예시
        all_examples = [
            {
                "question": "응급의료체계의 주요 구성요소는?",
                "options": [
                    "119 구급대",
                    "응급의료기관",
                    "의료지도",
                    "모두 포함"
                ],
                "answer_index": 4,
                "explanation": "응급의료체계는 119 구급대, 응급의료기관, 의료지도 등 모든 요소가 유기적으로 연결되어 있습니다."
            }
        ]
        category_examples = {}
    
    return {
        "MCQ_GENERAL": {
            "name": "MCQ_GENERAL",
            "instruction": (
                "교재 내용을 기반으로 4지선다형 문제를 생성하세요. "
                "⚠️ 중요: Few-shot 예시와 동일한 형식(질문 구조, 보기 스타일, 해설 방식)으로 작성하되, "
                "내용은 반드시 교재에서 가져와야 합니다. "
                "질문은 명확하고 구체적이어야 하며, 보기는 서로 구분되어야 합니다. 정답 해설은 상세하게 작성하세요."
            ),
            "few_shot_examples": all_examples,
            "category_examples": category_examples,  # 카테고리별 예시 추가
        }
    }


def get_prompt_templates() -> Dict[str, str]:
    """
    MCQ 생성용 프롬프트 템플릿 반환
    
    프롬프트는 Data/Prompts/ 폴더의 텍스트 파일에서 로드됩니다.
    버전 관리와 A/B 테스트를 위해 파일로 분리되었습니다.
    
    Returns:
        프롬프트 템플릿 딕셔너리
        - mcq_generation_system: 시스템 프롬프트
        - mcq_generation_human_retriever: Retriever 기반 프롬프트 (주제 기반 생성)
    
    Example:
        >>> templates = get_prompt_templates()
        >>> system_prompt = templates["mcq_generation_system"]
    """
    prompt_dir = Path(__file__).parent / "Data" / "Prompts"
    
    try:
        # 프롬프트 파일에서 로드
        system_prompt = (prompt_dir / "system_prompt.txt").read_text(encoding="utf-8")
        human_retriever = (prompt_dir / "retriever_prompt.txt").read_text(encoding="utf-8")
        
        _config_logger.debug("프롬프트 템플릿 로드 완료 (파일에서)")
        
        return {
            "mcq_generation_system": system_prompt,
            "mcq_generation_human_retriever": human_retriever,
        }
        
    except FileNotFoundError as e:
        _config_logger.warning(f"프롬프트 파일 로드 실패: {e}. 기본 템플릿 사용")
        
        # Fallback: 기본 프롬프트 (간단 버전)
        return {
            "mcq_generation_system": (
                "당신은 교육 전문가입니다. 주어진 교재 내용을 바탕으로 "
                "4지선다형 문제를 생성합니다."
            ),
            "mcq_generation_human_retriever": (
                "교재 내용:\n{context}\n\n"
                "주제: {question}\n\n"
                "지침:\n{instruction}\n\n"
                "{format_instructions}"
            ),
        }


# ==================== 교재 구조 설정 ====================


def get_textbook_structure() -> Dict[str, List[str]]:
    """
    교재의 Part와 Chapter 구조 반환
    
    출처: 2026_양승아_응급처치학개론_목차.pdf
    
    중요: 실제 메타데이터 형식 사용 (짧은 형식)
    - Part: "총론", "법령", "각론"
    - Chapter: "전문심장소생술", "전문외상처치술" 등
    
    Returns:
        교재 구조 딕셔너리
        - Key: Part 이름 (실제 메타데이터 형식)
        - Value: Chapter 이름 리스트 (실제 메타데이터 형식)
    
    사용 예시:
        >>> structure = get_textbook_structure()
        >>> generator.generate_mcq(topics_hierarchical=structure)
    """
    return {
        "총론": [
            "응급의료체계의개요",
            "환자이송및구급차운용",
            "대량재난",
            "환자평가",
            "구급장비",
        ],
        "법령": [
            "구조구급에관한법률",
            "응급의료에관한법률",
        ],
        "각론": [
            "전문심장소생술",
            "전문외상처치술",
            "내과응급",
            "특수응급",
        ],
    }


# 전역 상수로 노출
TEXTBOOK_STRUCTURE = get_textbook_structure()


# ==================== 초기화 시 자동 검증 ====================

if __name__ == "__main__":
    # config.py를 직접 실행하면 설정 검증
    _config_logger.info("🔍 설정 검증 중...")
    
    if validate_config():
        log_config_status()
        
        # 교재 구조 출력
        _config_logger.info("=" * 60)
        _config_logger.info("📚 교재 구조")
        _config_logger.info("=" * 60)
        structure = get_textbook_structure()
        for part, chapters in structure.items():
            _config_logger.info(f"{part}")
            for chapter in chapters:
                _config_logger.info(f"  - {chapter}")
        _config_logger.info("=" * 60)
    else:
        _config_logger.error("💡 .env 파일 설정 후 다시 실행하세요.")

