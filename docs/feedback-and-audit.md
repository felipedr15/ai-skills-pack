# Feedback and Audit (Phase 8)

## Feedback

Local, structured feedback capture — no telemetry, no upload, nothing sent anywhere.

```text
python scripts/ai-os.py feedback add --type outdated --target-type document \
    --target-id knowledge/sharepoint/README.md --comment "Refresh steps changed."
python scripts/ai-os.py feedback list [--status open] [--type outdated]
python scripts/ai-os.py feedback resolve <id>
python scripts/ai-os.py feedback stats
```

Types: `helpful, incorrect, outdated, missing-information, wrong-project, wrong-procedure,
unsafe, incomplete, ranking-problem`. Stored in `.ai-os/feedback/feedback.json` (local,
git-ignored). Comments are sanitized (control characters stripped, length capped, secret-like
patterns redacted) before being written. Feedback never modifies the document or entity it's
about — it can only contribute a count toward the `feedbackSignal` knowledge-health category (see
[Knowledge Health](knowledge-health.md)) when the same target receives repeated corrections.

## Audit Trail

Every orchestration event — workflow selection, agent selection, knowledge retrieval, approval
request/approve/reject, validation run, session completion, memory suggestion/approval/rejection,
feedback added, knowledge gap detected — is appended to `.ai-os/audit/audit-<n>.log` (JSONL,
local, git-ignored).

```text
python scripts/ai-os.py audit list [--type X] [--limit N]
python scripts/ai-os.py audit show <index>
python scripts/ai-os.py audit export [--output path.json]
python scripts/ai-os.py audit validate
```

Each entry is hash-chained: `hash = sha256(prevHash + canonical_json(event))`. `audit validate`
recomputes the chain from the genesis hash and reports any break — a modified or deleted line
changes every subsequent hash, so tampering is detectable. Files rotate to a new numbered log once
they reach the configured entry limit (`AUDIT_MAX_ENTRIES_PER_FILE`).

**What is never recorded:** secrets, tokens, full file contents, full memory bodies, full chat
transcripts, or nested object values (only flat string/number/boolean fields, each redacted and
length-capped, are kept — nested dicts are dropped rather than serialized, so a caller can't
accidentally log an entire file's contents through a details payload).

## Troubleshooting

- **`review-due` always returns nothing.** Expected until a document's front matter declares
  `owner`/`lastReviewed`/`reviewIntervalDays`/`nextReview` — see
  [Knowledge Health](knowledge-health.md).
- **`memory-suggestions approve` fails with "no approved permanent-memory approval".** Run
  `ai-os.py approval list --status pending`, find the matching approval, then
  `ai-os.py approval approve <id>` first.
- **`session complete` fails with "must be in 'validation' status".** Run
  `ai-os.py session validate <id> --name X --status pass` first.
- **`audit validate` reports a chain break.** Treat this as a security incident — something
  modified `.ai-os/audit/` outside the normal append path. Investigate before trusting the log.

[Back to AI OS](../README.md)
