"""
FastAPI dependency: service factory functions.
Services are singletons or request-scoped depending on the service's needs.
"""
from src.service.compiler_service import compiler_service as _compiler_service
from src.service.registration_service import registration_service as _registration_service
from src.service.execution_service import ExecutionService


def get_compiler_service():
    return _compiler_service


def get_registration_service():
    return _registration_service


def get_execution_service() -> ExecutionService:
    return ExecutionService()
