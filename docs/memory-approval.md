# Approvals and Memory Suggestions (Phase 8)

## Human Approval Requirement

Nothing in Phase 8 writes a source-of-truth document, modifies a file, or creates a permanent
memory without an explicit human approval. There is no configuration flag that enables
auto-approval — the code path does not exist.

## Approval Types

`plan`, `source-modification`, `permanent-memory`, `knowledge-document-update`,
`workflow-continuation`, `controlled-validation`, `session-completion`.

Approvals are created automatically at the point they become relevant (starting a session that
needs plan approval; completing a session that produced a memory suggestion) and stored in
`.ai-os/approvals/approvals.json` (local, git-ignored) with status `pending`. Only an explicit
command moves them forward:

```text
python scripts/ai-os.py approval list [--status pending]
python scripts/ai-os.py approval show <id>
python scripts/ai-os.py approval approve <id>
python scripts/ai-os.py approval reject <id> [--reason "..."]
```

Approval history is preserved — rejected and approved approvals remain visible via `approval
list`/`show`; nothing is deleted.

## Memory Suggestions

When `session complete <id>` finds at least one passed validation, it automatically:

1. Generates a memory suggestion (`.ai-os/memory-suggestions/<id>.json`) summarizing the problem,
   cause, resolution, validations passed, and a confidence score with explainable reasons.
2. Checks it against `generated/memory-index.json` for near-duplicates (token-overlap similarity)
   and records any matches.
3. Requests a `permanent-memory` approval targeting the suggestion.

```text
python scripts/ai-os.py memory-suggestions list [--status pending]
python scripts/ai-os.py memory-suggestions show <id>
python scripts/ai-os.py memory-suggestions approve <id>
python scripts/ai-os.py memory-suggestions reject <id> [--reason "..."]
python scripts/ai-os.py memory-suggestions export <id> [--output path.json]
```

`memory-suggestions approve` fails with a clear error unless a matching `permanent-memory`
approval has already been granted via `approval approve`. When it succeeds, it reuses
`scripts/memory-add.py`'s existing record-creation logic (front matter, registry update, secret
checks) — this is the only code path in Phase 8 that writes into `memory/`.

`export` writes the suggestion to a file so it can be reviewed or edited by hand before deciding.

## Security Notes

- Suggestion text (problem/cause/resolution/summary) is redacted for secret-like patterns and
  capped in length before it is ever written to disk.
- No full session transcript, chat history, or raw memory body is ever included in a suggestion.
- Rejected suggestions are retained (not deleted) for audit purposes.

[Back to AI OS](../README.md)
