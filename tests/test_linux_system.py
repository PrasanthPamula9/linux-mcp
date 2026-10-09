from unittest.mock import patch

from linux_mcp.services.system import get_system_info
from linux_mcp.services.package_manager import get_package_manager, search_package


@patch("linux_mcp.services.system.Path.read_text")
def test_get_system_info_reads_os_release(mock_read_text):
    mock_read_text.return_value = """
NAME="Ubuntu"
VERSION="24.04.1 LTS (Noble Numbat)"
ID=ubuntu
ID_LIKE=debian
VERSION_ID="24.04"
PRETTY_NAME="Ubuntu 24.04.1 LTS"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"

"""

    with patch("linux_mcp.services.system.platform.system", return_value="Linux"), patch(
        "linux_mcp.services.system.platform.machine", return_value="x86_64"
    ), patch("linux_mcp.services.system.platform.release", return_value="6.8.0-49-generic"):
        result = get_system_info()

    assert result["os"] == "Linux"
    assert result["distribution"] == "ubuntu"
    assert result["release"] == "24.04"
    assert result["architecture"] == "x86_64"
    assert result["kernel"] == "6.8.0-49-generic"


@patch("linux_mcp.services.package_manager.shutil.which")
def test_get_package_manager_reports_supported_backends(mock_which):
    def fake_which(name):
        return {"apt-get": "/usr/bin/apt-get", "dpkg": "/usr/bin/dpkg", "snap": "/usr/bin/snap"}.get(name)

    mock_which.side_effect = fake_which

    result = get_package_manager()

    assert result["supported"]["debian"] is True
    assert result["supported"]["apt"] is True
    assert result["supported"]["snap"] is True
    assert result["available"][0]["name"] == "apt"


@patch("linux_mcp.services.package_manager.subprocess.run")
def test_search_package_returns_matches(mock_run):
    mock_run.return_value = type(
        "Completed",
        (),
        {"stdout": "python3\npython3-venv\npython3-pip\n", "returncode": 0, "stderr": ""}
    )()

    result = search_package("python3", limit=2)

    assert result["success"] is True
    assert result["count"] == 2
    assert result["results"][0]["name"] == "python3"
    assert result["results"][0]["source"] == "apt"
