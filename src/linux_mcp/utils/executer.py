import asyncio
import os
import re
import shutil
from typing import Any


SAFE_COMMANDS = {
    "cat",
    "date",
    "dpkg-query",
    "echo",
    "find",
    "grep",
    "head",
    "id",
    "ls",
    "pwd",
    "sed",
    "sha256sum",
    "stat",
    "tail",
    "true",
    "uname",
    "which",
    "apt-cache",
    "lsb_release",
}


class Executer:
    def __init__(self, command: list[str] | tuple[str, ...], timeout: int = 30, max_output_bytes: int = 200_000):
        self.command = list(command) if command is not None else []
        self.timeout = timeout
        self.max_output_bytes = max_output_bytes

    def _validate(self) -> tuple[str, list[str]]:
        if not self.command:
            raise ValueError("Command cannot be empty.")

        rejected_patterns = [";", "&&", "||", "|", "`", "$(", "\n", "\r"]
        for part in self.command:
            if any(pattern in str(part) for pattern in rejected_patterns):
                raise ValueError(f"Unsafe command fragment detected: {part!r}")

        executable = os.path.basename(str(self.command[0]))
        if executable not in SAFE_COMMANDS:
            raise PermissionError(f"Command '{executable}' is not in the allowlist.")

        resolved = shutil.which(executable)
        if not resolved:
            raise FileNotFoundError(f"Command '{executable}' was not found on PATH.")

        return resolved, self.command[1:]

    async def execute(self) -> dict[str, Any]:
        try:
            resolved, args = self._validate()
        except (ValueError, PermissionError, FileNotFoundError) as exc:
            return {
                "success": False,
                "error_code": "command_not_allowed" if isinstance(exc, PermissionError) else "invalid_command",
                "error_message": str(exc),
                "command": self.command,
                "stdout": "",
                "stderr": "",
                "returncode": None,
            }

        env = {"PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")}
        try:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    resolved,
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                ),
                timeout=self.timeout,
            )
            stdout_bytes, stderr_bytes = await process.communicate()
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error_code": "timeout",
                "error_message": f"Command timed out after {self.timeout} seconds.",
                "command": self.command,
                "stdout": "",
                "stderr": "",
                "returncode": None,
            }

        stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
        stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

        truncated = False
        if len(stdout.encode("utf-8")) > self.max_output_bytes:
            stdout = stdout[: self.max_output_bytes]
            truncated = True
        if len(stderr.encode("utf-8")) > self.max_output_bytes:
            stderr = stderr[: self.max_output_bytes]
            truncated = True

        return {
            "success": process.returncode == 0,
            "status": "completed" if process.returncode == 0 else "failed",
            "command": self.command,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": process.returncode,
            "truncated": truncated,
            "error_code": None if process.returncode == 0 else "command_failed",
            "error_message": None if process.returncode == 0 else (stderr or "Command returned a non-zero exit code."),
        }