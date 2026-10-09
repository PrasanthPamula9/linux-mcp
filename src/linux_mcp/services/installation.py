from __future__ import annotations

import hashlib
import ipaddress
import re
import shutil
import subprocess
import tempfile
import urllib.request
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_OPERATION_STORE: dict[str, dict[str, Any]] = {}


class OperationTracker:
    """Simple in-memory tracker for installation operations."""

    @staticmethod
    def create(package_name: str, source: str) -> str:
        operation_id = str(uuid.uuid4())
        _OPERATION_STORE[operation_id] = {
            "operation_id": operation_id,
            "package": package_name,
            "source": source,
            "status": "PENDING",
            "started_at": None,
            "completed_at": None,
            "exit_code": None,
            "error_classification": None,
            "diagnostic_evidence": [],
            "verification": None,
        }
        return operation_id

    @staticmethod
    def update(operation_id: str, status: str | None = None, **kwargs: Any) -> dict[str, Any]:
        entry = _OPERATION_STORE.setdefault(operation_id, {"operation_id": operation_id})
        if status is not None:
            entry["status"] = status
        for key, value in kwargs.items():
            if value is not None:
                entry[key] = value
        return entry

    @staticmethod
    def get(operation_id: str) -> dict[str, Any] | None:
        return _OPERATION_STORE.get(operation_id)


def validate_download_url(url: str) -> dict[str, Any]:
    """Reject local, private, or metadata endpoints before any download is attempted."""
    if not url or not url.strip():
        return {"success": False, "error_code": "invalid_url", "error_message": "A download URL is required."}

    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return {"success": False, "error_code": "invalid_url", "error_message": "Only http and https download URLs are allowed."}

    host = (parsed.hostname or "").lower()
    if not host:
        return {"success": False, "error_code": "invalid_url", "error_message": "The URL does not include a valid hostname."}

    blocked_hosts = {"localhost", "localhost.localdomain", "metadata.google.internal", "169.254.169.254", "metadata.google.internal"}
    if host in blocked_hosts or host.endswith(".localhost") or host.endswith(".internal"):
        return {"success": False, "error_code": "blocked_destination", "error_message": "Refusing to connect to local or internal network targets."}

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None and (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return {"success": False, "error_code": "blocked_destination", "error_message": "Refusing to connect to non-public network targets."}

    return {"success": True, "url": url, "host": host}


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_destination(destination: str | None) -> Path:
    if destination:
        path = Path(destination)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    default_name = "download.bin"
    return Path(tempfile.gettempdir()) / default_name


def download_software(
    url: str,
    destination: str | None = None,
    expected_sha256: str | None = None,
    max_bytes: int = 250 * 1024 * 1024,
    timeout: int = 30,
) -> dict[str, Any]:
    """Download a file from an approved URL and validate size and content hash."""
    validation = validate_download_url(url)
    if not validation["success"]:
        return validation

    target_path = _validate_destination(destination)

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, open(target_path, "wb") as handle:
            total_bytes = 0
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise ValueError(f"Download exceeded the configured size limit of {max_bytes} bytes.")
                handle.write(chunk)
    except ValueError as exc:
        return {
            "success": False,
            "error_code": "download_size_limit_exceeded",
            "error_message": str(exc),
            "data": {"path": str(target_path)},
        }
    except Exception as exc:  # pragma: no cover - external IO failure path
        return {
            "success": False,
            "error_code": "download_failed",
            "error_message": str(exc),
            "data": {"path": str(target_path)},
        }

    sha256 = _sha256_file(target_path)
    if expected_sha256 and sha256.lower() != expected_sha256.lower():
        return {
            "success": False,
            "error_code": "checksum_mismatch",
            "error_message": "Downloaded file hash does not match the expected value.",
            "data": {"path": str(target_path), "sha256": sha256},
        }

    return {
        "success": True,
        "data": {"path": str(target_path), "sha256": sha256, "bytes_downloaded": total_bytes if "total_bytes" in locals() else 0},
    }


def verify_download(path: str, expected_sha256: str | None = None) -> dict[str, Any]:
    """Validate a downloaded file and optionally compare it against an expected hash."""
    file_path = Path(path)
    if not file_path.exists():
        return {"success": False, "error_code": "file_not_found", "error_message": f"No file exists at {path}."}

    actual_hash = _sha256_file(file_path)
    if expected_sha256 and actual_hash.lower() != expected_sha256.lower():
        return {
            "success": False,
            "error_code": "checksum_mismatch",
            "error_message": "Checksum mismatch detected.",
            "data": {"path": str(file_path), "sha256": actual_hash},
        }

    return {"success": True, "data": {"path": str(file_path), "sha256": actual_hash, "matches_expected": expected_sha256 is None or actual_hash.lower() == expected_sha256.lower()}}


def install_package(package_name: str, authorized: bool = False, source: str = "apt", version: str | None = None) -> dict[str, Any]:
    """Install a package via a supported manager only after explicit authorization."""
    if not authorized:
        return {
            "success": False,
            "error_code": "authorization_required",
            "error_message": "Explicit authorization is required before package installation.",
        }

    if not package_name or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", package_name):
        return {"success": False, "error_code": "invalid_package_name", "error_message": "The package name is invalid."}

    if source.lower() != "apt":
        return {"success": False, "error_code": "unsupported_source", "error_message": "The current implementation only supports apt-based installation."}

    apt_get = shutil.which("apt-get")
    if not apt_get:
        return {"success": False, "error_code": "package_manager_unavailable", "error_message": "The apt-get backend is not available."}

    operation_id = OperationTracker.create(package_name, source)
    OperationTracker.update(operation_id, "PREPARING")

    command = [apt_get, "install", "-y", "--no-install-recommends"]
    if version:
        command.append(f"{package_name}={version}")
    else:
        command.append(package_name)

    OperationTracker.update(operation_id, "INSTALLING")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    except subprocess.SubprocessError as exc:
        OperationTracker.update(operation_id, "FAILED", exit_code=1, error_classification="timeout_or_command_failure", diagnostic_evidence=[str(exc)])
        return {"success": False, "error_code": "install_failed", "error_message": str(exc), "operation_id": operation_id}

    OperationTracker.update(operation_id, "VERIFYING", exit_code=result.returncode)
    verification = verify_installation(package_name)
    if result.returncode != 0:
        OperationTracker.update(operation_id, "FAILED", exit_code=result.returncode, error_classification="install_failed", diagnostic_evidence=[result.stderr.strip() or result.stdout.strip()])
        return {
            "success": False,
            "error_code": "install_failed",
            "error_message": result.stderr.strip() or result.stdout.strip() or "Package installation failed.",
            "operation_id": operation_id,
            "verification": verification,
        }

    OperationTracker.update(operation_id, "COMPLETED", completion_status="completed", verification=verification)
    return {
        "success": True,
        "operation_id": operation_id,
        "status": "COMPLETED",
        "data": {"package": package_name, "source": source, "version": verification["data"].get("version") if verification.get("data") else None},
        "verification": verification,
    }


def verify_installation(package_name: str, expected_version: str | None = None, binary: str | None = None) -> dict[str, Any]:
    """Check whether a package is installed and whether a binary is available."""
    if not package_name or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", package_name):
        return {"success": False, "error_code": "invalid_package_name", "error_message": "The package name is invalid."}

    command = ["dpkg-query", "-W", "-f=${Status} ${Version}\n", package_name]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return {"success": False, "error_code": "package_manager_unavailable", "error_message": str(exc)}

    output = (result.stdout or "").strip()
    if result.returncode != 0 or "install ok installed" not in output:
        return {
            "success": False,
            "error_code": "package_not_installed",
            "error_message": result.stderr.strip() or f"Package '{package_name}' is not installed.",
            "data": {"installed": False, "version": None, "binary": shutil.which(binary) if binary else None},
        }

    version = output.split()[-1] if output.split() else None
    binary_path = shutil.which(binary) if binary else None
    if expected_version and version and version != expected_version:
        return {
            "success": False,
            "error_code": "version_mismatch",
            "error_message": f"Expected version {expected_version} but found {version}.",
            "data": {"installed": True, "version": version, "binary": binary_path},
        }

    return {
        "success": True,
        "data": {"installed": True, "version": version, "binary": binary_path},
    }
