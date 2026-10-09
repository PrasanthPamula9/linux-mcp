from __future__ import annotations

import re
import urllib.request
from typing import Any
from urllib.parse import quote_plus


OFFICIAL_DOMAINS = {
    "mozilla.org",
    "canonical.com",
    "ubuntu.com",
    "github.com",
    "gitlab.com",
    "microsoft.com",
    "oracle.com",
    "apache.org",
    "python.org",
    "flathub.org",
    "snapcraft.io",
    "launchpad.net",
    "debian.org",
    "sourceforge.net",
}


def _classify_result(url: str, title: str, package_name: str) -> str:
    host = url.split("//", 1)[-1].split("/", 1)[0].lower()
    if any(host.endswith(domain) for domain in OFFICIAL_DOMAINS):
        return "official"
    if package_name.lower() in host.lower() or package_name.lower() in title.lower():
        return "official"
    return "third_party"


def research_official_sources(package_name: str, limit: int = 5) -> dict[str, Any]:
    """Search the web for likely official download or documentation pages for a package."""
    if not package_name or not package_name.strip():
        return {"success": False, "error_code": "invalid_package_name", "error_message": "Package name must not be empty.", "results": []}

    query = quote_plus(package_name)
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - network access can fail in CI
        return {
            "success": False,
            "error_code": "research_failed",
            "error_message": f"Unable to query public source metadata: {exc}",
            "results": [],
        }

    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for href in hrefs:
        if href.startswith("/"):
            continue
        if "duckduckgo.com" in href or "javascript:" in href.lower():
            continue
        if href.startswith("https://") or href.startswith("http://"):
            cleaned = href
            title = cleaned.split("//", 1)[-1].split("/", 1)[0]
            if cleaned in seen:
                continue
            seen.add(cleaned)
            result = {
                "title": title,
                "url": cleaned,
                "source_type": _classify_result(cleaned, title, package_name),
                "trusted": _classify_result(cleaned, title, package_name) == "official",
            }
            results.append(result)
        if len(results) >= limit:
            break

    if not results:
        return {
            "success": True,
            "query": package_name,
            "results": [],
            "message": "No public official-source candidates were found from the available research results.",
        }

    return {"success": True, "query": package_name, "results": results, "source": "web_search"}


def inspect_installation_methods(
    package_name: str,
    distribution: str,
    architecture: str,
    package_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect supported installation patterns and compare them to the host environment."""
    distro = (distribution or "").lower()
    arch = (architecture or "").lower()
    status = (package_status or {}).get("status", "unknown")

    methods: list[dict[str, Any]] = []
    apt_supported = distro in {"ubuntu", "debian", "linuxlite"}
    methods.append(
        {
            "method": "apt",
            "supported": apt_supported,
            "trust_level": "trusted",
            "requires_privilege": True,
            "notes": "Use the configured apt repository for distribution-managed installs when the package is available.",
            "status": status,
        }
    )
    methods.append(
        {
            "method": "deb",
            "supported": True,
            "trust_level": "moderate",
            "requires_privilege": True,
            "notes": "Download an official .deb package, validate metadata and architecture, then install through the system package manager.",
            "status": status,
        }
    )
    methods.append(
        {
            "method": "flatpak",
            "supported": True,
            "trust_level": "moderate",
            "requires_privilege": False,
            "notes": "Useful when the application is packaged as a sandboxed Flatpak and the runtime is already available.",
            "status": status,
        }
    )
    methods.append(
        {
            "method": "appimage",
            "supported": True,
            "trust_level": "low_to_moderate",
            "requires_privilege": False,
            "notes": "An AppImage can be convenient but requires manual verification and a trusted official source.",
            "status": status,
        }
    )

    if status == "not_found":
        methods[0]["notes"] = "The package is not available in the active configured repositories; continue with official-source research before choosing a vendor installer."

    return {
        "success": True,
        "package_name": package_name,
        "distribution": distro,
        "architecture": arch,
        "methods": methods,
        "preferred_method": "apt" if apt_supported else "deb",
    }
