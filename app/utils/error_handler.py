from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from typing import Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class APIError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Union[dict, list, None] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)

async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global error handler for the application"""
    error_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    if isinstance(exc, APIError):
        status_code = exc.status_code
        error_code = exc.error_code
        message = exc.message
        details = exc.details
    elif isinstance(exc, RequestValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        error_code = "VALIDATION_ERROR"
        message = "Validation error"
        details = [{"loc": err["loc"], "msg": err["msg"]} for err in exc.errors()]
    elif isinstance(exc, SQLAlchemyError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "DATABASE_ERROR"
        message = "Database error occurred"
        details = None
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_SERVER_ERROR"
        message = "An unexpected error occurred"
        details = None
    
    # Log the error
    logger.error(
        f"Error ID: {error_id} - {error_code}: {message}",
        extra={
            "error_id": error_id,
            "error_code": error_code,
            "status_code": status_code,
            "path": request.url.path,
            "method": request.method,
            "details": details
        }
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "id": error_id,
                "code": error_code,
                "message": message,
                "details": details
            }
        }
    )

# Common error types
class NotFoundError(APIError):
    def __init__(self, message: str = "Resource not found", details: Union[dict, list, None] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details
        )

class ValidationError(APIError):
    def __init__(self, message: str = "Validation error", details: Union[dict, list, None] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )

class AuthenticationError(APIError):
    def __init__(self, message: str = "Authentication failed", details: Union[dict, list, None] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )

class AuthorizationError(APIError):
    def __init__(self, message: str = "Not authorized", details: Union[dict, list, None] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )

class ConflictError(APIError):
    def __init__(self, message: str = "Resource conflict", details: Union[dict, list, None] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
            details=details
        ) 