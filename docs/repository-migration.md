# Repository Migration

Date: 2026-08-26

## Canonical Repository

- Old owner: `frojas15`
- New owner: `felipedr15`
- Repository: `felipedr15/ai-skills-pack`
- Canonical URL: `https://github.com/felipedr15/ai-skills-pack`

## Updated References

- `docs/cli-reference.md`: clone command updated to `https://github.com/felipedr15/ai-skills-pack.git`.
- `RELEASE_NOTES_v0.9.0.md`: comparison URL updated to the new canonical owner.
- Local Git remote `origin`: updated to `https://github.com/felipedr15/ai-skills-pack.git`.

## Intentional Historical References

No remaining `frojas15` source references were found after the migration pass. Future historical references may remain only when the text is explicitly documenting past ownership rather than instructing users where to clone, compare, or file work.

## Verification

Run:

```powershell
rg -n "frojas15|github.com/frojas15|frojas15/ai-skills-pack"
git remote -v
```
