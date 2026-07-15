# Knowledge Health (Phase 8)

## Two Views, One Reason

There are two ways to see knowledge health, and the split is deliberate:

- **`generated/knowledge-health.json` / `.md`** — deterministic, repo-only categories (graph
  integrity, project/skill documentation coverage, memory linkage, workflow governance,
  freshness). Built by `scripts/generate-knowledge-health.py`, checked via `--check` like every
  other generated artifact, safe to commit — it produces the same score on every machine given
  the same repository content.
- **Live view (`ai-os.py knowledge-health` / `knowledge-gaps`, the dashboard, and the
  `get_knowledge_health` MCP tool)** — the same deterministic categories plus `sessionHealth` and
  `feedbackSignal`, computed at request time from local `.ai-os/` runtime state. This view is
  never written back into the committed artifact, because local session/feedback state differs
  machine to machine and would make `--check` fail constantly if it did.

## Commands

```text
python scripts/ai-os.py knowledge-health          # score + category breakdown + recommendations
python scripts/ai-os.py knowledge-gaps [--limit N] # detailed gap list
python scripts/ai-os.py review-due [--days N]      # documents due for review
```

## Scoring

Every category scores 0-100: `100` means nothing was found to flag; the score degrades with the
ratio of flagged items to items evaluated, rounded to the nearest integer. This is an explainable
heuristic, not a precise measurement — `diagnostics.scoreRange` in the JSON output says so
explicitly, and every score is accompanied by the raw counts and gap descriptions it came from.

## Known Limitation: No Search Query Log

"Frequent search queries with weak results" and "no-result searches" cannot be computed — this
system does not log search queries (no telemetry, by design). The health report's `diagnostics`
field documents this explicitly rather than fabricating a signal.

## Freshness / Review-Due

Only documents that declare `owner`, `lastReviewed`, `reviewIntervalDays`, or `nextReview` in
their front matter are tracked (deliberately excluding the generic `status` field already used by
skills and memory records for unrelated purposes). Most Phase 1-7 documents predate this
convention, so an empty `review-due` result on this repository today is expected, not a bug.
Review dates are never updated automatically — only a human editing the front matter changes them.

## Gap Categories

Frequent search queries (unavailable, see above), no-result searches (unavailable), unresolved
graph references, isolated graph nodes, project without overview/architecture/validation
checklist, skill without a validation section, memory without a project link, workflow without an
approval gate, document without an owner or review date, stale generated artifacts, unknown task
intents, repeated session failures, repeated user corrections (from feedback).

[Back to AI OS](../README.md)
