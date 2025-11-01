"""
로깅 유틸리티 모듈

주요 기능:
- setup_logging: 공통 로깅 설정 함수 (콘솔 + 파일 로깅)
- ColorFormatter: 컬러 로그 포맷터 (콘솔용)
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# config import (fallback 메커니즘 사용)
try:
    from config import get_logging_config, get_paths
except ImportError:
    import sys as _sys
    from pathlib import Path as _Path

    project_root = _Path(__file__).parent.parent
    if str(project_root) not in _sys.path:
        _sys.path.insert(0, str(project_root))

    from config import get_logging_config, get_paths


class ColorFormatter(logging.Formatter):
    """컬러 로그 포맷터 (콘솔용)"""
    
    # ANSI 컬러 코드
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # 로그 레벨에 따른 컬러 적용
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(
    logger_name: str,
    level: Optional[str] = None,
    format_str: Optional[str] = None,
    console: Optional[bool] = None,
    file_logging: Optional[bool] = None,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    공통 로깅 설정 함수 (콘솔 + 파일 로깅)

    Args:
        logger_name: 로거 이름
        level: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_str: 로그 포맷 문자열
        console: 콘솔 로깅 활성화 여부
        file_logging: 파일 로깅 활성화 여부
        log_file: 로그 파일 경로 (None이면 config에서 가져옴)

    Returns:
        설정된 로거 객체

    예제:
        logger = setup_logging(__name__)
        logger.info("로그 메시지")
    """
    # 설정 가져오기
    logging_config = get_logging_config()
    paths = get_paths()
    
    # 기본값 설정
    if level is None:
        level = logging_config["level"]
    
    if format_str is None:
        format_str = logging_config["format"]
    
    # config에서 설정 가져오기 (None인 경우만)
    if file_logging is None:
        file_logging = logging_config.get("file_logging", True)
    
    if console is None:
        console = logging_config.get("console", True)
    
    if log_file is None and file_logging:
        # 로그 디렉토리 생성
        log_dir = paths["logs"]
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 로그 파일 경로 설정
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"generator_{timestamp}.log"
    
    # 로거 생성
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()
    
    # 콘솔 핸들러
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        # 컬러 포맷터 사용 (콘솔용)
        console_formatter = ColorFormatter(format_str)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 파일 핸들러
    if file_logging and log_file:
        # 로그 디렉토리 생성
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        
        # 일반 포맷터 사용 (파일용)
        file_formatter = logging.Formatter(format_str)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"로그 파일: {log_file}")
    
    # propagate 방지 (중복 로그 방지)
    logger.propagate = False
    
    return logger
