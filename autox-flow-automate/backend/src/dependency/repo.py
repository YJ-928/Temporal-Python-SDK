"""
FastAPI dependency: repo factory functions.
"""
from src.repo.workflow_repo import WorkflowRepo
from src.repo.workflow_version_repo import WorkflowVersionRepo
from src.repo.workflow_registration_repo import WorkflowRegistrationRepo
from src.repo.workflow_run_repo import WorkflowRunRepo


def get_workflow_repo() -> WorkflowRepo:
    return WorkflowRepo()


def get_workflow_version_repo() -> WorkflowVersionRepo:
    return WorkflowVersionRepo()


def get_workflow_registration_repo() -> WorkflowRegistrationRepo:
    return WorkflowRegistrationRepo()


def get_workflow_run_repo() -> WorkflowRunRepo:
    return WorkflowRunRepo()
