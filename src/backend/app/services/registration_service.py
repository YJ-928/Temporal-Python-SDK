"""
Registration service for tracking and reloading Zigflow workflows.
"""
import os
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from ..config import settings, get_logger
from .storage_service import calculate_dsl_hash, load_dsl

logger = get_logger(__name__)

WORKSPACE_ROOT = settings.BACKEND_ROOT
REGISTRATIONS_FILE = WORKSPACE_ROOT / "runtime" / "registrations.json"


class RegistrationService:
    """
    Manages workflow registrations tracking and hot-reloading the Zigflow daemon.
    """

    def __init__(self):
        self.lock = asyncio.Lock()
        self.reload_in_progress = False
        self.reload_pending = False
        self._ensure_registrations_file()

    def _ensure_registrations_file(self):
        """Ensure runtime/ directory and registrations.json file exist."""
        try:
            REGISTRATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not REGISTRATIONS_FILE.exists():
                with open(REGISTRATIONS_FILE, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to create registrations file: {e}")

    def get_all_registrations(self) -> Dict[str, Any]:
        """Retrieve all workflow registrations."""
        self._ensure_registrations_file()
        try:
            with open(REGISTRATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read registrations file: {e}")
            return {}

    def _save_registrations(self, regs: Dict[str, Any]):
        """Save registrations map back to registrations.json."""
        self._ensure_registrations_file()
        try:
            with open(REGISTRATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(regs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registrations file: {e}")

    def _mark_all_loaded(self):
        """Mark all successfully registered entries as runtime_loaded=True."""
        regs = self.get_all_registrations()
        for k in regs:
            if regs[k].get("registered", False):
                regs[k]["runtime_loaded"] = True
        self._save_registrations(regs)

    def is_registered(self, dsl_hash: str) -> bool:
        """Check if a workflow is registered."""
        regs = self.get_all_registrations()
        entry = regs.get(dsl_hash)
        return entry is not None and entry.get("registered", False)

    def is_runtime_loaded(self, dsl_hash: str) -> bool:
        """Check if a workflow has been hot-reloaded into the runtime daemon."""
        regs = self.get_all_registrations()
        entry = regs.get(dsl_hash)
        return entry is not None and entry.get("runtime_loaded", False)

    def register_workflow(
        self,
        dsl_hash: str,
        workflow_id: str,
        workflow_type: str,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Register a new workflow and schedule a hot-reload of the runtime.
        """
        regs = self.get_all_registrations()
        entry = regs.get(dsl_hash)

        if entry and entry.get("registered") and entry.get("validated"):
            # Already validated and registered, just check if loaded
            if not entry.get("runtime_loaded"):
                asyncio.create_task(self.trigger_reload())
            return entry

        # Run zigflow validation as a safety check
        validated = self._validate_dsl_file(file_path)

        new_entry = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "validated": validated,
            "registered": True if validated else False,
            "runtime_loaded": False,
            "registered_at": datetime.utcnow().isoformat() + "Z"
        }

        regs[dsl_hash] = new_entry
        self._save_registrations(regs)

        # Trigger background non-blocking daemon reload only if valid
        if validated:
            asyncio.create_task(self.trigger_reload())

        return new_entry

    def _validate_dsl_file(self, file_path: Path) -> bool:
        """Run zigflow validate command against the generated file."""
        try:
            result = subprocess.run(
                ["zigflow", "validate", str(file_path)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error(f"Zigflow validate failed for {file_path}: {result.stderr.strip()}")
                return False
            return True
        except Exception as e:
            logger.error(f"Validation runner crashed: {e}")
            return False

    async def trigger_reload(self):
        """
        Background task to reload/restart the runtime worker.
        Implements reload batching using a lock and reload-pending flag.
        """
        async with self.lock:
            if self.reload_in_progress:
                self.reload_pending = True
                return
            self.reload_in_progress = True

        try:
            while True:
                logger.info("Hot-reloading Zigflow Runtime Daemon...")
                
                # Stop runtime daemon
                stop_script = WORKSPACE_ROOT / "scripts" / "stop_runtime.sh"
                proc_stop = await asyncio.create_subprocess_exec(
                    "bash", str(stop_script)
                )
                await proc_stop.wait()

                # Start runtime daemon
                start_script = WORKSPACE_ROOT / "scripts" / "start_runtime.sh"
                proc_start = await asyncio.create_subprocess_exec(
                    "bash", str(start_script)
                )
                await proc_start.wait()

                logger.info("Zigflow Runtime Daemon reloaded successfully.")

                # Update status of registrations
                self._mark_all_loaded()

                async with self.lock:
                    if self.reload_pending:
                        self.reload_pending = False
                        # Loop again to perform another reload batch
                        continue
                    else:
                        self.reload_in_progress = False
                        break
        except Exception as e:
            logger.error(f"Failed reloading Zigflow daemon in background: {e}")
            async with self.lock:
                self.reload_in_progress = False
                self.reload_pending = False

    async def sync_pre_existing(self):
        """
        Scan compiled directory on backend startup and register pre-existing workflows.
        """
        logger.info("Syncing pre-existing compiled workflows...")
        compiled_dir = settings.COMPILED_DIR
        if not compiled_dir.exists():
            return

        regs = self.get_all_registrations()
        has_new = False

        # Scan recursively
        for path in compiled_dir.glob("**/*.json"):
            if "active" in path.parts:
                continue
            if path.name.endswith(".rf.json") or path.name.endswith("registrations.json"):
                continue
            
            try:
                dsl = load_dsl(path)
                doc = dsl.get("document", {})
                workflow_type = doc.get("workflowType")
                
                parts = path.stem.split("-")
                workflow_id = "-".join(parts[:-1]) if len(parts) > 1 else path.stem
                
                if not workflow_type:
                    continue

                dsl_hash = calculate_dsl_hash(dsl)
                if dsl_hash not in regs:
                    # Validate
                    validated = self._validate_dsl_file(path)
                    regs[dsl_hash] = {
                        "workflow_id": workflow_id,
                        "workflow_type": workflow_type,
                        "validated": validated,
                        "registered": True if validated else False,
                        "runtime_loaded": False,
                        "registered_at": datetime.utcnow().isoformat() + "Z"
                    }
                    has_new = True
                    logger.info(f"Synced workflow version {workflow_type} (hash: {dsl_hash})")
            except Exception as e:
                logger.warning(f"Failed parsing file {path} during sync: {e}")

        if has_new:
            self._save_registrations(regs)
            # Reload to load synced files
            await self.trigger_reload()


# Global Registration Service instance
registration_service = RegistrationService()
