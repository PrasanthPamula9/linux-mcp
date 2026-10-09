from unittest.mock import patch

from linux_mcp.services.diagnostics import (
    check_dependencies,
    check_permissions,
    diagnose_application,
    diagnose_installation,
    get_operation_logs,
    propose_remediation,
)


@patch("linux_mcp.services.diagnostics.shutil.which")
def test_check_dependencies_reports_missing_binary(mock_which):
    mock_which.side_effect = lambda name: None if name == "python3" else "/usr/bin/apt-get"

    result = check_dependencies(["python3", "apt-get"])

    assert result["success"] is False
    assert result["missing"] == ["python3"]


@patch("linux_mcp.services.diagnostics.os.stat")
def test_check_permissions_reports_writable_root_files(mock_stat):
    mock_stat.return_value.st_mode = 0o100777
    mock_stat.return_value.st_uid = 0
    mock_stat.return_value.st_gid = 0

    result = check_permissions("/usr/bin/example")

    assert result["success"] is False
    assert result["issues"]


@patch("linux_mcp.services.diagnostics.subprocess.run")
def test_diagnose_installation_collects_apt_error(mock_run):
    mock_run.return_value = type(
        "Completed",
        (),
        {"returncode": 100, "stdout": "", "stderr": "E: Unable to locate package xppen\n"},
    )()

    result = diagnose_installation("xppen")

    assert result["success"] is False
    assert result["classification"] == "package_not_found"


@patch("linux_mcp.services.diagnostics.subprocess.run")
def test_diagnose_application_collects_runtime_failure(mock_run):
    mock_run.return_value = type(
        "Completed",
        (),
        {"returncode": 127, "stdout": "", "stderr": "bash: python3: command not found\n"},
    )()

    result = diagnose_application("python3")

    assert result["success"] is False
    assert result["classification"] == "missing_runtime_dependency"


@patch("linux_mcp.services.diagnostics.subprocess.run")
def test_get_operation_logs_returns_bounded_output(mock_run):
    mock_run.return_value = type(
        "Completed",
        (),
        {"returncode": 0, "stdout": "line1\nline2\nline3\n", "stderr": ""},
    )()

    result = get_operation_logs("apt-get install curl", max_lines=2)

    assert result["success"] is True
    assert len(result["data"]["lines"]) == 2


def test_propose_remediation_generates_structured_steps():
    result = propose_remediation(
        {
            "classification": "package_not_found",
            "evidence": [{"source": "apt-cache search", "message": "Package was not found in the configured repository."}],
        }
    )

    assert result["success"] is True
    assert result["actions"][0]["type"] == "check_repository"
