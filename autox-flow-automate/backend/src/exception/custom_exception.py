"""
Typed business exception classes raised in service layer code.
Services raise these; the handler layer converts them to HTTP responses.
"""


class FlowAutomateException(Exception):
    def __init__(self, msg: str, msg_code: str | None = None, status_code: int = 500):
        self.msg = msg
        self.msg_code = msg_code
        self.status_code = status_code
        super().__init__(msg)


class NotFoundException(FlowAutomateException):
    def __init__(self, msg: str = "Resource not found.", msg_code: str = "NOT_FOUND"):
        super().__init__(msg, msg_code, status_code=404)


class ConflictException(FlowAutomateException):
    def __init__(self, msg: str, msg_code: str = "CONFLICT"):
        super().__init__(msg, msg_code, status_code=409)


class ValidationException(FlowAutomateException):
    def __init__(self, msg: str, msg_code: str = "VALIDATION_ERROR"):
        super().__init__(msg, msg_code, status_code=422)


class ServiceUnavailableException(FlowAutomateException):
    def __init__(self, msg: str, msg_code: str = "SERVICE_UNAVAILABLE"):
        super().__init__(msg, msg_code, status_code=503)
