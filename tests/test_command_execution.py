import asyncio

from linux_mcp.controllers import Command_executor_ctrl
from linux_mcp.utils.executer import Executer


def test_allowed_command_executes_successfully():
    result = asyncio.run(Executer(["echo", "hello from mcp"]).execute())

    assert result["success"] is True
    assert "hello from mcp" in result["stdout"]


def test_disallowed_command_is_rejected():
    result = asyncio.run(Executer(["bash", "-c", "echo bad"]).execute())

    assert result["success"] is False
    assert result["error_code"] == "command_not_allowed"


def test_controller_wrapper_calls_executor():
    result = asyncio.run(Command_executor_ctrl.execute_command(["echo", "controller-check"]))

    assert result["success"] is True
    assert "controller-check" in result["stdout"]
