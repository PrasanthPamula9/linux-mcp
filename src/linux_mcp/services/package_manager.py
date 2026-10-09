from __future__ import annotations

import shutil
import subprocess
from typing import Any


def get_package_manager() -> dict[str, Any]:
    """Identify supported package-manager backends and which are currently available."""
    known_backends = {
        "apt": "debian",
        "apt-get": "debian",
        "dpkg": "debian",
        "snap": "ubuntu",
        "dnf": "fedora",
        "yum": "rhel",
        "pacman": "arch",
        "zypper": "opensuse",
        "apk": "alpine",
    }

    supported: dict[str, bool] = {
        "debian": False,
        "ubuntu": False,
        "fedora": False,
        "rhel": False,
        "arch": False,
        "opensuse": False,
        "alpine": False,
        "apt": False,
        "apt-get": False,
        "dpkg": False,
        "snap": False,
        "dnf": False,
        "yum": False,
        "pacman": False,
        "zypper": False,
        "apk": False,
    }
    available: list[dict[str, str]] = []
    seen_names: set[str] = set()

    for name, family in known_backends.items():
        path = shutil.which(name)
        is_available = bool(path)
        supported[name] = is_available
        if is_available:
            supported[family] = True
            canonical_name = "apt" if name in {"apt", "apt-get"} else name
            if canonical_name not in seen_names:
                available.append({"name": canonical_name, "path": path})
                seen_names.add(canonical_name)

    supported["apt"] = bool(shutil.which("apt") or shutil.which("apt-get"))
    supported["debian"] = supported["debian"] or supported["apt"]

    if supported["apt"] and not any(item["name"] == "apt" for item in available):
        apt_path = shutil.which("apt") or shutil.which("apt-get")
        available.insert(0, {"name": "apt", "path": apt_path or ""})

    return {
        "supported": supported,
        "available": available,
    }


def search_package(query: str, limit: int = 10) -> dict[str, Any]:
    """Search apt repositories for a package using the configured package cache."""
    if not query or not query.strip():
        return {
            "success": False,
            "status": "invalid_query",
            "error_code": "invalid_package_name",
            "error_message": "Package query must not be empty.",
            "results": [],
        }

    if limit <= 0:
        return {
            "success": True,
            "status": "not_found",
            "query": query,
            "count": 0,
            "results": [],
            "source": "apt",
        }

    apt_cache = shutil.which("apt-cache")
    if not apt_cache:
        return {
            "success": False,
            "status": "unavailable",
            "error_code": "package_manager_unavailable",
            "error_message": "apt-cache is not available on this system.",
            "results": [],
        }

    try:
        result = subprocess.run(
            [apt_cache, "search", query],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return {
            "success": False,
            "status": "search_failed",
            "error_code": "package_search_failed",
            "error_message": "Unable to search for the requested package.",
            "results": [],
        }

    if result.returncode != 0:
        return {
            "success": False,
            "status": "search_failed",
            "error_code": "package_search_failed",
            "error_message": result.stderr.strip() or "Package search failed.",
            "results": [],
        }

    matches: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        if " - " in line:
            name, summary = line.split(" - ", 1)
        else:
            name, summary = line.strip(), ""
        cleaned_name = name.strip()
        if cleaned_name and cleaned_name not in {item["name"] for item in matches}:
            matches.append({"name": cleaned_name, "source": "apt", "summary": summary.strip()})
        if len(matches) >= limit:
            break

    if not matches:
        return {
            "success": True,
            "status": "not_found",
            "query": query,
            "count": 0,
            "results": [],
            "source": "apt",
            "message": "The package is not present in the configured package sources.",
        }

    return {
        "success": True,
        "status": "found",
        "query": query,
        "count": len(matches),
        "results": matches,
        "source": "apt",
    }
