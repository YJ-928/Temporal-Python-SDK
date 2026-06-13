"""
Standard API response envelope.
Generic[T] gives type-safe response_model= annotations.
"""
from typing import Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    msg_code: str | None = None
    message: str | None = None
    body: T | None = None

    @staticmethod
    def ok(body: T, message: str | None = None, msg_code: str | None = None) -> "ApiResponse[T]":
        return ApiResponse(success=True, body=body, message=message, msg_code=msg_code)

    @staticmethod
    def error(message: str, msg_code: str | None = None) -> "ApiResponse[Any]":
        return ApiResponse(success=False, message=message, msg_code=msg_code)
