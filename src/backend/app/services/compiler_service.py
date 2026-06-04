"""
Compiler service layer.

High-level service wrapping the workflow compiler.
Handles workflow JSON → DSL compilation without direct API concerns.
"""
import os
import json
import tempfile
import subprocess
from typing import Optional
from ..compiler.workflow_compiler import compile_workflow_to_dsl, initialize_builders
from ..config import settings, get_logger
from .storage_service import save_dsl


logger = get_logger(__name__)


class CompilerService:
    """
    Service for compiling workflow JSON to Zigflow DSL.

    This service wraps the low-level compiler and provides:
    - Consistent error handling
    - Logging
    - Optional automatic persistence via storage service
    """

    def __init__(self):
        """Initialize the compiler service."""
        # Register all builders on service initialization
        initialize_builders()
        logger.info("CompilerService initialized")

    def compile(
        self,
        workflow: dict,
        workflow_type: str,
        task_queue: str = settings.DEFAULT_TASK_QUEUE,
        dsl_version: str = settings.DEFAULT_DSL_VERSION,
        version: str = "1.0.0",
    ) -> dict:
        """
        Compile workflow JSON to Zigflow DSL.

        Args:
            workflow: Workflow JSON with "nodes" and "edges"
            workflow_type: Temporal workflow type identifier
            task_queue: Temporal task queue name
            dsl_version: DSL specification version
            version: Workflow version

        Returns:
            Complete Zigflow DSL dictionary

        Raises:
            ValueError: If workflow JSON is invalid
            KeyError: If required fields are missing

        Example:
            >>> service = CompilerService()
            >>> dsl = service.compile(
            ...     workflow={"nodes": [...], "edges": [...]},
            ...     workflow_type="order-processing",
            ...     task_queue="orders-queue",
            ... )
        """
        logger.info(f"Compiling workflow: {workflow_type}")

        try:
            # Validate workflow structure
            if "nodes" not in workflow or "edges" not in workflow:
                raise ValueError("Workflow must contain 'nodes' and 'edges' keys")

            # Compile
            dsl = compile_workflow_to_dsl(
                workflow=workflow,
                dsl_version=dsl_version,
                version=version,
                workflow_type=workflow_type,
                task_queue=task_queue,
            )

            # Validate generated DSL using zigflow validate
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(dsl, tmp)
                tmp_path = tmp.name

            try:
                result = subprocess.run(
                    ["zigflow", "validate", tmp_path],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    logger.error(f"Zigflow validation failed for {workflow_type}: {error_msg}")
                    raise ValueError(f"Zigflow validation failed: {error_msg}")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            logger.info(
                f"Compilation successful: {workflow_type} "
                f"({len(workflow['nodes'])} nodes, {len(dsl.get('do', []))} tasks)"
            )

            return dsl

        except Exception as e:
            logger.error(f"Compilation failed for {workflow_type}: {e}", exc_info=True)
            raise

    def compile_and_save(
        self,
        workflow: dict,
        workflow_type: str,
        task_queue: str = settings.DEFAULT_TASK_QUEUE,
        dsl_version: str = settings.DEFAULT_DSL_VERSION,
        version: str = "1.0.0",
        workflow_id: Optional[str] = None,
        custom_filename: Optional[str] = None,
    ) -> dict:
        """
        Compile workflow and save DSL to storage.

        Args:
            workflow: Workflow JSON with "nodes" and "edges"
            workflow_type: Temporal workflow type identifier
            task_queue: Temporal task queue name
            dsl_version: DSL specification version
            version: Workflow version
            workflow_id: Optional workflow identifier (for file naming)
            custom_filename: Optional custom filename for saved DSL

        Returns:
            Dict with keys: workflow_id, dsl, file_path

        Example:
            >>> service = CompilerService()
            >>> result = service.compile_and_save(
            ...     workflow={"nodes": [...], "edges": [...]},
            ...     workflow_type="order-processing",
            ...     workflow_id="order-001",
            ... )
            >>> print(result["file_path"])
            'runtime/compiled/2026/06/02/order-001_20260602_143052.json'
        """
        # Compile
        dsl = self.compile(
            workflow=workflow,
            workflow_type=workflow_type,
            task_queue=task_queue,
            dsl_version=dsl_version,
            version=version,
        )

        # Use workflow_id if provided, else fall back to workflow_type
        save_id = workflow_id or workflow_type

        from .storage_service import calculate_dsl_hash
        content_hash = calculate_dsl_hash(dsl)

        # Save to storage (persisting both .json and .rf.json versioned by content hash)
        file_path = save_dsl(
            dsl=dsl,
            workflow_id=save_id,
            custom_filename=custom_filename,
            rf_json=workflow,
        )

        logger.info(f"DSL saved: {file_path} (hash: {content_hash})")

        return {
            "workflow_id": save_id,
            "dsl": dsl,
            "file_path": file_path,
            "content_hash": content_hash,
        }


# Global service instance
compiler_service = CompilerService()
