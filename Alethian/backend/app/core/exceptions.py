from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime

class AlethianException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code

async def alethian_exception_handler(request: Request, exc: AlethianException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

from fastapi.encoders import jsonable_encoder

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Input validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": jsonable_encoder(exc.errors()),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
