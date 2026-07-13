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
