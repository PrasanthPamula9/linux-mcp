from linux_mcp.services.source_validation import (
    check_distribution_compatibility,
    plan_vendor_repository_install,
    validate_source_url,
)


def test_validate_source_url_rejects_private_hosts():
    result = validate_source_url("http://127.0.0.1/repo.list")

    assert result["success"] is False
    assert result["error_code"] == "blocked_destination"


def test_validate_source_url_accepts_public_https_host():
    result = validate_source_url("https://packages.mozilla.org/repo")

    assert result["success"] is True
    assert result["host"] == "packages.mozilla.org"


def test_check_distribution_compatibility_rejects_unsupported_combo():
    result = check_distribution_compatibility("ubuntu", "riscv64")

    assert result["success"] is False
    assert result["status"] == "incompatible"


def test_plan_vendor_repository_install_requires_approval():
    result = plan_vendor_repository_install(
        url="https://packages.example.com/ubuntu",
        distribution="ubuntu",
        architecture="amd64",
        signing_method="gpg-keyserver",
    )

    assert result["success"] is True
    assert result["approval_required"] is True
    assert result["risk_level"] in {"medium", "high"}
