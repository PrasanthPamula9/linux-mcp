from linux_mcp.utils.executer import Executer


async def execute_command(command: list[str], timeout: int = 30):
    """Execute a safe, allowlisted command and return structured output."""
    if command is None or not command:
        raise ValueError("Command list must not be empty.")
    return await Executer(command, timeout=timeout).execute()