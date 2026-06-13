"""
Storage service for DSL file persistence.

Primary store: filesystem under runtime/compiled/ (Zigflow file watcher reads from here).
Secondary store: PostgreSQL via WorkflowVersionRepo + WorkflowRepo (dual-write).
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from ..config import settings, get_logger


logger = get_logger(__name__)


def calculate_dsl_hash(dsl: dict) -> str:
    """
    Calculate a deterministic 16-character SHA-256 content hash of the compiled DSL.
    """
    import hashlib
    dsl_bytes = json.dumps(dsl, sort_keys=True).encode("utf-8")
    return hashlib.sha256(dsl_bytes).hexdigest()[:16]


def save_dsl(
    dsl: dict,
    workflow_id: Optional[str] = None,
    custom_filename: Optional[str] = None,
    rf_json: Optional[dict] = None,
) -> Path:
    """
    Save compiled DSL to resources/compiled/ with date-based folder structure.

    Directory structure:
        resources/compiled/YYYY/MM/DD/wf-{dsl_hash}.json

    Args:
        dsl: Complete Zigflow DSL dictionary
        workflow_id: Optional workflow identifier (included in filename if provided)
        custom_filename: Optional custom filename (overrides default naming)
        rf_json: Optional ReactFlow representation dictionary to save alongside DSL

    Returns:
        Path to saved file
    """
    now = datetime.now(timezone.utc)

    # Calculate deterministic SHA-256 content hash of DSL
    dsl_hash = calculate_dsl_hash(dsl)

    # Create date-based directory structure: YYYY/MM/DD
    year_dir = settings.COMPILED_DIR / str(now.year)
    month_dir = year_dir / f"{now.month:02d}"
    day_dir = month_dir / f"{now.day:02d}"

    # Ensure directories exist
    day_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with hash suffix to guarantee version safety
    if custom_filename:
        # Strip extension if provided
        base_name = custom_filename[:-5] if custom_filename.endswith('.json') else custom_filename
        filename = f"{base_name}-{dsl_hash}.json"
    else:
        prefix = workflow_id if workflow_id else "wf"
        filename = f"{prefix}-{dsl_hash}.json"

    # Full file path
    file_path = day_dir / filename

    # Write DSL to file
    with file_path.open('w', encoding='utf-8') as f:
        json.dump(dsl, f, indent=2, ensure_ascii=False)

    logger.info(f"DSL saved to: {file_path} (hash: {dsl_hash})")

    # Save active/latest version to flat 'active' directory
    try:
        active_dir = settings.COMPILED_DIR / "active"
        active_dir.mkdir(parents=True, exist_ok=True)
        if custom_filename:
            active_filename = custom_filename if custom_filename.endswith('.json') else f"{custom_filename}.json"
        else:
            active_filename = f"{workflow_id or 'wf'}.json"
        active_path = active_dir / active_filename
        with active_path.open('w', encoding='utf-8') as f:
            json.dump(dsl, f, indent=2, ensure_ascii=False)
        logger.info(f"Active DSL saved to: {active_path}")
    except Exception as e:
        logger.error(f"Failed to save copy to active directory: {e}")

    # If original ReactFlow JSON is provided, save it under same hash name
    if rf_json:
        rf_filename = filename.replace(".json", ".rf")
        rf_path = day_dir / rf_filename
        with rf_path.open('w', encoding='utf-8') as f:
            json.dump(rf_json, f, indent=2, ensure_ascii=False)
        logger.info(f"ReactFlow schema saved to: {rf_path}")

    return file_path


def find_by_hash(workflow_id: str, dsl_hash: str, ext: str = ".json") -> Optional[Path]:
    """
    Find a compiled or ReactFlow file by its workflow ID and DSL hash.

    Args:
        workflow_id: Visual design ID of the workflow
        dsl_hash: 16-character content hash
        ext: Target extension (.json or .rf.json)

    Returns:
        Path to file if found, otherwise None
    """
    # Scope search to pattern containing BOTH workflow_id and dsl_hash to prevent collision
    matches = list(settings.COMPILED_DIR.glob(f"**/*{workflow_id}*-{dsl_hash}{ext}"))
    if matches:
        return matches[0]
    return None


def load_dsl(file_path: str | Path) -> dict:
    """
    Load compiled DSL from file.

    Args:
        file_path: Path to DSL JSON file (absolute or relative to compiled/)

    Returns:
        Loaded DSL dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON

    Example:
        >>> dsl = load_dsl("2026/06/02/wf_20260602_143052.json")
        >>> dsl = load_dsl("/full/path/to/workflow.json")
    """
    path = Path(file_path)

    # If relative path, resolve against compiled directory
    if not path.is_absolute():
        path = settings.COMPILED_DIR / path

    if not path.exists():
        logger.error(f"DSL file not found: {path}")
        raise FileNotFoundError(f"DSL file not found: {path}")

    with path.open('r', encoding='utf-8') as f:
        dsl = json.load(f)

    logger.info(f"DSL loaded from: {path}")

    return dsl


def list_compiled_workflows(
    date: Optional[datetime] = None,
) -> list[Path]:
    """
    List all compiled workflow files, optionally filtered by date.

    Args:
        date: Optional date to filter by (defaults to today)

    Returns:
        List of Path objects to DSL files

    Example:
        >>> workflows = list_compiled_workflows()  # Today's workflows
        >>> workflows = list_compiled_workflows(datetime(2026, 6, 1))  # Specific date
    """
    if date is None:
        date = datetime.now(timezone.utc)

    day_dir = (
        settings.COMPILED_DIR
        / str(date.year)
        / f"{date.month:02d}"
        / f"{date.day:02d}"
    )

    if not day_dir.exists():
        logger.info(f"No workflows found for {date.date()}")
        return []

    workflows = sorted([w for w in day_dir.glob("*.json") if not w.name.endswith(".rf.json")])
    logger.info(f"Found {len(workflows)} workflows for {date.date()}")

    return workflows


def get_latest_workflow(workflow_id: Optional[str] = None) -> Optional[Path]:
    """
    Get the most recently compiled workflow file.

    Args:
        workflow_id: Optional workflow ID to filter by

    Returns:
        Path to latest workflow file, or None if no workflows exist

    Example:
        >>> latest = get_latest_workflow()
        >>> latest = get_latest_workflow(workflow_id="order-flow")
    """
    from datetime import timedelta
    # Search in reverse chronological order (last 30 days)
    for days_ago in range(30):
        date = datetime.now(timezone.utc) - timedelta(days=days_ago)

        workflows = list_compiled_workflows(date)

        if workflow_id:
            # Filter by workflow ID
            workflows = [w for w in workflows if workflow_id in w.stem]

        if workflows:
            return workflows[-1]  # Most recent file for that day

    logger.warning("No workflows found in the last 30 days")
    return None


async def save_dsl_to_db(
    dsl: dict,
    workflow_id: str,
    workflow_type: str,
    task_queue: str,
    file_path: str,
    rf_json: Optional[dict] = None,
) -> None:
    """
    Dual-write: persist a compiled DSL as Workflow + WorkflowVersion in PostgreSQL.
    Called as a fire-and-forget background task after save_dsl() succeeds.
    """
    try:
        from ..config.db_config import get_session_factory
        from ..repo.workflow_repo import WorkflowRepo
        from ..repo.workflow_version_repo import WorkflowVersionRepo
        from ..model.workflow_version import WorkflowVersion

        content_hash = calculate_dsl_hash(dsl)
        workflow_repo = WorkflowRepo()
        version_repo = WorkflowVersionRepo()

        async with get_session_factory()() as session:
            workflow = await workflow_repo.get_or_create(
                workflow_id=workflow_id,
                name=workflow_id.replace("-", " ").title(),
                db=session,
            )

            existing = await version_repo.get_by_hash(content_hash, session)
            if existing is None:
                version = WorkflowVersion(
                    workflow_id=workflow.id,
                    content_hash=content_hash,
                    dsl_json=dsl,
                    rf_json=rf_json,
                    file_path=file_path,
                    workflow_type=workflow_type,
                    task_queue=task_queue,
                )
                await version_repo.save(version, session)

            await session.commit()
            logger.debug(f"DSL persisted to DB: workflow_id={workflow_id} hash={content_hash}")
    except Exception as exc:
        logger.warning(f"DB dual-write for DSL {workflow_id} failed (non-fatal): {exc}")
