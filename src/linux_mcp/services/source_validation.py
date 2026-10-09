from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlparse

SUPPORTED_DISTRIBUTIONS = {"ubuntu", "debian", "linuxlite"}
SUPPORTED_ARCHITECTURES = {"amd64", "arm64", "armhf", "i386"}


def validate_source_url(url: str) -> dict[str, Any]:
    """Validate a source URL before it is used for vendor repository or installer research."""
    if not url or not url.strip():
        return {"success": False, "error_code": "invalid_url", "error_message": "A source URL is required."}

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        return {"success": False, "error_code": "invalid_url", "error_message": "Only http and https source URLs are allowed."}

    host = (parsed.hostname or "").lower()
    if not host:
        return {"success": False, "error_code": "invalid_url", "error_message": "The source URL must include a valid hostname."}

    blocked_hosts = {"localhost", "127.0.0.1", "::1", "metadata.google.internal", "169.254.169.254"}
    if host in blocked_hosts or host.endswith(".localhost") or host.endswith(".internal"):
        return {"success": False, "error_code": "blocked_destination", "error_message": "Refusing to use local or internal network addresses for software sources."}

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
        return {"success": False, "error_code": "blocked_destination", "error_message": "Refusing to use non-public network addresses for software sources."}

    return {"success": True, "scheme": scheme, "host": host, "url": url, "source_type": "repository"}


def check_distribution_compatibility(distribution: str, architecture: str) -> dict[str, Any]:
    """Check whether the distribution and architecture combination is supported for the current Ubuntu/Debian policy."""
    distro = (distribution or "").lower()
    arch = (architecture or "").lower()

    if distro not in SUPPORTED_DISTRIBUTIONS:
        return {
            "success": False,
            "status": "incompatible",
            "distribution": distro,
            "architecture": arch,
            "reason": "This implementation currently supports Ubuntu, Debian, and Linux Lite only.",
        }

    if arch not in SUPPORTED_ARCHITECTURES:
        return {
            "success": False,
            "status": "incompatible",
            "distribution": distro,
            "architecture": arch,
            "reason": f"Architecture '{arch}' is not in the supported Ubuntu/Debian set.",
        }

    return {"success": True, "status": "compatible", "distribution": distro, "architecture": arch, "reason": "Distribution and architecture are in the supported compatibility matrix."}


def plan_vendor_repository_install(
    url: str,
    distribution: str,
    architecture: str,
    signing_method: str = "gpg-keyring",
) -> dict[str, Any]:
    """Produce an explicit, approval-required plan for a vendor repository installation."""
    validation = validate_source_url(url)
    if not validation["success"]:
        return validation

    compatibility = check_distribution_compatibility(distribution, architecture)
    if not compatibility["success"]:
        return compatibility

    risk_level = "medium"
    if signing_method.lower() in {"apt-key", "gpg-keyserver", "curl | bash"}:
        risk_level = "high"

    return {
        "success": True,
        "approval_required": True,
        "risk_level": risk_level,
        "distribution": distribution,
        "architecture": architecture,
        "source": url,
        "signing_method": signing_method,
        "steps": [
            "Validate that the source URL is public and not private or local.",
            "Check the repository signing method and confirm the signing key is trusted and versioned.",
            "Create a precise apt source entry instead of modifying unrelated system files.",
            "Update apt metadata and verify the repo is reachable before installing packages.",
            "Perform a dry validation of the package metadata before installing anything.",
        ],
        "warnings": [
            "Vendor repositories change system package sources and should only be approved by a human operator.",
            "This plan intentionally avoids untrusted scripts and blanket permission changes.",
        ],
    }
