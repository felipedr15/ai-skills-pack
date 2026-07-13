---
id: review
name: Review Prompt
role: Reviewer
purpose: Compare the Git diff to requirements, design, tasks, and handoff; return APPROVED, APPROVED WITH CHANGES, or REJECTED with evidence.
requiredSkills: ["analytical", "testing"]
requiredInputs: [request, repository context]
expectedOutputs: [structured result, assumptions, risks, validation]
---

# Review Prompt

Compare the Git diff to requirements, design, tasks, and handoff; return APPROVED, APPROVED WITH CHANGES, or REJECTED with evidence.

Follow `AGENTS.md`, preserve scope, cite applicable requirement IDs, identify missing inputs, and prepare the next role's handoff.
