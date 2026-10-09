from __future__ import annotations

import shutil
import subprocess
from typing import Any

from linux_mcp.services.package_manager import get_package_manager
from linux_mcp.services.system import get_system_info


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


def _parse_metadata(raw: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            metadata[current_key] = value.strip()
        elif current_key and line.startswith(" "):
            metadata[current_key] = f"{metadata.get(current_key, '')} {line.strip()}".strip()
    return metadata


def search_software(query: str, limit: int = 10) -> dict[str, Any]:
    """Search the configured distribution repositories for a candidate package."""
    if not query or not query.strip():
        return {"success": False, "error_code": "invalid_query", "error_message": "Package query must not be empty.", "results": []}

    apt_cache = shutil.which("apt-cache")
    if not apt_cache:
        return {"success": False, "error_code": "package_manager_unavailable", "error_message": "apt-cache is not available on this system.", "results": []}

    try:
        result = subprocess.run([apt_cache, "search", query], capture_output=True, text=True, timeout=10, check=False)
    except (FileNotFoundError, subprocess.SubprocessError):
        return {"success": False, "error_code": "search_failed", "error_message": "Unable to search software repositories.", "results": []}

    if result.returncode != 0:
        return {"success": False, "error_code": "search_failed", "error_message": result.stderr.strip() or "Search failed.", "results": []}

    matches: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        if " - " in line:
            name, summary = line.split(" - ", 1)
        else:
            name, summary = line.strip(), ""
        package_name = name.strip()
        if not package_name or package_name in seen:
            continue
        matches.append({"name": package_name, "summary": summary.strip(), "source": "apt", "trusted_source": "distribution repository"})
        seen.add(package_name)
        if len(matches) >= limit:
            break

    return {"success": True, "query": query, "count": len(matches), "results": matches, "source": "apt", "trusted_source": "distribution repository"}


def get_software_details(package_name: str) -> dict[str, Any]:
    """Return package metadata from trusted distribution metadata when available."""
    if not package_name or not package_name.strip():
        return {"success": False, "error_code": "invalid_package_name", "error_message": "Package name must not be empty.", "data": None}

    apt_cache = shutil.which("apt-cache")
    if not apt_cache:
        return {"success": False, "error_code": "package_manager_unavailable", "error_message": "apt-cache is not available on this system.", "data": None}

    try:
        result = subprocess.run([apt_cache, "show", package_name], capture_output=True, text=True, timeout=10, check=False)
    except (FileNotFoundError, subprocess.SubprocessError):
        return {"success": False, "error_code": "metadata_lookup_failed", "error_message": "Unable to read package metadata.", "data": None}

    if result.returncode != 0:
        return {"success": False, "error_code": "package_not_found", "error_message": result.stderr.strip() or f"Package '{package_name}' was not found.", "data": None}

    metadata = _parse_metadata(result.stdout)
    data = {
        "name": metadata.get("Package", package_name),
        "version": metadata.get("Version", ""),
        "architecture": metadata.get("Architecture", ""),
        "source": "apt",
        "trusted_source": "distribution repository",
        "maintainer": metadata.get("Maintainer", ""),
        "homepage": metadata.get("Homepage", ""),
        "description": metadata.get("Description", ""),
        "section": metadata.get("Section", ""),
    }

    return {"success": True, "data": data, "evidence": [{"type": "package_metadata", "source": "apt"}]}


def check_software_compatibility(package_name: str, system_info: dict[str, Any] | None = None, package_details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assess whether the package metadata matches the host and whether the package is likely installable."""
    local_system = system_info or get_system_info()
    if package_details is None:
        package_lookup = get_software_details(package_name)
        if not package_lookup["success"]:
            return {
                "status": "unknown",
                "success": False,
                "package_name": package_name,
                "evidence": package_lookup.get("evidence", []),
                "warnings": [package_lookup.get("error_message", "Package metadata is unavailable.")],
                "missing_requirements": ["package_metadata"],
                "limitations": ["This check cannot prove runtime compatibility without package metadata."],
            }
        package_details = package_lookup["data"]

    package_arch = _normalize_arch(package_details.get("architecture"))
    host_arch = _normalize_arch(local_system.get("architecture"))
    distribution = (local_system.get("distribution") or "").lower()
    status = "compatible"
    missing_requirements: list[str] = []
    warnings: list[str] = []
    evidence: list[dict[str, Any]] = [
        {"type": "system", "distribution": distribution, "architecture": host_arch},
        {"type": "package", "name": package_details.get("name"), "architecture": package_arch, "source": package_details.get("source")},
    ]

    if package_arch and host_arch and package_arch not in {"", "all", "any"} and package_arch != host_arch:
        status = "incompatible"
        missing_requirements.append(f"Architecture mismatch: package requires {package_arch}, host is {host_arch}.")
        warnings.append("Package metadata does not match the host architecture.")

    if distribution not in {"ubuntu", "debian"}:
        status = "conditional" if status == "compatible" else status
        warnings.append(f"Distribution '{distribution}' is not explicitly covered by the Ubuntu/Debian compatibility policy.")

    package_manager = get_package_manager()
    if not package_manager["supported"].get("apt"):
        status = "conditional" if status == "compatible" else status
        warnings.append("APT package-manager backend is not available; the package may still be valid but not installable through the default path.")

    if status == "compatible":
        warnings.append("This compatibility result confirms package metadata is consistent with the host; it does not guarantee runtime compatibility.")

    return {
        "status": status,
        "success": status != "incompatible",
        "package_name": package_name,
        "system": local_system,
        "package_details": package_details,
        "missing_requirements": missing_requirements,
        "warnings": warnings,
        "evidence": evidence,
        "limitations": ["Package metadata compatibility is not the same as runtime validation.", "This tool does not execute the package or verify that all downstream runtime dependencies are satisfied."],
    }
