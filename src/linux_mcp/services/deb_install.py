from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from typing import Any


def _normalize_arch(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    aliases = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armhf",
        "armhf": "armhf",
        "i386": "i386",
        "i686": "i386",
    }
    return aliases.get(normalized, normalized)


def validate_deb_package(path: str, host_architecture: str | None = None) -> dict[str, Any]:
    """Validate a local DEB package's metadata and architecture before installation."""
    if not path or not path.strip():
        return {"success": False, "error_code": "invalid_path", "error_message": "A .deb file path is required."}

    if not path.lower().endswith(".deb"):
        return {"success": False, "error_code": "invalid_file_type", "error_message": "Only .deb packages are supported."}

    host_arch = _normalize_arch(host_architecture or platform.machine())
    try:
        result = subprocess.run(
            ["dpkg-deb", "-f", path, "Package", "Architecture", "Depends"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return {"success": False, "error_code": "package_metadata_unavailable", "error_message": str(exc)}

    stdout = result.stdout.strip()
    if result.returncode != 0 or not stdout:
        return {"success": False, "error_code": "invalid_deb_metadata", "error_message": result.stderr.strip() or "The package metadata could not be read."}

    metadata: dict[str, str] = {}
    for line in stdout.splitlines():
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    package_name = metadata.get("Package", os.path.basename(path))
    package_arch = _normalize_arch(metadata.get("Architecture"))
    depends = [item.strip() for item in metadata.get("Depends", "").split(",") if item.strip()]

    if package_arch and package_arch != "all" and host_arch and package_arch != host_arch:
        return {
            "success": False,
            "error_code": "architecture_mismatch",
            "error_message": f"Package architecture {package_arch} does not match host architecture {host_arch}.",
            "data": {"package": package_name, "architecture": package_arch, "host_architecture": host_arch, "depends": depends},
        }

    return {
        "success": True,
        "data": {"package": package_name, "architecture": package_arch, "host_architecture": host_arch, "depends": depends},
    }


def install_deb(path: str, authorized: bool = False, host_architecture: str | None = None, package_name: str | None = None) -> dict[str, Any]:
    """Install a local DEB package only after explicit authorization and metadata validation."""
    if not authorized:
        return {"success": False, "error_code": "authorization_required", "error_message": "Explicit authorization is required before installing a .deb package."}

    if not path or not path.strip():
        return {"success": False, "error_code": "invalid_path", "error_message": "A .deb file path is required."}

    apt_get = shutil.which("apt-get")
    if not apt_get:
        return {"success": False, "error_code": "package_manager_unavailable", "error_message": "The apt-get backend is not available."}

    validation = validate_deb_package(path, host_architecture=host_architecture)
    if not validation["success"]:
        return validation

    package = package_name or validation["data"].get("package")
    install_cmd = [apt_get, "install", "-y", "--no-install-recommends", path]
    try:
        result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=600, check=False)
    except subprocess.SubprocessError as exc:
        return {"success": False, "error_code": "install_failed", "error_message": str(exc), "package": package}

    if result.returncode != 0:
        return {
            "success": False,
            "error_code": "install_failed",
            "error_message": result.stderr.strip() or result.stdout.strip() or "DEB installation failed.",
            "package": package,
            "data": {"returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()},
        }

    return {
        "success": True,
        "package": package,
        "data": {"returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()},
    }
