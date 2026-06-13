"""
Registers exception handlers on the FastAPI app.
Called once from src/app.py.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from .custom_exception import FlowAutomateException, NotFoundException, ConflictException


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "msg_code": "INVALID_PAYLOAD",
                "message": "Validation error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "msg_code": "INVALID_PAYLOAD",
                "message": "Validation error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={"success": False, "msg_code": exc.msg_code, "message": exc.msg},
        )

    @app.exception_handler(ConflictException)
    async def conflict_handler(request: Request, exc: ConflictException):
        return JSONResponse(
            status_code=409,
            content={"success": False, "msg_code": exc.msg_code, "message": exc.msg},
        )

    @app.exception_handler(FlowAutomateException)
    async def flowautomate_error_handler(request: Request, exc: FlowAutomateException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "msg_code": exc.msg_code, "message": exc.msg},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "msg_code": "BAD_REQUEST", "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def catch_all_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "msg_code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"},
        )
