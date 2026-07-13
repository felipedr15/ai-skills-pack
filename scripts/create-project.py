#!/usr/bin/env python3
import argparse
from pathlib import Path
TYPES=['generic-project','web-app','power-apps','power-automate','python','documentation','internal-it','automation']
def main():
    ap=argparse.ArgumentParser(description='Create an AI OS project from a starter; no Git or dependency operations are performed.')
    ap.add_argument('--name'); ap.add_argument('--type',choices=TYPES); ap.add_argument('--destination'); ap.add_argument('--owner',default='[OWNER]'); ap.add_argument('--technology',default='[TECHNOLOGY]'); ap.add_argument('--status',default='planning'); ap.add_argument('--force',action='store_true')
    a=ap.parse_args(); name=a.name or input('Project name: ').strip(); typ=a.type or input('Project type ('+', '.join(TYPES)+'): ').strip(); dest=Path(a.destination or input('Destination: ').strip()).expanduser().resolve()
    if typ not in TYPES: ap.error('unsupported project type')
    if dest.exists() and any(dest.iterdir()) and not a.force: ap.error('destination is non-empty; use --force to merge without deleting existing files')
    src=Path(__file__).resolve().parents[1]/'templates'/'project-starters'/typ; dest.mkdir(parents=True,exist_ok=True)
    created=[]
    for p in src.rglob('*'):
        if p.is_dir(): continue
        out=dest/p.relative_to(src); out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists() and not a.force: ap.error(f'would overwrite {out}')
        text=p.read_text(encoding='utf-8').replace('[PROJECT NAME]',name).replace('[OWNER]',a.owner).replace('[TECHNOLOGY]',a.technology).replace('[CURRENT STATUS]',a.status)
        out.write_text(text,encoding='utf-8'); created.append(out)
    print('\n'.join(str(x) for x in created)); print(f'Created {len(created)} files in {dest}')
if __name__=='__main__': main()
