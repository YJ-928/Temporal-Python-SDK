from pydantic_settings import BaseSettings


class CompilerSettings(BaseSettings):
    """Compiler defaults — all values sourced from .env."""

    COMPILER_WORKFLOW_TYPE: str = "flowautomate"
    COMPILER_TASK_QUEUE: str = "flowautomate"
    COMPILER_DSL_VERSION: str = "1.0.0"
    COMPILER_WORKFLOW_VERSION: str = "1.0.0"

    # Expose lowercase aliases used throughout the compiler pipeline
    @property
    def workflow_type(self) -> str:
        return self.COMPILER_WORKFLOW_TYPE

    @property
    def task_queue(self) -> str:
        return self.COMPILER_TASK_QUEUE

    @property
    def dsl_version(self) -> str:
        return self.COMPILER_DSL_VERSION

    @property
    def workflow_version(self) -> str:
        return self.COMPILER_WORKFLOW_VERSION

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


compiler_settings = CompilerSettings()
