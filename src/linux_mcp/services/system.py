from __future__ import annotations

import platform
from pathlib import Path


def _read_os_release() -> dict[str, str]:
    """Read /etc/os-release without crashing when the file is missing."""
    data: dict[str, str] = {}
    os_release_path = Path("/etc/os-release")
    if not os_release_path.exists():
        return data

    try:
        content = os_release_path.read_text(encoding="utf-8")
    except OSError:
        return data

    for raw_line in content.splitlines():
        if not raw_line or raw_line.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        data[key.strip()] = value.strip().strip('"')

    return data


def get_system_info() -> dict[str, str]:
    """Return a lightweight, non-sensitive summary of the host OS and hardware."""
    os_release = _read_os_release()

    return {
        "os": platform.system() or "unknown",
        "distribution": os_release.get("ID", "unknown"),
        "release": os_release.get("VERSION_ID", os_release.get("VERSION", "unknown")),
        "architecture": platform.machine() or "unknown",
        "kernel": platform.release() or "unknown",
        "pretty_name": os_release.get("PRETTY_NAME", os_release.get("NAME", "unknown")),
        "id_like": os_release.get("ID_LIKE", ""),
    }
