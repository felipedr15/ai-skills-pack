# Security Policy

Never store passwords, API keys, access tokens, private certificates, connection strings, authentication cookies, MFA codes, employee or customer personal data, government-protected data, confidential screenshots, production exports, internal credentials, or private URLs here.

Use placeholders and least privilege. Minimize data, report suspected secrets, avoid copying sensitive data into logs or external research, review `.gitignore`, and never publish without approval. Rotate exposed credentials through the owning system; deleting a file is not sufficient. Dependency and platform controls require separate review. Report concerns privately to repository maintainers rather than opening a public issue with sensitive evidence.
