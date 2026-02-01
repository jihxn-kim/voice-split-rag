"""
로깅 유틸리티 - 싱글톤 로거 관리
"""
import logging
import sys
from typing import Optional


class LoggerSingleton:
    """
    싱글톤 패턴의 로거 팩토리  
    """
    _loggers = {}

    @classmethod
    def get_logger(cls, logger_name: str = "app", level: int = logging.INFO) -> logging.Logger:
        """
        지정된 이름의 로거를 반환합니다. 이미 생성된 경우 기존 로거를 반환합니다.
        
        Args:
            logger_name: 로거 이름
            level: 로그 레벨 (기본값: INFO)
            
        Returns:
            logging.Logger: 설정된 로거 인스턴스
        """
        if logger_name in cls._loggers:
            return cls._loggers[logger_name]

        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

        # 핸들러가 없는 경우에만 추가 (중복 방지)
        if not logger.handlers:
            # 콘솔 핸들러
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)

            # 포맷터
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)

        cls._loggers[logger_name] = logger
        return logger
