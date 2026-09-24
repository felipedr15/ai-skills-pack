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

For a new project, list starters with `python scripts/create-project.py --list-types`, then provide `--name`, `--type`, and `--destination`. Use `--force` only after reviewing an existing destination.

## Phase 2 Memory Workflow (Implemented)

1. Create memory records with `python scripts/memory-add.py` using explicit metadata and safe content.
2. Keep authoritative data in source Markdown files and `memory/registry.json`.
3. List and search memory using `python scripts/memory-list.py` and `python scripts/memory-search.py`.
4. Promote temporary or proposed records with `python scripts/memory-promote.py`.
5. Archive inactive records with `python scripts/memory-archive.py` while preserving IDs.
6. Regenerate derived memory indexes with `python scripts/generate-memory-index.py`.
7. Run validation and security checks:

```text
python scripts/generate-memory-index.py --check
python scripts/validate-memory-security.py
python scripts/validate-all.py
```

## Phase 3 Knowledge Graph Workflow (Implemented)

1. Build graph artifacts from repository source files with `python scripts/generate-knowledge-graph.py`.
2. Validate graph schema, references, and path safety with `python scripts/validate-knowledge-graph.py`.
3. Check generated graph freshness without writing via `python scripts/generate-knowledge-graph.py --check`.
4. Run unified validation to confirm no regressions in prior phases.

## Phase 4 Semantic Discovery Workflow (Implemented)

1. Build discovery index from knowledge graph and source files with `python scripts/discovery-build.py`.
2. Validate discovery index structure with `python scripts/discovery-validate.py`.
3. Check generated discovery index freshness without writing via `python scripts/discovery-check.py`.
4. Query the repository using the discovery CLI:

```text
python scripts/discover.py search "knowledge graph"
python scripts/discover.py search validation --type skill
python scripts/discover.py related <node-id>
python scripts/discover.py traverse <node-id> --depth 2
python scripts/discover.py path <source-id> <target-id>
python scripts/discover.py explain <node-id> "query"
python scripts/discover.py stats
```

5. Run unified validation to confirm no regressions across all phases.

## Phase 5 Interactive Dashboard Workflow (Implemented)

1. Build dashboard artifacts with `python scripts/dashboard-build.py`.
2. Validate dashboard structure with `python scripts/dashboard-validate.py`.
3. Check dashboard freshness without writing via `python scripts/dashboard-check.py`.
4. Start the local dashboard server:

```text
python scripts/dashboard-serve.py
python scripts/dashboard-serve.py --port 9000 --no-browser
```

5. Access the dashboard at `http://127.0.0.1:8080` (default port).
6. Use the API endpoints for programmatic access:

```text
GET /api/health
GET /api/data
GET /api/skills?q=&category=&path=
GET /api/memory?category=&status=&project=
GET /api/graph/nodes?type=&q=&limit=
GET /api/graph/edges?type=&node=&limit=
GET /api/graph/node/{id}
GET /api/graph/visualize?focus=&nodeType=&edgeType=&depth=&limit=
GET /api/discovery/search?q=&type=&path=&limit=
GET /api/discovery/explain/{id}?q=
GET /api/repository?category=&q=&limit=
```

7. Run unified validation to confirm no regressions across all phases.

## Phase 6 MCP Integration Workflow (Implemented)

1. Start the MCP server over stdio: `python scripts/mcp-server.py`
2. Run the automated smoke test: `python scripts/mcp-smoke-test.py`
3. Configure MCP clients using examples in `examples/mcp/`.
4. The server is read-only by default with no network calls.
5. Run unified validation to confirm MCP integration passes.

## Phase 7 Release Hardening Workflow (Implemented)

1. Bootstrap: `python scripts/ai-os.py bootstrap`
2. Status: `python scripts/ai-os.py status`
3. Doctor: `python scripts/ai-os.py doctor`
4. Generate: `python scripts/ai-os.py build`
5. Validate: `python scripts/ai-os.py validate`
6. Release check: `python scripts/ai-os.py release-check`
7. Package: `python scripts/ai-os.py package`
8. Backup: `python scripts/ai-os.py backup`
9. Restore: `python scripts/ai-os.py restore <path>`

## Phase 8 Continuous Learning and Agent Orchestration Workflow (Implemented)

1. Classify: `python scripts/ai-os.py classify "<task>"`
2. Plan: `python scripts/ai-os.py plan "<task>" --explain`
3. Start a session: `python scripts/ai-os.py session start "<task>"`
4. Approve the plan if requested: `python scripts/ai-os.py approval approve <id>`
5. Record a validation result: `python scripts/ai-os.py session validate <id> --name X --status pass`
6. Complete the session: `python scripts/ai-os.py session complete <id>`
7. Review the generated memory suggestion: `python scripts/ai-os.py memory-suggestions show <id>`
8. Approve its permanent-memory approval, then approve the suggestion itself — this is the only
   path that writes into `memory/`.
9. Check knowledge health and review-due items: `python scripts/ai-os.py knowledge-health`,
   `knowledge-gaps`, `review-due`.
10. Record feedback and inspect the audit trail: `feedback add`, `audit list`, `audit validate`.
11. Run unified validation to confirm no regressions across all phases.
10. Clean: `python scripts/ai-os.py clean-generated --confirm`

## Phase 9 Professional Context Workflow (Implemented)

1. List configured profiles (read-only): `python scripts/ai-os.py profile list`
2. Show the active profile, or a specific one, (read-only): `python scripts/ai-os.py profile show
   [profile-id]`
3. Switch profiles (explicit, approval-gated): `python scripts/ai-os.py profile switch
   <profile-id>` — the first run requests a `profile-switch` approval and stops; approve it with
   `python scripts/ai-os.py approval approve <id>`, then re-run the switch to activate it.
4. Scaffold the curated overview once (safe, no-overwrite): `python scripts/ai-os.py profile
   sync-knowledge`.
5. Checkpoint the current curated overview into a dated snapshot (never rewrites `overview.md`):
   `python scripts/ai-os.py profile sync-knowledge --force-refresh`.
6. Query professional context read-only via MCP: `get_professional_profile`, `list_expertise`,
   `get_work_activity_summary`.
7. Run unified validation to confirm no regressions across all phases.
