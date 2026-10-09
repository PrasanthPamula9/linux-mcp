import hashlib
from pathlib import Path
from unittest.mock import patch

from linux_mcp.services.installation import (
    download_software,
    install_package,
    validate_download_url,
    verify_download,
    verify_installation,
)


def test_validate_download_url_rejects_localhost():
    result = validate_download_url("http://127.0.0.1:8080/example.deb")

    assert result["success"] is False
    assert result["error_code"] == "blocked_destination"


def test_download_software_uses_expected_hash_and_size_limit(tmp_path):
    payload = b"deb-payload"
    destination = tmp_path / "demo.deb"
    expected_hash = hashlib.sha256(payload).hexdigest()

    class FakeResponse:
        def __init__(self, payload_bytes):
            self._payload = payload_bytes
            self.bytes_read = 0

        def read(self, size=-1):
            if size == -1:
                size = len(self._payload) - self.bytes_read
            chunk = self._payload[self.bytes_read : self.bytes_read + size]
            self.bytes_read += len(chunk)
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch("linux_mcp.services.installation.urllib.request.urlopen", return_value=FakeResponse(payload)):
        result = download_software(
            "https://example.com/demo.deb",
            destination=str(destination),
            expected_sha256=expected_hash,
            max_bytes=1024,
        )

    assert result["success"] is True
    assert destination.exists()
    assert result["data"]["sha256"] == expected_hash


def test_install_package_requires_explicit_authorization():
    result = install_package("curl", authorized=False)

    assert result["success"] is False
    assert result["error_code"] == "authorization_required"


@patch("linux_mcp.services.installation.subprocess.run")
def test_verify_installation_reads_installed_package(mock_run):
    mock_run.return_value = type(
        "Completed",
        (),
        {
            "returncode": 0,
            "stdout": "Package: curl\nStatus: install ok installed\nVersion: 8.5.0-2ubuntu1\n",
            "stderr": "",
        },
    )()

    result = verify_installation("curl")

    assert result["success"] is True
    assert result["data"]["installed"] is True
    assert result["data"]["version"] == "8.5.0-2ubuntu1"


@patch("linux_mcp.services.installation.hashlib.sha256")
def test_verify_download_rejects_mismatched_hash(mock_sha256, tmp_path):
    target = tmp_path / "demo.deb"
    target.write_bytes(b"real-bytes")
    mock_sha256.return_value.hexdigest.return_value = "abc123"

    result = verify_download(str(target), expected_sha256="def456")

    assert result["success"] is False
    assert result["error_code"] == "checksum_mismatch"
