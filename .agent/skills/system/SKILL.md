# System Skill

Combined skill for skill orchestration, superpower behavior, and platform adaptation.

This combines Superpower, Using Superpowers, and platform tool mapping references.

## Purpose

Help AI agents select and apply the correct skill for the task.

## Superpower Mode

Goal:
Deliver complete solutions by combining relevant skills.

Use:

- Creator
- Analytical
- Testing
- Frontend
- Communication
- Research
- Thinking

Steps:

1. Analyze
2. Design
3. Build
4. Test
5. Optimize
6. Communicate clearly

Output:

- Full solution
- Production-ready code when applicable
- Clear explanation

## Skill Selection Rule

Before starting a task, check whether a skill applies.

If a skill applies, use it.

Examples:

- Writing, emails, tickets, summaries → Communication Skill
- Building apps or UI → Build Skill
- Problem solving or simplifying → Thinking Skill
- Research and summaries → Research Skill
- Coordinating multiple skills → System Skill

## Skill Priority

When multiple skills could apply:

1. Process skills first
   - Thinking
   - Research
   - System

2. Implementation skills second
   - Build
   - Testing
   - UI/UX

3. Communication skill last
   - Use it to clean the final output

## Platform Adaptation

Skills may reference tools from other AI platforms.

Use `references/` files for mappings:

- `codex-tools.md`
- `copilot-tools.md`
- `gemini-tools.md`

## Output Rule

After completing the work, apply Communication Skill standards:

- Clear
- Specific
- Natural
- Useful
- No unnecessary filler
