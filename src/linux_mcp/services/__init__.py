"""Service layer for Linux MCP capabilities."""

from .compatibility import check_software_compatibility, get_software_details, search_software
from .deb_install import install_deb, validate_deb_package
from .diagnostics import (
    check_dependencies,
    check_permissions,
    diagnose_application,
    diagnose_installation,
    get_operation_logs,
    propose_remediation,
)
from .installation import (
    OperationTracker,
    download_software,
    install_package,
    validate_download_url,
    verify_download,
    verify_installation,
)
from .package_manager import get_package_manager, search_package
from .research import inspect_installation_methods, research_official_sources
from .source_validation import (
    check_distribution_compatibility,
    plan_vendor_repository_install,
    validate_source_url,
)
from .system import get_system_info

__all__ = [
    "get_system_info",
    "get_package_manager",
    "search_package",
    "search_software",
    "get_software_details",
    "check_software_compatibility",
    "validate_download_url",
    "download_software",
    "verify_download",
    "install_package",
    "verify_installation",
    "check_dependencies",
    "check_permissions",
    "diagnose_installation",
    "diagnose_application",
    "get_operation_logs",
    "propose_remediation",
    "research_official_sources",
    "inspect_installation_methods",
    "validate_deb_package",
    "install_deb",
    "validate_source_url",
    "check_distribution_compatibility",
    "plan_vendor_repository_install",
    "OperationTracker",
]
