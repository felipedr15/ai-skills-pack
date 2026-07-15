# Generated Agent Registry

> Generated from `agents/*.md` and `agents.json`. This file is not a source of truth —
> edit the agent markdown docs instead and regenerate.

Generated at: 2026-07-15T18:31:15Z
Generator: ai-os-orchestration
Total agents: 10

## Agents by Role

- architecture: 1
- building: 1
- documentation: 1
- planning: 1
- project-management: 1
- quality-assurance: 1
- release: 1
- research: 1
- review: 1
- security: 1

## Agents

### Architect (`agent:architect`)

- Role: architecture
- Description: Design components, interfaces, risks, and alternatives.
- Source: `agents/architect.md`
- Required skills: analytical, problem-solving
- Allowed actions: design_components, create_plan
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Builder (`agent:builder`)

- Role: building
- Description: Implement only approved scope and record evidence.
- Source: `agents/builder.md`
- Required skills: creator, testing
- Allowed actions: modify_files
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Deployment Manager (`agent:deployment-manager`)

- Role: release
- Description: Prepare approved deployment and rollback guidance.
- Source: `agents/deployment-manager.md`
- Required skills: vercel-agent, testing
- Allowed actions: prepare_deployment_guidance
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Documentation Writer (`agent:documentation-writer`)

- Role: documentation
- Description: Create clear, accurate, audience-focused documentation.
- Source: `agents/documentation-writer.md`
- Required skills: writing, clear-concise-writing
- Allowed actions: create_memory_suggestion, update_documentation
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Planner (`agent:planner`)

- Role: planning
- Description: Turn requests into approved, traceable scope.
- Source: `agents/planner.md`
- Required skills: problem-solving, analytical
- Allowed actions: search_knowledge, create_plan, classify_task
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Project Manager (`agent:project-manager`)

- Role: project-management
- Description: Coordinate gates, status, ownership, and human decisions.
- Source: `agents/project-manager.md`
- Required skills: writing, problem-solving
- Allowed actions: coordinate_approval_gates
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### QA (`agent:qa`)

- Role: quality-assurance
- Description: Plan and perform traceable validation.
- Source: `agents/qa.md`
- Required skills: testing, problem-solving
- Allowed actions: run_approved_validation
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Researcher (`agent:researcher`)

- Role: research
- Description: Gather and distinguish evidence, inference, and limitations.
- Source: `agents/researcher.md`
- Required skills: browser, analytical
- Allowed actions: search_knowledge, gather_evidence
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Reviewer (`agent:reviewer`)

- Role: review
- Description: Evaluate the Git diff against approved artifacts.
- Source: `agents/reviewer.md`
- Required skills: analytical, testing
- Allowed actions: review_diff
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

### Security Reviewer (`agent:security-reviewer`)

- Role: security
- Description: Assess data, access, dependency, and deployment risks.
- Source: `agents/security-reviewer.md`
- Required skills: analytical, problem-solving
- Allowed actions: assess_security_risk
- Forbidden actions: git_commit, git_push, git_merge, git_tag, arbitrary_shell_execution, secret_access, network_access, automatic_approval

