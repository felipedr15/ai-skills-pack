# AI OS Workflow

## Lifecycle
Request → planner skill selection → requirements → design → tasks → executor handoff → implementation → validation → diff review → human validation → commit → deployment.

## Gates
1. **Intake:** clarify scope, users, constraints, risks, and acceptance criteria.
2. **Requirements:** record testable functional and non-functional requirements.
3. **Design:** document components, data flow, interfaces, security, alternatives, and rollback.
4. **Tasks:** trace work items to requirements and assign validation.
5. **Approval:** a human approves scope and prepares `HANDOFF.md`.
6. **Execution:** the builder changes only allowed files and records evidence.
7. **Validation:** QA runs relevant automated and manual checks.
8. **Review:** reviewer evaluates the Git diff against approved sources.
9. **Human authority:** a person decides whether to commit and deploy.

Research may inform any pre-approval stage. Deployment requires a plan, explicit approval, smoke tests, monitoring, and rollback. AI OS documents this process; it does not automatically enforce every gate in every tool.

## Phase 1 Automation Workflow

1. Edit source files, including `SKILL.md` metadata when skills change.
2. Run `python scripts/generate-skill-registry.py` and `python scripts/index-repository.py` to refresh derived artifacts.
3. Run both commands with `--check` to verify deterministic freshness without writing.
4. Run `python scripts/validate-all.py` for the complete validation summary and unit tests.
5. Review the Git diff and obtain human approval before any commit.

For a new project, list starters with `python scripts/create-project.py --list-types`, then provide `--name`, `--type`, and `--destination`. Use `--force` only after reviewing an existing destination. Phase 2 remains proposed and is not yet implemented.
