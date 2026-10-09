from unittest.mock import patch

from linux_mcp.services.compatibility import (
    check_software_compatibility,
    get_software_details,
    search_software,
)


@patch("linux_mcp.services.compatibility.subprocess.run")
def test_search_software_returns_trusted_candidates(mock_run):
    mock_run.return_value = type(
        "Completed",
        (),
        {
            "stdout": "python3\npython3-pip\npython3-venv\n",
            "returncode": 0,
            "stderr": "",
        },
    )()

    result = search_software("python3", limit=2)

    assert result["success"] is True
    assert result["count"] == 2
    assert result["results"][0]["name"] == "python3"
    assert result["results"][0]["source"] == "apt"


@patch("linux_mcp.services.compatibility.subprocess.run")
def test_get_software_details_parses_package_metadata(mock_run):
    mock_run.return_value = type(
        "Completed",
        (),
        {
            "stdout": """
Package: python3
Version: 3.12.3-1ubuntu1
Architecture: amd64
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://www.python.org/
Description: Interactive high-level object-oriented language (default python3 version)
""",
            "returncode": 0,
            "stderr": "",
        },
    )()

    result = get_software_details("python3")

    assert result["success"] is True
    assert result["data"]["name"] == "python3"
    assert result["data"]["version"] == "3.12.3-1ubuntu1"
    assert result["data"]["architecture"] == "amd64"
    assert result["data"]["source"] == "apt"


def test_check_software_compatibility_flags_arch_mismatch():
    result = check_software_compatibility(
        "python3",
        system_info={"os": "Linux", "distribution": "ubuntu", "architecture": "x86_64"},
        package_details={"name": "python3", "architecture": "arm64", "source": "apt"},
    )

    assert result["status"] == "incompatible"
    assert result["missing_requirements"]
