# Security Policy

Never store passwords, API keys, access tokens, private certificates, connection strings, authentication cookies, MFA codes, employee or customer personal data, government-protected data, confidential screenshots, production exports, internal credentials, or private URLs here.

Use placeholders and least privilege. Minimize data, report suspected secrets, avoid copying sensitive data into logs or external research, review `.gitignore`, and never publish without approval. Rotate exposed credentials through the owning system; deleting a file is not sufficient. Dependency and platform controls require separate review. Report concerns privately to repository maintainers rather than opening a public issue with sensitive evidence.

## Memory Engine Rules

AI OS memory is explicit repository content in `memory/`.

- Do not store secrets, access credentials, authentication cookies, private keys, MFA codes, personal records, confidential production exports, or regulated identifiers.
- Use placeholders for demonstrations.
- Run `python scripts/validate-memory-security.py` after memory changes.
- Treat `memory/registry.json` and source Markdown memory records as authoritative.
- Treat generated memory indexes as derived outputs only.

Memory security scanning is pattern-based and conservative. It may miss some risks or flag false positives, so human review remains required.

## Knowledge Graph Rules

Knowledge Graph generation must remain local and repository-based.

- Do not send repository data to external services.
- Do not include full record contents for memory files in graph nodes.
- Include concise metadata and relationships only.
- Exclude secret-like files and ignored directories from discovery.
- Treat generated graph files as derived outputs only.

## Continuous Learning and Orchestration Rules (Phase 8)

- No permanent memory is ever written without an explicit, human-granted `permanent-memory`
  approval. There is no configuration setting that enables auto-approval.
- No source file or knowledge document is modified automatically by any orchestration command.
- No Git operation, arbitrary shell execution, or network call originates from
  `scripts/orchestration/`.
- Session, approval, memory-suggestion, feedback, and audit data live only in the local,
  git-ignored `.ai-os/` directory — never in `generated/` (which stays deterministic and
  machine-independent) and never uploaded anywhere.
- Free-text fields (task descriptions, feedback comments, memory-suggestion summaries, audit
  event details) are redacted for secret-like patterns and length-capped before being written to
  disk, reusing the same `ai_os_service.permissions` redaction used elsewhere.
- No approval-mutating operation (approve/reject) is exposed through the MCP layer — approvals
  are CLI-only.
- The audit trail is hash-chained so tampering with `.ai-os/audit/` is detectable via
  `python scripts/ai-os.py audit validate`.

## Professional Context Rules (Phase 9)

Professional-context and expertise data is high-sensitivity personal data about the user, not
project knowledge, and is treated more conservatively than every other content type in this
repository.

- Never store raw resumes, raw performance evaluations, personal phone numbers, personal email
  addresses, home addresses, ZIP codes, employee IDs, credentials, asset/customer/employee
  records, internal IP addresses, or confidential/County-security-marked content anywhere under
  `profile/` or `knowledge/professional-context/`.
- `profile/` is reserved for canonical, explicitly-authored identity data; `memory/` validation
  actively rejects any record whose front matter carries the reserved profile-only keys `role`,
  `team`, or `reportingTo` — this boundary is enforced structurally, not by convention.
- Evidence pointers (`{type, ref}`) must be normalized identifiers, never free text, file paths,
  or contact information; validation rejects anything else.
- `overview.md` and every snapshot under `knowledge/professional-context/snapshots/` are passed
  through deterministic, regex-based sanitization before being written — this reduces risk but is
  not a substitute for human privacy review, exactly like the memory-security scan above.
- No profile is ever created, edited, or switched automatically. `profile switch` requires an
  explicitly approved `profile-switch` approval before any mutation; no CLI flag or invocation
  implies approval.
- Generic knowledge-graph and semantic-discovery traversal never expose role, team,
  responsibilities, or profile prose — only a profile's normalized id and active status are
  visible outside the approval-gated CLI and the summary-only MCP tools.
- No network calls, no telemetry, no arbitrary shell execution, and no automatic promotion into
  permanent memory originates from any Phase 9 code path.
