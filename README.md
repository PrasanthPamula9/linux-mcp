# Linux MCP

A production-oriented MCP (Model Context Protocol) tool layer for Linux system inspection, package discovery, software research, safe installation, verification, and troubleshooting.

This project is intentionally a server-side capability layer for external AI agents or clients. It does not implement a planning loop, agent runtime, or orchestration system. The server exposes reliable, typed tools that an external agent can call in a controlled and auditable way.

## Why this project exists

The repository is designed to demonstrate a clean MCP server architecture for real Linux operations:

- system and package-manager discovery
- repository-backed software lookup
- official-source research for software not found in configured repositories
- installation-method inspection and source validation
- secure Debian package validation and installation
- dependency, permission, and installation diagnostics
- structured remediation guidance
- allowlisted command execution with bounded output and safety checks

The design keeps business logic out of the MCP transport layer and separates:

- MCP tool contracts
- application services
- Linux-specific adapters
- security validation
- evidence-based diagnostics

## Architecture

The project uses a simple layered structure:

- `src/linux_mcp/server.py` — MCP entry point and tool registration
- `src/linux_mcp/services/` — business logic for system info, package discovery, compatibility, installation, diagnostics, and source validation
- `src/linux_mcp/controllers/` — thin controller adapters over the execution layer
- `src/linux_mcp/utils/executer.py` — safe allowlisted subprocess executor
- `tests/` — real behavioral tests for the tool layer

## Supported scope

The tool layer currently focuses on Debian/Ubuntu-style systems, especially Ubuntu and Linux Lite patterns. The implementation is structured so additional distributions can be supported later without changing the MCP contract.

## Current tool capabilities

The MCP server exposes tools for:

- system information
- package-manager detection
- package search in configured repositories
- software metadata lookup
- compatibility checks
- official-source research
- installation-method inspection
- source URL validation
- secure Debian package validation and installation
- installation verification
- dependency and permission checks
- installation failure diagnosis
- remediation planning
- allowlisted command execution

## Security model

This project intentionally enforces strict boundaries:

- only allowlisted commands are executed
- shell metacharacters and unsafe shell patterns are rejected
- network destinations are validated to block local/private metadata endpoints
- download URLs are restricted to approved schemes and public destinations
- file writes are bounded and destination paths are controlled
- installation requires explicit authorization for privileged operations
- diagnostic results are structured and redacted rather than exposing raw sensitive output

## Quick start

### Prerequisites

Install Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

### 1. Clone the repository

```bash
git clone https://github.com/PrasanthPamula9/linux-mcp.git
cd linux-mcp
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Run the MCP server

```bash
uv run python -m linux_mcp.server
```

If your MCP client launches the server as a subprocess, configure its command to run `uv` with arguments `run`, `python`, `-m`, and `linux_mcp.server`, using the cloned repository as the working directory.

## Example MCP tools

The server supports tools such as:

- `get_system_info`
- `get_package_manager`
- `search_package`
- `search_software`
- `check_software_compatibility`
- `research_official_sources`
- `inspect_installation_methods`
- `validate_source_url`
- `validate_deb_package`
- `install_deb`
- `verify_installation`
- `check_dependencies`
- `check_permissions`
- `diagnose_installation`
- `propose_remediation`
- `execute_command`

## Tool usage principles

The external agent is expected to:

1. detect OS and architecture
2. search configured package managers
3. choose a trusted path when available
4. research official sources when a package is not found in the repo
5. compare installation methods
6. request approval before sensitive operations
7. validate install results before treating them as successful

The MCP server is not responsible for autonomous decision-making. It exposes safe capabilities to a higher-level external client.

## Testing

The project includes a focused pytest suite covering:

- system detection
- package-manager behavior
- compatibility logic
- installation workflows
- diagnostic reports
- security constraints
- command execution safety

Run the test suite with:

```bash
uv run pytest -q
```

## Project status

This project is a tool layer intended for demonstration, engineering review, and practical Linux automation through MCP. It is not an agent, planner, or orchestration framework.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.



```bash
git remote set-url origin <your-github-repo-url>
git push -u origin main
```
