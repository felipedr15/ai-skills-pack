#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; failures=[]; warnings=[]; passes=[]
def fail(x): failures.append(x)
def warn(x): warnings.append(x)
def ok(x): passes.append(x)
roots=['README.md','AGENTS.md','CLAUDE.md','WORKFLOW.md','ARCHITECTURE.md','ROADMAP.md','CONTRIBUTING.md','CHANGELOG.md','SECURITY.md','GOVERNANCE.md','skills.json','agents.json','prompts.json','.gitignore']
dirs=['.github','.kiro','.agent/skills','agents','prompts','templates','standards','knowledge','references','scripts']
for x in roots+dirs: (ok if (ROOT/x).exists() else fail)(f'exists: {x}')
registries={}
for n in ['skills','agents','prompts']:
    try: registries[n]=json.loads((ROOT/f'{n}.json').read_text(encoding='utf-8'))[n]; ok(f'valid {n}.json')
    except Exception as e: fail(f'invalid {n}.json: {e}'); registries[n]=[]
allowed={'draft','experimental','stable','deprecated','archived'}; ids=set()
def frontmatter(path):
    text=path.read_text(encoding='utf-8-sig')
    if not text.startswith('---\n') or '\n---\n' not in text:
        return {}
    block=text.split('\n---\n',1)[0].splitlines()[1:]
    result={}
    for line in block:
        if line and not line[0].isspace() and ':' in line:
            key,value=line.split(':',1); result[key.strip()]=value.strip().strip('"')
    return result
for s in registries['skills']:
    missing=[k for k in ['id','name','path','version','status','description','triggers','dependencies'] if k not in s]
    if missing: fail(f"skill {s.get('id','?')} missing {missing}"); continue
    if s['id'] in ids: fail(f"duplicate skill id: {s['id']}")
    ids.add(s['id'])
    if not re.fullmatch(r'\d+\.\d+\.\d+',s['version']): fail(f"invalid version: {s['id']}")
    if s['status'] not in allowed: fail(f"invalid status: {s['id']}")
    path=ROOT/s['path']
    if not path.is_file(): fail(f"missing skill path: {s['path']}")
    else:
        meta=frontmatter(path)
        required={'name','id','version','description','triggers','inputs','outputs','dependencies','status','replaces','deprecatedBy'}
        missing_meta=sorted(required-set(meta))
        if missing_meta: fail(f"skill metadata missing in {s['id']}: {missing_meta}")
        for key in ('id','name','version','status','description'):
            if str(s[key]) != meta.get(key): fail(f"skill registry mismatch for {s['id']}: {key}")
        if not (path.parent/'README.md').is_file(): fail(f"missing skill README: {path.parent.relative_to(ROOT)}")
for s in registries['skills']:
    for d in s.get('dependencies',[]):
        if d not in ids: fail(f"invalid dependency {d} in {s['id']}")
required_agents={'planner','architect','researcher','builder','reviewer','qa','documentation-writer','security-reviewer','deployment-manager','project-manager'}
required_prompts={'plan','specify','design','execute','debug','review','qa','research','document','deploy','create-skill'}
for kind,required in [('agents',required_agents),('prompts',required_prompts)]:
    got={x.get('id') for x in registries[kind]}
    for miss in sorted(required-got): fail(f'missing {kind[:-1]}: {miss}')
    for x in registries[kind]:
        if not (ROOT/x.get('path','')).is_file(): fail(f"missing registered path: {x.get('path')}")
memory={'README.md','AGENTS.md','CLAUDE.md','ARCHITECTURE.md','REQUIREMENTS.md','DESIGN.md','TASKS.md','decisions.md','HANDOFF.md','SESSION.md','TESTING.md','KNOWN_ISSUES.md','CHANGELOG.md','ROADMAP.md','RELEASE_NOTES.md','RETROSPECTIVE.md'}
for base in [ROOT/'templates/project-memory']+list((ROOT/'templates/project-starters').iterdir()):
    if base.is_dir():
        for n in memory:
            if not (base/n).is_file(): fail(f'missing project-memory file: {base.relative_to(ROOT)}/{n}')
required_specs={'README.md','requirements.md','design.md','tasks.md','testing-plan.md','deployment-plan.md','retrospective.md'}
for n in required_specs:
    if not (ROOT/'templates/specifications'/n).is_file(): fail(f'missing specification template: {n}')
actual_skills={p.relative_to(ROOT).as_posix() for p in ROOT.glob('.agent/skills/**/SKILL.md')}
registered_skills={s.get('path') for s in registries['skills']}
for path in sorted(actual_skills-registered_skills): fail(f'unregistered skill: {path}')
for path in sorted(registered_skills-actual_skills): fail(f'registered non-skill path: {path}')
required_files=[
    '.kiro/steering/product.md','.kiro/steering/structure.md','.kiro/steering/technology.md','.kiro/steering/workflow.md','.kiro/specs/README.md',
    '.github/copilot-instructions.md','.github/workflows/validate.yml',
    '.github/instructions/markdown.instructions.md','.github/instructions/skills.instructions.md','.github/instructions/prompts.instructions.md','.github/instructions/specifications.instructions.md','.github/instructions/templates.instructions.md',
    'standards/documentation.md','standards/naming.md','standards/git.md','standards/testing.md','standards/security.md','standards/accessibility.md','standards/code-review.md','standards/release-management.md',
    'references/chatgpt.md','references/claude.md','references/codex.md','references/copilot.md','references/kiro.md','references/v0.md','references/vercel.md','references/canva.md','references/mcp.md','references/workflow-examples.md',
    'scripts/validate-repo.py','scripts/validate-markdown.ps1','scripts/create-project.py','scripts/list-skills.py']
for path in required_files:
    if not (ROOT/path).is_file(): fail(f'missing required file: {path}')
for md in ROOT.rglob('*.md'):
    if '.git' in md.parts: continue
    data=md.read_bytes(); rel=md.relative_to(ROOT).as_posix()
    if not data.strip(): fail(f'empty Markdown: {rel}')
    if data and not data.endswith(b'\n'): warn(f'missing final newline: {rel}')
    text=data.decode('utf-8',errors='replace'); heads=[x.strip() for x in text.splitlines() if x.startswith('#')]
    for a,b in zip(heads,heads[1:]):
        if a==b: warn(f'duplicate adjacent heading: {rel}: {a}')
    for target in re.findall(r'\[[^]]*\]\((?!https?://|mailto:|#)([^)]+)\)',text):
        clean=target.split('#')[0].replace('%20',' ')
        if clean and not (md.parent/clean).resolve().exists(): warn(f'broken relative link: {rel} -> {target}')
secret=re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+=]{16,}")
for p in ROOT.rglob('*'):
    if p.is_file() and '.git' not in p.parts and p.suffix.lower() in {'.md','.json','.yml','.yaml','.py','.ps1','.txt'}:
        if secret.search(p.read_text(encoding='utf-8',errors='ignore')): fail(f'possible secret: {p.relative_to(ROOT)}')
for d in ['agents','prompts','templates','templates/project-memory','templates/specifications','templates/project-starters','standards','knowledge','references','scripts','.kiro','.kiro/steering','.kiro/specs','.github','.github/instructions','.github/workflows']:
    if not (ROOT/d/'README.md').is_file(): fail(f'missing major folder README: {d}')
for x in passes: print('PASS',x)
for x in warnings: print('WARNING',x)
for x in failures: print('FAIL',x)
print(f'\nSummary: {len(passes)} PASS, {len(warnings)} WARNING, {len(failures)} FAIL')
raise SystemExit(1 if failures else 0)
