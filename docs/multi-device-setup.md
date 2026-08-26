# AI OS Multi-Device Setup

AI OS is designed to run from any clone of `felipedr15/ai-skills-pack` without requiring the same Windows username or directory on every device.

## Clone

```powershell
git clone https://github.com/felipedr15/ai-skills-pack.git
cd ai-skills-pack
```

## Python Setup

Use Python 3.10 or newer.

```powershell
python --version
python scripts/ai-os.py doctor
```

AI OS currently uses the Python standard library for its core scripts. If a future workflow adds dependencies, install them from the repository's documented dependency file before running validation.

## Environment Setup

Most commands infer the repository root from the script location.

`AI_OS_HOME` is optional. Set it only when an external tool needs a stable pointer to the clone root:

```powershell
[Environment]::SetEnvironmentVariable("AI_OS_HOME", "C:\path\to\ai-skills-pack", "User")
```

Safe fallback behavior:

- If `AI_OS_HOME` points at a valid AI OS root, MCP uses it.
- If `AI_OS_HOME` is missing or invalid, MCP uses the repository root containing `scripts/mcp-server.py`.
- Do not commit `AI_OS_HOME`, usernames, credentials, or machine-specific local configuration.

## MCP Setup

Use the repository-specific MCP server script path in each MCP client:

```json
{
  "mcpServers": {
    "ai-os": {
      "command": "python",
      "args": ["<REPOSITORY_ROOT>/scripts/mcp-server.py"],
      "disabled": false
    }
  }
}
```

Replace `<REPOSITORY_ROOT>` with the clone path on that device. This path is local client configuration, not repository source.

Validate MCP:

```powershell
python scripts/ai-os.py mcp check
```

Start MCP manually for debugging:

```powershell
python scripts/ai-os.py mcp start
```

## VS Code Setup

Open the cloned repository folder in VS Code.

Recommended checks:

```powershell
python scripts/ai-os.py doctor
python scripts/ai-os.py status
python scripts/ai-os.py validate
```

For VS Code MCP clients, use the same MCP command shape shown above. Keep per-device MCP files local unless the client explicitly supports safe template variables.

## Validation

Run the standard local checks after cloning or moving the repository:

```powershell
python scripts/ai-os.py doctor
python scripts/ai-os.py status
python scripts/ai-os.py build --check
python scripts/ai-os.py validate
python scripts/ai-os.py mcp check
git diff --check
```

`doctor` focuses on local environment and configuration. `status` focuses on AI OS subsystem health and generated artifact freshness.

## Troubleshooting

- `python` not found: install Python 3.10+ or use the full Python executable path in MCP client configuration.
- MCP starts from the wrong clone: update the MCP `args` path or set `AI_OS_HOME` to the intended repository root.
- Generated files are stale: run `python scripts/ai-os.py build`, review the diff, then re-run validation.
- `status` says `NOT READY`: inspect the failed generated-file checks and run `python scripts/ai-os.py release-check`.
- Local config differs by device: create `config/ai-os.local.json` locally and do not commit it.
- Permission errors in tests: verify the temp directory is writable and retry outside restricted execution environments.
