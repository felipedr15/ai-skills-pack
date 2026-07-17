# Feature Specifications

This is the tool-neutral source of truth for project requirements, design, and implementation tasks. It is usable by Kiro, ChatGPT, Claude, Codex, Copilot, and human contributors alike — nothing here depends on any single tool's configuration or conventions.

Organize substantial features as:

```text
specs/[feature-name]/
├── requirements.md
├── design.md
└── tasks.md
```

Use lowercase hyphenated feature names, trace tasks to requirement IDs, record approval, and keep durable decisions in `decisions.md` when one is needed. Do not implement from unapproved substantial specifications: requirements, then design, then tasks, each reviewed before the next.

`.kiro/` is reserved for Kiro-specific configuration, workspace state, prompts, or temporary metadata — it does not hold canonical specification content. See [.kiro/specs/README.md](../.kiro/specs/README.md).

[Back to AI OS](../README.md)
