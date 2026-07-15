# Generated Workflow Registry

> Generated from `knowledge/workflows/*.json`. This file is not a source of truth —
> edit the workflow JSON sources instead and regenerate.

Generated at: 2026-07-15T18:31:15Z
Generator: ai-os-orchestration
Total workflows: 8

## Workflows

### Bug Fix (`workflow:bug-fix`)

- Description: Diagnose and resolve a defect with a validated fix and optional lesson capture.
- Trigger intent: bug-fix
- Source: `knowledge/workflows/bug-fix.json`
- Approval gates: create-plan, implement, suggest-memory
- Validation gates: validate
- Steps:
  - `retrieve-context` — planner: search_knowledge
  - `create-plan` — planner: create_plan (requires approval)
  - `implement` — builder: modify_files (requires approval)
  - `validate` — qa: run_approved_validation
  - `suggest-memory` — documentation-writer: create_memory_suggestion (requires approval)

### Documentation Update (`workflow:documentation-update`)

- Description: Update existing documentation to correct or extend it, with review and validation.
- Trigger intent: documentation
- Source: `knowledge/workflows/documentation-update.json`
- Approval gates: create-plan, update-docs, suggest-memory
- Validation gates: validate
- Steps:
  - `retrieve-context` — planner: search_knowledge
  - `create-plan` — planner: create_plan (requires approval)
  - `update-docs` — documentation-writer: update_documentation (requires approval)
  - `review` — reviewer: review_diff
  - `validate` — qa: run_approved_validation
  - `suggest-memory` — documentation-writer: create_memory_suggestion (requires approval)

### Feature Development (`workflow:feature-development`)

- Description: Plan, design, implement, and validate a new feature end to end.
- Trigger intent: feature-development
- Source: `knowledge/workflows/feature-development.json`
- Approval gates: create-plan, design, implement, suggest-memory
- Validation gates: validate
- Steps:
  - `retrieve-context` — planner: search_knowledge
  - `create-plan` — planner: create_plan (requires approval)
  - `design` — architect: design_components (requires approval)
  - `implement` — builder: modify_files (requires approval)
  - `review` — reviewer: review_diff
  - `validate` — qa: run_approved_validation
  - `suggest-memory` — documentation-writer: create_memory_suggestion (requires approval)

### Incident Response (`workflow:incident-response`)

- Description: Triage and resolve an active incident or reported issue with a validated fix.
- Trigger intent: incident-response
- Source: `knowledge/workflows/incident-response.json`
- Approval gates: create-plan, implement, suggest-memory
- Validation gates: validate
- Steps:
  - `retrieve-context` — planner: search_knowledge
  - `assess` — security-reviewer: assess_security_risk
  - `create-plan` — planner: create_plan (requires approval)
  - `implement` — builder: modify_files (requires approval)
  - `validate` — qa: run_approved_validation
  - `suggest-memory` — documentation-writer: create_memory_suggestion (requires approval)

### Knowledge Maintenance (`workflow:knowledge-maintenance`)

- Description: Address a detected knowledge gap, stale document, or research question.
- Trigger intent: knowledge-maintenance
- Source: `knowledge/workflows/knowledge-maintenance.json`
- Approval gates: create-plan, update-docs, suggest-memory
- Validation gates: validate
- Steps:
  - `retrieve-context` — researcher: search_knowledge
  - `gather-evidence` — researcher: gather_evidence
  - `create-plan` — planner: create_plan (requires approval)
  - `update-docs` — documentation-writer: update_documentation (requires approval)
  - `validate` — qa: run_approved_validation
  - `suggest-memory` — documentation-writer: create_memory_suggestion (requires approval)

### Procedure Creation (`workflow:procedure-creation`)

- Description: Draft a new reusable procedure or runbook from research and existing conventions.
- Trigger intent: procedure-creation
- Source: `knowledge/workflows/procedure-creation.json`
- Approval gates: create-plan, draft-procedure, suggest-memory
- Validation gates: validate
- Steps:
  - `retrieve-context` — researcher: search_knowledge
  - `create-plan` — planner: create_plan (requires approval)
  - `draft-procedure` — documentation-writer: update_documentation (requires approval)
  - `review` — reviewer: review_diff
  - `validate` — qa: run_approved_validation
  - `suggest-memory` — documentation-writer: create_memory_suggestion (requires approval)

### Project Onboarding (`workflow:project-onboarding`)

- Description: Scaffold and document a new project within the AI OS knowledge structure.
- Trigger intent: project-planning
- Source: `knowledge/workflows/project-onboarding.json`
- Approval gates: create-plan, scaffold, document, coordinate
- Validation gates: validate
- Steps:
  - `retrieve-context` — planner: search_knowledge
  - `create-plan` — planner: create_plan (requires approval)
  - `scaffold` — builder: modify_files (requires approval)
  - `document` — documentation-writer: update_documentation (requires approval)
  - `validate` — qa: run_approved_validation
  - `coordinate` — project-manager: coordinate_approval_gates (requires approval)

### Release Preparation (`workflow:release-preparation`)

- Description: Prepare a release candidate for human review — never creates the release itself.
- Trigger intent: release
- Source: `knowledge/workflows/release-preparation.json`
- Approval gates: create-plan, deployment-guidance, coordinate
- Validation gates: validate
- Steps:
  - `retrieve-context` — planner: search_knowledge
  - `create-plan` — planner: create_plan (requires approval)
  - `security-review` — security-reviewer: assess_security_risk
  - `deployment-guidance` — deployment-manager: prepare_deployment_guidance (requires approval)
  - `validate` — qa: run_approved_validation
  - `coordinate` — project-manager: coordinate_approval_gates (requires approval)

