# Workflow Examples

Each example follows request → scope → approved artifacts → execution (when authorized) → validation → review → human decision.

## Writing workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Research workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Troubleshooting workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Application-building workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Power Apps workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Power Automate workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Web-app and v0 workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Vercel deployment workflow
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Planner-to-builder handoff
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Builder-to-reviewer report
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## QA report
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Security review
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Human approval
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.
## Commit-readiness checklist
Define inputs and owner; select skills; document requirements/design/tasks as proportional; perform authorized work; record evidence, risks, and next handoff.

## Memory add workflow
Define memory type and scope, write safe source Markdown content, run `python scripts/memory-add.py`, verify `memory/registry.json`, run memory index and security validation, then review diff.

## Memory search workflow
Use `python scripts/memory-search.py` with phrase and filters, confirm source record relevance, and avoid treating generated indexes as source of truth.

## Memory archive workflow
Archive by ID using `python scripts/memory-archive.py`, verify source file moved under `memory/archive/`, and confirm record status updates to `archived`.

## Memory promotion workflow
Promote using `python scripts/memory-promote.py` with explicit reason, preserve traceability via related IDs, and mark superseded records appropriately.

## Memory validation workflow
Run:

```text
python scripts/generate-memory-index.py --check
python scripts/validate-memory-security.py
python scripts/validate-all.py
```

[Back to references](README.md)
