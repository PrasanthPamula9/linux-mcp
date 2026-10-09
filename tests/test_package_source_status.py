from linux_mcp.services.package_manager import search_package


def test_search_package_reports_explicit_not_found_status():
    # This uses the actual system package metadata, so it is intentionally a live check.
    result = search_package("nonexistent-package-xyz-12345", limit=5)

    assert result["success"] is True
    assert result["status"] == "not_found"
    assert result["source"] == "apt"
