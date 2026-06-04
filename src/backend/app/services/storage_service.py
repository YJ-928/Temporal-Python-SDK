"""
Storage service for DSL file persistence.

Handles saving and loading compiled DSL files with date-based organization.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from ..config import settings, get_logger


logger = get_logger(__name__)


def save_dsl(
    dsl: dict,
    workflow_id: Optional[str] = None,
    custom_filename: Optional[str] = None,
) -> Path:
    """
    Save compiled DSL to resources/compiled/ with date-based folder structure.

    Directory structure:
        resources/compiled/YYYY/MM/DD/wf_YYYYMMDD_HHMMSS.json

    Args:
        dsl: Complete Zigflow DSL dictionary
        workflow_id: Optional workflow identifier (included in filename if provided)
        custom_filename: Optional custom filename (overrides default naming)

    Returns:
        Path to saved file

    Example:
        >>> save_dsl(my_dsl)
        Path('resources/compiled/2026/06/02/wf_20260602_143052.json')

        >>> save_dsl(my_dsl, workflow_id="order-flow")
        Path('resources/compiled/2026/06/02/order-flow_20260602_143052.json')
    """
    now = datetime.now()

    # Create date-based directory structure: YYYY/MM/DD
    year_dir = settings.COMPILED_DIR / str(now.year)
    month_dir = year_dir / f"{now.month:02d}"
    day_dir = month_dir / f"{now.day:02d}"

    # Ensure directories exist
    day_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    if custom_filename:
        filename = custom_filename if custom_filename.endswith('.json') else f"{custom_filename}.json"
    else:
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        if workflow_id:
            filename = f"{workflow_id}_{timestamp}.json"
        else:
            filename = f"wf_{timestamp}.json"

    # Full file path
    file_path = day_dir / filename

    # Write DSL to file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(dsl, f, indent=2, ensure_ascii=False)

    logger.info(f"DSL saved to: {file_path}")

    return file_path


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

    with open(path, 'r', encoding='utf-8') as f:
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
        date = datetime.now()

    day_dir = (
        settings.COMPILED_DIR
        / str(date.year)
        / f"{date.month:02d}"
        / f"{date.day:02d}"
    )

    if not day_dir.exists():
        logger.info(f"No workflows found for {date.date()}")
        return []

    workflows = sorted(day_dir.glob("*.json"))
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
    # Search in reverse chronological order (last 30 days)
    for days_ago in range(30):
        date = datetime.now()
        date = date.replace(day=date.day - days_ago) if days_ago > 0 else date

        workflows = list_compiled_workflows(date)

        if workflow_id:
            # Filter by workflow ID
            workflows = [w for w in workflows if workflow_id in w.stem]

        if workflows:
            return workflows[-1]  # Most recent file for that day

    logger.warning("No workflows found in the last 30 days")
    return None
