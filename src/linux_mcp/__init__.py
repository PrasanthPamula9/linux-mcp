def main() -> None:
    """Run the Linux MCP server over the default transport."""
    from .server import mcp

    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)


__all__ = ["main"]
