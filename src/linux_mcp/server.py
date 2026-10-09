from mcp.server import MCPServer

from linux_mcp.controllers import Command_executor_ctrl
from linux_mcp.services.compatibility import (
    check_software_compatibility,
    get_software_details,
    search_software,
)
from linux_mcp.services.deb_install import install_deb, validate_deb_package
from linux_mcp.services.diagnostics import (
    check_dependencies,
    check_permissions,
    diagnose_application,
    diagnose_installation,
    get_operation_logs,
    propose_remediation,
)
from linux_mcp.services.installation import (
    download_software,
    install_package,
    validate_download_url,
    verify_download,
    verify_installation,
)
from linux_mcp.services.package_manager import get_package_manager, search_package
from linux_mcp.services.research import inspect_installation_methods, research_official_sources
from linux_mcp.services.source_validation import (
    check_distribution_compatibility,
    plan_vendor_repository_install,
    validate_source_url,
)
from linux_mcp.services.system import get_system_info

mcp = MCPServer("linux-mcp", title="Linux MCP", description="Linux system inspection and package-manager capability layer")


@mcp.tool(name="get_system_info")
def get_system_info_tool() -> dict:
    """Return basic OS, distribution, and hardware metadata for the host."""
    return get_system_info()


@mcp.tool(name="get_package_manager")
def get_package_manager_tool() -> dict:
    """Return supported package-manager backends and what is available on this system."""
    return get_package_manager()


@mcp.tool(name="search_package")
def search_package_tool(package: str, limit: int = 10) -> dict:
    """Search configured package repositories for a package candidate."""
    return search_package(package, limit=limit)


@mcp.tool(name="search_software")
def search_software_tool(package: str, limit: int = 10) -> dict:
    """Search trusted distribution repositories for a software candidate."""
    return search_software(package, limit=limit)


@mcp.tool(name="get_software_details")
def get_software_details_tool(package: str) -> dict:
    """Return verified package metadata from the configured system package sources."""
    return get_software_details(package)


@mcp.tool(name="check_software_compatibility")
def check_software_compatibility_tool(package: str) -> dict:
    """Assess package metadata compatibility against the local host and Debian/Ubuntu policy."""
    return check_software_compatibility(package)


@mcp.tool(name="download_software")
def download_software_tool(url: str, destination: str | None = None, expected_sha256: str | None = None) -> dict:
    """Download a file from an approved remote destination and optionally validate a hash."""
    return download_software(url=url, destination=destination, expected_sha256=expected_sha256)


@mcp.tool(name="verify_download")
def verify_download_tool(path: str, expected_sha256: str | None = None) -> dict:
    """Verify the checksum of a downloaded file using explicit expected values when available."""
    return verify_download(path=path, expected_sha256=expected_sha256)


@mcp.tool(name="install_package")
def install_package_tool(package: str, authorized: bool = False, source: str = "apt") -> dict:
    """Install a package through the supported apt backend only after explicit authorization."""
    return install_package(package_name=package, authorized=authorized, source=source)


@mcp.tool(name="verify_installation")
def verify_installation_tool(package: str, binary: str | None = None) -> dict:
    """Verify a package installation and the presence of its binary."""
    return verify_installation(package_name=package, binary=binary)


@mcp.tool(name="validate_download_url")
def validate_download_url_tool(url: str) -> dict:
    """Validate download destinations before they are fetched."""
    return validate_download_url(url)


@mcp.tool(name="check_dependencies")
def check_dependencies_tool(requirements: list[str]) -> dict:
    """Check whether required executables or libraries are present."""
    return check_dependencies(requirements)


@mcp.tool(name="check_permissions")
def check_permissions_tool(path: str) -> dict:
    """Inspect path permissions and ownership for the target installation or launch path."""
    return check_permissions(path)


@mcp.tool(name="diagnose_installation")
def diagnose_installation_tool(package: str) -> dict:
    """Collect evidence and classify the likely cause of a failed installation."""
    return diagnose_installation(package)


@mcp.tool(name="diagnose_application")
def diagnose_application_tool(command: str) -> dict:
    """Collect evidence when a command or application fails to start."""
    return diagnose_application(command)


@mcp.tool(name="get_operation_logs")
def get_operation_logs_tool(command: str, max_lines: int = 20) -> dict:
    """Return a bounded set of relevant log lines using a strict line cap."""
    return get_operation_logs(command, max_lines=max_lines)


@mcp.tool(name="propose_remediation")
def propose_remediation_tool(diagnostic: dict) -> dict:
    """Produce a structured remediation proposal from diagnostic evidence."""
    return propose_remediation(diagnostic)


@mcp.tool(name="research_official_sources")
def research_official_sources_tool(package: str, limit: int = 5) -> dict:
    """Search the web for likely official vendor sources and installation information."""
    return research_official_sources(package, limit=limit)


@mcp.tool(name="inspect_installation_methods")
def inspect_installation_methods_tool(package: str, distribution: str, architecture: str, package_status: dict | None = None) -> dict:
    """Compare candidate installation strategies for a software package."""
    return inspect_installation_methods(package, distribution, architecture, package_status)


@mcp.tool(name="validate_deb_package")
def validate_deb_package_tool(path: str, host_architecture: str | None = None) -> dict:
    """Validate a local .deb package's metadata and architecture before installation."""
    return validate_deb_package(path, host_architecture=host_architecture)


@mcp.tool(name="install_deb")
def install_deb_tool(path: str, authorized: bool = False, host_architecture: str | None = None, package_name: str | None = None) -> dict:
    """Install a validated local .deb package with explicit authorization."""
    return install_deb(path, authorized=authorized, host_architecture=host_architecture, package_name=package_name)


@mcp.tool(name="validate_source_url")
def validate_source_url_tool(url: str) -> dict:
    """Validate a vendor or installer source URL before use."""
    return validate_source_url(url)


@mcp.tool(name="check_distribution_compatibility")
def check_distribution_compatibility_tool(distribution: str, architecture: str) -> dict:
    """Check whether the target distribution and architecture are supported for the current installation policy."""
    return check_distribution_compatibility(distribution, architecture)


@mcp.tool(name="plan_vendor_repository_install")
def plan_vendor_repository_install_tool(url: str, distribution: str, architecture: str, signing_method: str = "gpg-keyring") -> dict:
    """Plan an approval-required vendor repository installation with explicit risk and validation steps."""
    return plan_vendor_repository_install(url=url, distribution=distribution, architecture=architecture, signing_method=signing_method)


@mcp.tool(name="execute_command")
async def execute_command_tool(command: list[str], timeout: int = 30) -> dict:
    """Execute a safe, allowlisted command and return bounded output."""
    return await Command_executor_ctrl.execute_command(command, timeout=timeout)


# @mcp.tool()
# def add(a: int, b: int) -> int:
#     """Add two numbers."""
#     return a + b


@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


@mcp.resource("system://{info}")
async def system_info(info: str) -> str:
    """Return a system resource placeholder."""
    return f"System information: {info}"


@mcp.prompt()
async def summarize(text: str) -> str:
    """Summarize a piece of text in one sentence."""
    return f"Summarize the following text in one sentence:\n\n{text}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
