# Gemini CLI Tool Mapping

Skills may reference Claude Code tool names. When using Gemini CLI, map them like this:

| Skill references | Gemini CLI equivalent |
|---|---|
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `replace` |
| `Bash` | `run_shell_command` |
| `Grep` | `grep_search` |
| `Glob` | `glob` |
| `TodoWrite` | `write_todos` |
| `Skill` | `activate_skill` |
| `WebSearch` | `google_web_search` |
| `WebFetch` | `web_fetch` |
| `Task` | No equivalent |

## Notes

Gemini CLI does not support subagents. Run those workflows in the main session.
