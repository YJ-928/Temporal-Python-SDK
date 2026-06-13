"""
Shared (cross-domain) API messages.
"""
from enum import Enum
from .api_msg import Message


class SharedAPIMsg(Enum):
    NOT_FOUND = Message("NOT_FOUND", "Resource not found.")
    INTERNAL_SERVER_ERROR = Message("INTERNAL_SERVER_ERROR", "Unexpected error occurred.")
    UNAUTHORIZED = Message("UNAUTHORIZED", "Unauthorized.")
    FORBIDDEN = Message("FORBIDDEN", "Forbidden.")
    CONFLICT = Message("CONFLICT", "Resource already exists.")
    VALIDATION_ERROR = Message("VALIDATION_ERROR", "Validation error.")
