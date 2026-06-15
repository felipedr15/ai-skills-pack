# Codex Tool Mapping

Skills may reference Claude Code tool names. When using Codex, map them like this:

| Skill references | Codex equivalent |
|---|---|
| `Task` tool | `spawn_agent` |
| Multiple `Task` calls | Multiple `spawn_agent` calls |
| Task returns result | `wait` |
| `TodoWrite` | `update_plan` |
| `Skill` tool | Skills load natively; follow the instructions |
| `Read`, `Write`, `Edit` | Use native file tools |
| `Bash` | Use native shell tools |

## Notes

If multi-agent support is unavailable, complete the workflow in the main session.

Use read-only git checks before branch or worktree operations.
