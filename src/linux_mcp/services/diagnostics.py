from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any


def _redact(value: str | None) -> str:
    if not value:
        return ""
    redacted = value
    for pattern in [r"(Authorization: )[A-Za-z0-9._:-]+", r"(token=)[A-Za-z0-9._:-]+", r"(password=)[A-Za-z0-9._:-]+", r"(secret=)[A-Za-z0-9._:-]+"]:
        redacted = re.sub(pattern, r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
    return redacted


def check_dependencies(requirements: list[str] | str | None) -> dict[str, Any]:
    """Check whether required executables are present and return missing ones only."""
    if requirements is None:
        return {"success": True, "missing": [], "present": []}
    if isinstance(requirements, str):
        requirements = [requirements]

    missing: list[str] = []
    present: list[str] = []
    for requirement in requirements:
        resolved = shutil.which(requirement)
        if resolved:
            present.append(requirement)
        else:
            missing.append(requirement)

    return {
        "success": not missing,
        "missing": missing,
        "present": present,
        "evidence": [{"type": "executable", "name": item, "available": item in present} for item in requirements],
    }


def check_permissions(path: str) -> dict[str, Any]:
    """Inspect file mode bits and ownership to identify permission issues without broad recursive changes."""
    if not path:
        return {"success": True, "path": path, "issues": [], "warnings": []}

    try:
        stat_result = os.stat(path)
    except OSError as exc:
        return {"success": False, "path": path, "issues": [{"type": "stat_failed", "message": str(exc)}], "warnings": []}

    mode = stat_result.st_mode
    issues: list[dict[str, Any]] = []
    warnings: list[str] = []

    if mode & 0o0777 == 0o0777:
        issues.append({"type": "world_writable", "path": path, "mode": oct(mode & 0o777)})
    if mode & 0o02000:
        warnings.append("The target is setuid/setgid; review whether this is required and acceptable.")
    if stat_result.st_uid == 0:
        warnings.append("The target is owned by root. Verify whether the installation or launch path requires root ownership.")

    return {"success": not issues, "path": path, "issues": issues, "warnings": warnings}


def diagnose_installation(package_name: str, log_output: str | None = None) -> dict[str, Any]:
    """Collect evidence associated with a failed installation and classify the likely cause."""
    evidence: list[dict[str, Any]] = []
    if log_output:
        evidence.append({"source": "install_log", "message": _redact(log_output)})
    else:
        try:
            result = subprocess.run(["apt-get", "install", "-y", package_name], capture_output=True, text=True, timeout=30, check=False)
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            return {"success": False, "classification": "install_command_failed", "error_message": str(exc), "evidence": [{"source": "apt-get", "message": str(exc)}]}

        evidence.append({"source": "apt-get", "message": _redact(result.stderr or result.stdout or "No diagnostic output available.")})
        if result.returncode == 100 or "Unable to locate package" in (result.stderr or ""):
            return {"success": False, "classification": "package_not_found", "error_message": "Package is not available in the configured repositories.", "evidence": evidence}
        if result.returncode != 0:
            return {"success": False, "classification": "installation_failure", "error_message": result.stderr.strip() or result.stdout.strip() or "Installation failed.", "evidence": evidence}

    return {"success": True, "classification": "installation_ok", "error_message": "No installation failure detected.", "evidence": evidence}


def diagnose_application(command: str) -> dict[str, Any]:
    """Collect evidence from runtime failures when an application fails to start."""
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=20, check=False)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return {"success": False, "classification": "launch_command_failed", "error_message": str(exc), "evidence": [{"source": "command", "message": str(exc)}]}

    stderr = result.stderr.strip() or result.stdout.strip() or "No output captured."
    if result.returncode == 127 or "command not found" in stderr.lower():
        return {"success": False, "classification": "missing_runtime_dependency", "error_message": "The application command or one of its runtime dependencies is missing.", "evidence": [{"source": "runtime", "message": _redact(stderr)}]}
    if result.returncode != 0:
        return {"success": False, "classification": "launch_failure", "error_message": stderr, "evidence": [{"source": "runtime", "message": _redact(stderr)}]}

    return {"success": True, "classification": "launch_ok", "error_message": "Application launch did not fail.", "evidence": [{"source": "runtime", "message": _redact(stderr)}]}


def get_operation_logs(command: str, max_lines: int = 20) -> dict[str, Any]:
    """Return a bounded set of log lines for a known operation without exposing the full raw stream."""
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=20, check=False)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return {"success": False, "error_message": str(exc), "data": {"lines": []}}

    lines = (result.stdout or result.stderr or "").splitlines()[:max_lines]
    return {"success": True, "data": {"command": command, "lines": lines, "truncated": len(lines) >= max_lines}}


def propose_remediation(diagnostic: dict[str, Any]) -> dict[str, Any]:
    """Turn classified evidence into a narrow, structured remediation plan."""
    classification = diagnostic.get("classification")
    evidence = diagnostic.get("evidence") or []

    if classification == "package_not_found":
        actions = [
            {"type": "check_repository", "action": "Verify the apt source lists and update package metadata.", "evidence": evidence},
            {"type": "search_candidate", "action": "Check whether the package name differs from the expected distribution package.", "evidence": evidence},
        ]
    elif classification == "missing_runtime_dependency":
        actions = [
            {"type": "install_dependency", "action": "Install the missing runtime dependency or package that provides the missing binary.", "evidence": evidence},
            {"type": "verify_binary", "action": "Confirm the binary is now available on PATH.", "evidence": evidence},
        ]
    else:
        actions = [
            {"type": "collect_evidence", "action": "Capture the exact command output and package metadata for the failing step.", "evidence": evidence},
            {"type": "verify_permissions", "action": "Review permissions and ownership on the affected installation path.", "evidence": evidence},
        ]

    return {"success": True, "classification": classification, "actions": actions}
