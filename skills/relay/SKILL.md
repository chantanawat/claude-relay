---
name: relay
description: Use when the session's main model is an expensive one (Opus, Fable, or any model you want to keep off the keyboard) and the user asks for application code to be written or changed — build a feature/screen/module/flow (สร้างระบบ/หน้า/ฟีเจอร์, implement, build), fix or debug a bug (แก้บั๊ก, debug, พัง, ไม่ทำงาน), or any edit inside the project's source folders. Also on an explicit "/relay". Not for read-only questions, deploys, or edits to plans, notes and docs.
---

# Relay — the planner never writes app code

**The expensive main model plans, briefs, dispatches and adjudicates. It does not write or edit application code.** Every code change goes to a cheaper seat: Sonnet at xhigh by default, Opus when the task needs judgment. A stronger, read-only seat reviews.

Why: implementation is where the tokens go. Anthropic's own advisor benchmarks show Sonnet doing the work with Opus consulted at decision points beats Sonnet alone by 2.7 pts on SWE-bench Multilingual **and** costs 11.9% less per task. Details and sources: `research.md` in this folder.

| Seat | Who | Dispatch |
|---|---|---|
| Planner | **this session** — plans, writes briefs, rules on conflicts; edits only plans/briefs/notes/docs | — |
| Coder | `relay-coder` — Sonnet, xhigh | `Agent(subagent_type: "relay-coder")` |
| Coder (escalation) | `relay-coder-opus` — Opus, high | `Agent(subagent_type: "relay-coder-opus")` |
| Reviewer | `relay-reviewer` — Opus, read-only | `Agent(subagent_type: "relay-reviewer")` |
| Diff-check | `relay-diffcheck` — Sonnet, xhigh, read-only | `Agent(subagent_type: "relay-diffcheck")` |

The seats run with `omitClaudeMd` and a `tools` allowlist, so they start at roughly 8K tokens instead of 35–70K — and they **do not see your CLAUDE.md**. Every project rule a seat must obey goes in the brief. **Always pass `subagent_type`**; an omitted model inherits the session's most expensive one.

## The line the planner does not cross

The planner may Edit/Write: plan files, task briefs, ledgers, notes, docs, skills, agent files, `CLAUDE.md`. Anything else in the project — source, tests, configs, version files, migrations — is **seat work**.

| Rationalization | Reality |
|---|---|
| "It's a one-line fix, dispatching costs more" | A seat costs ~8K to start; the planner's own edit costs a review it skipped plus the context it now carries all session. Dispatch. |
| "I already know exactly what to change" | Then the brief is trivial to write. Write it; the coder types it. |
| "The coder will just ask me questions" | Answer them in the brief up front — interfaces, exact values, acceptance test. |
| "It's just a version bump / config value" | Configs and version files are app code. Put the bump in the brief. |
| "The reviewer is Opus; it can fix it while it's there" | The reviewer is read-only by design. Findings go back to a coder seat. |

Red flags — stop: `Edit(` or `Write(` on a source path from this session · "let me quickly" · "while I'm here".

## 1. Choose the shape

| Signal | Shape |
|---|---|
| User asked a question or said "just look / don't change anything" | not relay — answer, no code changes |
| ≤2 files, spec already clear (typo, copy, one guard, a config value) | **Light** — one coder dispatch from an inline brief, then `relay-diffcheck` |
| Bug in existing code | **Debug** — planner diagnoses, coder fixes, diff-check verifies |
| New feature / screen / module, or ≥3 files | **Build** — plan → task loop → final review. Ask **one** question before the first spawn: `full relay (recommended)` · `light` · `plan only` |

Coder choice, per dispatch:

| Use `relay-coder` (Sonnet xhigh) | Use `relay-coder-opus` |
|---|---|
| brief contains the exact change or a complete spec · follows an existing pattern · 1–4 files | design judgment left open · ≥5 files with integration concerns · money, auth, tenant, concurrency or data-migration code · third attempt after two Sonnet fix rounds |

## 2. The brief — the only thing a seat knows

Write it to a file (never paste it into the prompt). Sections, in order:

```
# Task: <one line>
## Where            <project folder(s) the seat may touch; everything else is off-limits>
## Change           <exact files, exact values, interfaces from earlier tasks>
## Acceptance       <the test or command that proves it, and the expected output>
## Project rules    <copy from your CLAUDE.md: comment language, lint/format command, forbidden paths (secrets), UI conventions, whether a version file must be bumped>
## Report file      <path the seat writes its full report to>
```

## 3. Light

1. Brief → `<scratch>/relay-light-<ts>.md`.
2. `Agent(subagent_type: "relay-coder")` with the brief path and report path. Wait.
3. `git diff -U10 -- <folder>` → `<scratch>/relay-diff-<ts>.patch` → `relay-diffcheck` with brief path + diff path.
4. Findings → one more coder dispatch with the findings verbatim (same seat). Then stop; note deferred minors for the user.

## 4. Debug

1. Diagnose in this session: reproduce, trace, name the root cause in ≤2 sentences. Reading, grepping and running tests are planner work; the fix is not. (If `superpowers:systematic-debugging` is installed, use it here.)
2. Brief = symptom + reproduction + root cause + the mechanism to change + the test that proves it. Dispatch `relay-coder`, or `relay-coder-opus` if the cause sits on a money/auth/concurrency path.
3. Diff to a file → `relay-diffcheck` with symptom, root cause, diff path, folder.
4. ❌ verdict or Critical → one fix dispatch with the findings. The diff-check's "same bug class elsewhere" list → one batched coder dispatch, not one per site.

## 5. Build

1. **Plan (this session).** Clarify the request if it is vague, then write a plan file with one task per section: folder, files, exact values, interfaces, acceptance test, and whether it touches UI. (`superpowers:writing-plans` produces exactly this shape.)
2. **Execute.** If `superpowers:subagent-driven-development` is installed, invoke it and state these overrides in your first line; otherwise run the same loop by hand:
   - per task: brief file → `relay-coder` (or `relay-coder-opus` per the table) → diff file → `relay-reviewer` (brief + report + diff paths, plus the plan's global constraints)
   - **fix loop: 2 rounds on the same seat, round 3 = `relay-coder-opus` fresh with the report file, then stop.** If Opus also leaves Critical/Important findings open, the defect is in the plan: revise the plan text here, record the ruling, re-dispatch the task once.
   - never two implementers in parallel · no per-task commits unless your workflow wants them
3. **Final review.** Whole-branch diff → `relay-reviewer` in `final` mode. Findings → **one** fix dispatch with the full list, **one** scoped re-review. Then hand the branch to the user with every ruling you made listed.

## 6. Token rules (each one cost a real session before it became a rule)

1. **Files, not text.** Briefs, reports and diffs travel as paths; pasted text stays in your context all session.
2. **No history in a dispatch.** A seat needs its task, the interfaces it touches, and the rules that bind it. Not "state after tasks 1–3".
3. **Batch same-shape work** into one dispatch and one review.
4. **Never two implementers in parallel** — they collide on the tree.
5. **Turn count beats token price** — Sonnet at xhigh, not Haiku: the cheaper model takes 2–3× the turns on multi-step work.
6. **One fix wave after the final review**, one scoped re-review. Never one fixer per finding.
7. **Seats start cold and see no CLAUDE.md** — rules go in the brief; keep briefs small.
8. **Per-spawn floor ≈ 8K** with these agent files (system prompt + skill listing). Light = 2 spawns ≈ 16K; that is the price of the planner not coding — accept it.

## Lite alternative (no spawning)

`/model sonnet` + `/advisor opus` (or `/advisor fable` if you have Fable access) — Sonnet is the main model and consults the stronger one at decision points. It also satisfies "the expensive model never codes".

## Why this roster — `research.md`

Effort levels, ultracode, the advisor benchmarks, Sonnet 5 xhigh vs Opus 5 coding scores, and the token traps behind rules 1–8. Read it before changing a seat's model or effort.
