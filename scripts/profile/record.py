"""profile/<id>.md record loading (Task 012, read-only).

Parses front matter only -- never the free-text prose body below the
`---` fence. `ai-os.py profile show` must return only sanitized,
schema-defined profile information (design.md), never "raw source
documents, raw evidence content, confidential prose, ... or unrestricted
file contents." Restricting the returned summary to exactly
`schema.PROFILE_REQUIRED_FIELDS` is the enforcement mechanism for that:
any additional front-matter key a record might contain is never surfaced.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from .schema import PROFILE_REQUIRED_FIELDS
from .validate import validate_profile_record


class ProfileRecordError(ValueError):
    pass


def _parse_scalar(raw: str):
    value = raw.strip()
    if value in {"null", "~"}:
        return None
    if value == "":
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def parse_front_matter(path: Path) -> Tuple[Dict[str, object], str]:
    """Parse the same restricted YAML-subset front matter memory records
    use (scalars and simple string lists) -- never a full YAML parser, and
    never evaluates the body as anything other than opaque prose text.
    """
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text:
        raise ProfileRecordError(f"{path}: missing YAML front matter")
    block, body = text.split("\n---\n", 1)
    lines = block.splitlines()[1:]
    data: Dict[str, object] = {}
    current = None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            item = line.strip()
            if current and isinstance(data.get(current), list) and item.startswith("- "):
                data[current].append(_parse_scalar(item[2:]))
            continue
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        value = raw.strip()
        data[key] = [] if value == "" else _parse_scalar(value)
        current = key
    return data, body


def load_profile_summary(root: Path, registry_entry: dict) -> dict:
    """Load, validate, and summarize a profile/<id>.md record.

    Returns only the fields defined in schema.PROFILE_REQUIRED_FIELDS plus
    `active` (from the registry entry) -- the prose body is read but
    discarded, and any front-matter key outside the fixed schema is never
    included in the result. Raises ProfileRecordError, without partial
    output, if the record is missing or fails structural validation.
    """
    rel_path = registry_entry.get("path")
    if not rel_path:
        raise ProfileRecordError(f"registry entry {registry_entry.get('id')!r} has no path")

    record_path = root / rel_path
    if not record_path.is_file():
        raise ProfileRecordError(f"profile record not found: {rel_path}")

    metadata, _body = parse_front_matter(record_path)
    failures, _warnings = validate_profile_record(metadata)
    if failures:
        raise ProfileRecordError(f"invalid profile record {rel_path}: " + "; ".join(failures))

    summary = {field: metadata.get(field) for field in PROFILE_REQUIRED_FIELDS}
    summary["active"] = bool(registry_entry.get("active"))
    return summary
