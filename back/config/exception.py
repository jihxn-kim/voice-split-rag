from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Any, Dict, Optional
import traceback
import logging


class ErrorResponse(BaseModel):
    success: bool = False
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class AppException(Exception):
    """애플리케이션 전역에서 사용하는 커스텀 예외.

    - code: 서비스 내 식별 가능한 에러 코드 (예: AUTH_INVALID_TOKEN)
    - status_code: HTTP 상태 코드
    - message: 사용자에게 전달할 메시지
    - details: 디버깅/추가 정보 (옵션)
    - log_level: 기록 레벨 (logging.INFO, WARNING, ERROR 등)
    """

    def __init__(
        self,
        *,
        code: str,
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        log_level: int = logging.ERROR,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        self.log_level = log_level

    def to_response(self) -> JSONResponse:
        payload = ErrorResponse(code=self.code, message=self.message, details=self.details)
        return JSONResponse(status_code=self.status_code, content=payload.model_dump())


def register_exception_handlers(app) -> None:
    """FastAPI 앱에 전역 예외 핸들러를 등록합니다."""
    logger = logging.getLogger("exception")

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        logger.log(exc.log_level, f"AppException: {exc.code} - {exc.message} | path={request.url.path}")
        return exc.to_response()

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        logger.warning("ValidationError on %s: %s", request.url.path, exc.errors())
        payload = ErrorResponse(
            code="REQUEST_VALIDATION_ERROR",
            message="요청이 유효하지 않습니다.",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        tb = traceback.format_exc()
        logger.exception("Unhandled exception on %s: %s\n%s", request.url.path, str(exc), tb)
        payload = ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message="서버 내부 오류가 발생했습니다.",
            details=None,
        )
        return JSONResponse(status_code=500, content=payload.model_dump())


# 편의 유틸리티: 자주 쓰는 예외 생성기
def BadRequest(message: str, *, code: str = "BAD_REQUEST", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(code=code, status_code=400, message=message, details=details, log_level=logging.WARNING)


def Unauthorized(message: str = "인증이 필요합니다.", *, code: str = "UNAUTHORIZED", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(code=code, status_code=401, message=message, details=details, log_level=logging.WARNING)


def Forbidden(message: str = "접근 권한이 없습니다.", *, code: str = "FORBIDDEN", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(code=code, status_code=403, message=message, details=details, log_level=logging.WARNING)


def NotFound(message: str = "리소스를 찾을 수 없습니다.", *, code: str = "NOT_FOUND", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(code=code, status_code=404, message=message, details=details, log_level=logging.INFO)


def Conflict(message: str = "충돌이 발생했습니다.", *, code: str = "CONFLICT", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(code=code, status_code=409, message=message, details=details, log_level=logging.WARNING)


def UnprocessableEntity(message: str = "처리할 수 없는 요청입니다.", *, code: str = "UNPROCESSABLE_ENTITY", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(code=code, status_code=422, message=message, details=details, log_level=logging.WARNING)


def InternalError(message: str = "서버 내부 오류가 발생했습니다.", *, code: str = "INTERNAL_SERVER_ERROR", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(code=code, status_code=500, message=message, details=details, log_level=logging.ERROR)
