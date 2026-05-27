"""Docker service — creates and manages ephemeral execution containers.

Design contract
---------------
- Each call to ``run_workflow_container`` spins up ONE fresh container.
- The container runs exactly ONE Zigflow workflow then exits.
- Containers are removed after exit regardless of success or failure (``--rm``
  equivalent via explicit ``container.remove(force=True)`` in the finally block).
- The caller receives a structured result tuple; it never touches Docker objects.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container

from app.utils.config import get_settings

logger = logging.getLogger(__name__)


class DockerService:
    """Manages ephemeral Docker containers for isolated workflow execution."""

    def __init__(self) -> None:
        self._client = docker.from_env()

    # ── Public API ────────────────────────────────────────────────────────────

    async def run_workflow_container(
        self,
        workflow: str,
        workflow_path: str,
        input_data: Dict[str, Any],
        execution_id: str,
        timeout_secs: int = 3600,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], List[str], Optional[str]]:
        """Spin up an ephemeral runner container and wait for it to finish.

        Returns
        -------
        (container_id, result_dict, log_lines, error_message)
        ``result_dict`` is populated on success; ``error_message`` on failure.
        """
        settings = get_settings()
        container: Optional[Container] = None
        container_id: Optional[str] = None

        try:
            cmd = self._build_command(workflow, workflow_path, input_data, execution_id, settings)
            volumes = self._build_volumes(settings)
            environment = self._build_environment(execution_id, settings)
            logger.info(
                "Creating runner container",
                extra={"workflow": workflow, "execution_id": execution_id},
            )

            loop = asyncio.get_event_loop()

            # Container creation is a blocking SDK call — offload to thread pool
            container = await loop.run_in_executor(
                None,
                lambda: self._client.containers.create(
                    image=settings.RUNNER_IMAGE,
                    command=cmd,
                    volumes=volumes,
                    network=settings.DOCKER_NETWORK,
                    environment=environment,
                    detach=True,
                    auto_remove=False,  # removed explicitly in finally block
                    labels={
                        "managed-by": "zigflow-orchestrator",
                        "execution-id": execution_id,
                        "workflow": workflow,
                    },
                ),
            )
            container_id = container.id[:12]
            logger.info("Container created: %s", container_id)

            # Start
            await loop.run_in_executor(None, container.start)
            logger.info("Container started: %s", container_id)

            # Wait with overall timeout guard
            exit_result = await asyncio.wait_for(
                loop.run_in_executor(None, container.wait),
                timeout=float(timeout_secs),
            )
            exit_code: int = exit_result.get("StatusCode", -1)

            # Collect stdout + stderr
            raw_logs: bytes = await loop.run_in_executor(
                None, lambda: container.logs(stdout=True, stderr=True)
            )
            log_lines = raw_logs.decode("utf-8", errors="replace").strip().splitlines()

            result, error = self._parse_output(exit_code, log_lines, container_id)
            return container_id, result, log_lines, error

        except asyncio.TimeoutError:
            err = f"Container timed out after {timeout_secs}s"
            logger.error("Container %s timed out after %ss", container_id, timeout_secs)
            if container:
                await self._kill_container(container)
            return container_id, None, [], err

        except ImageNotFound:
            err = (
                f"Runner image '{get_settings().RUNNER_IMAGE}' not found. "
                "Build it with: docker build -f docker/Dockerfile.runner -t zigflow-runner:latest ."
            )
            logger.error(err)
            return container_id, None, [], err

        except DockerException as exc:
            err = f"Docker error: {exc}"
            logger.error(err)
            return container_id, None, [], err

        finally:
            if container:
                await self._remove_container(container, container_id)

    def health_check(self) -> bool:
        """Return True if the Docker daemon is reachable."""
        try:
            self._client.ping()
            return True
        except DockerException:
            return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_command(
        workflow: str,
        workflow_path: str,
        input_data: Dict[str, Any],
        execution_id: str,
        settings: Any,
    ) -> List[str]:
        return [
            "python", "/runner/run_workflow.py",
            "--workflow", workflow,
            "--workflow-path", workflow_path,
            "--input", json.dumps(input_data),
            "--execution-id", execution_id,
            "--temporal-host", settings.DOCKER_TEMPORAL_HOST,
            "--namespace", settings.TEMPORAL_NAMESPACE,
        ]

    @staticmethod
    def _build_volumes(settings: Any) -> Dict[str, Dict[str, str]]:
        # Mount the host workflows directory into the container as read-only
        return {
            settings.WORKFLOWS_DIR: {
                "bind": "/app/workflows/json",
                "mode": "ro",
            }
        }

    @staticmethod
    def _build_environment(execution_id: str, settings: Any) -> Dict[str, str]:
        return {
            "TEMPORAL_HOST": settings.DOCKER_TEMPORAL_HOST,
            "TEMPORAL_NAMESPACE": settings.TEMPORAL_NAMESPACE,
            "EXECUTION_ID": execution_id,
        }

    @staticmethod
    def _parse_output(
        exit_code: int,
        log_lines: List[str],
        container_id: Optional[str],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Extract the JSON result printed as the last stdout line."""
        if exit_code != 0:
            logger.error("Container %s exited with code %d", container_id, exit_code)
            return None, f"Container exited with code {exit_code}"

        # Scan from the end for the first JSON object line (the runner outputs
        # structured JSON as its very last stdout line)
        for line in reversed(log_lines):
            stripped = line.strip()
            if stripped.startswith("{"):
                try:
                    return json.loads(stripped), None
                except json.JSONDecodeError:
                    pass

        # Fallback: return raw output as a string result
        return {"raw_output": "\n".join(log_lines)}, None

    @staticmethod
    async def _kill_container(container: Container) -> None:
        try:
            await asyncio.get_event_loop().run_in_executor(None, container.kill)
        except Exception as exc:
            logger.warning("Could not kill container: %s", exc)

    @staticmethod
    async def _remove_container(
        container: Container, container_id: Optional[str]
    ) -> None:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: container.remove(force=True)
            )
            logger.info("Container %s removed", container_id)
        except Exception as exc:
            logger.warning("Could not remove container %s: %s", container_id, exc)
