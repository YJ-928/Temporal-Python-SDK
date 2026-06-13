from pydantic_settings import BaseSettings

class CompilerSettings(BaseSettings):
    workflow_type: str = "workflow-builder"
    task_queue: str = "workflow-builder"
    dsl_version: str = "1.0.0"
    workflow_version: str = "1.0.0"

    class Config:
        env_prefix = ""

compiler_settings = CompilerSettings()
