#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data=json.loads((root/"skills.json").read_text(encoding="utf-8"))
rows=data.get("skills",[])
print(f"{'ID':<28} {'NAME':<28} {'VERSION':<10} {'STATUS':<12} PATH")
print("-"*110)
bad=False
for s in rows:
    exists=(root/s['path']).is_file(); bad |= not exists
    print(f"{s['id']:<28} {s['name']:<28} {s['version']:<10} {s['status']:<12} {s['path']}"+(" [MISSING]" if not exists else ""))
print(f"\n{len(rows)} skills registered.")
raise SystemExit(1 if bad else 0)
