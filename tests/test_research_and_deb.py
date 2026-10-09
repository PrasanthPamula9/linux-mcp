from unittest.mock import patch

from linux_mcp.services.deb_install import install_deb, validate_deb_package
from linux_mcp.services.research import inspect_installation_methods, research_official_sources


def test_research_official_sources_prefers_vendor_sites():
    html = """
    <html><body>
    <a href="https://www.mozilla.org/en-US/firefox/new/">Firefox official</a>
    <a href="https://example.com/firefox-download">Third party mirror</a>
    </body></html>
    """

    with patch("linux_mcp.services.research.urllib.request.urlopen", return_value=type("Resp", (), {"read": lambda self: html.encode(), "__enter__": lambda self: self, "__exit__": lambda self, *args: None})()):
        result = research_official_sources("firefox")

    assert result["success"] is True
    assert result["results"][0]["source_type"] == "official"
    assert "mozilla.org" in result["results"][0]["url"]


def test_inspect_installation_methods_reports_options():
    result = inspect_installation_methods(
        package_name="firefox",
        distribution="ubuntu",
        architecture="amd64",
        package_status={"status": "not_found"},
    )

    assert result["success"] is True
    assert any(method["method"] == "apt" for method in result["methods"])
    assert any(method["method"] == "deb" for method in result["methods"])


def test_validate_deb_package_rejects_architecture_mismatch():
    class FakeResult:
        stdout = "Package: firefox\nArchitecture: arm64\nDepends: libc6\n"
        returncode = 0
        stderr = ""

    with patch("linux_mcp.services.deb_install.subprocess.run", return_value=FakeResult()):
        result = validate_deb_package("/tmp/firefox.deb", host_architecture="amd64")

    assert result["success"] is False
    assert result["error_code"] == "architecture_mismatch"


def test_install_deb_requires_explicit_authorization():
    result = install_deb("/tmp/unknown.deb", authorized=False)

    assert result["success"] is False
    assert result["error_code"] == "authorization_required"
