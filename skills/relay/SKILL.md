---
name: relay
description: Use when the session's main model is an expensive one (Opus, Fable, or any model you want to keep off the keyboard) and the user asks for application code to be written or changed — build a feature/screen/module/flow (สร้างระบบ/หน้า/ฟีเจอร์, implement, build), fix or debug a bug (แก้บั๊ก, debug, พัง, ไม่ทำงาน), or any edit inside the project's source folders. Also on an explicit "/relay". Not for read-only questions, deploys, or edits to plans, notes and docs.
---

# Relay — the planner never writes app code

**The expensive main model plans, briefs, dispatches and adjudicates. It does not write or edit application code.** Every code change goes to a cheaper seat: Sonnet by default, Opus only where the subscription tier allows it. A stronger, read-only seat reviews.

Why: implementation is where the tokens go. Anthropic's own advisor benchmarks show Sonnet doing the work with Opus consulted at decision points beats Sonnet alone by 2.7 pts on SWE-bench Multilingual **and** costs 11.9% less per task. Details and sources: `research.md` in this folder.

| Seat | Who | When |
|---|---|---|
| Planner | **this session** — plans, writes briefs, rules on conflicts; edits only plans/briefs/notes/docs | — |
| Coder (lite) | `relay-coder-lite` — Sonnet, medium, ≤30 turns | light shape when the brief contains the exact change |
| Coder | `relay-coder` — Sonnet, xhigh | default for every other dispatch |
| Coder (Opus) | `relay-coder-opus` — Opus, high | tier `max`: per the coder table · tier `pro`: only after the user says yes in the escalation question |
| Coder (top) | `relay-coder-top` — `model: inherit` = the session's own model (Fable on a Fable session) | only after the user says yes in the escalation question |
| Reviewer | `relay-reviewer` — Opus, read-only | build tasks, final review, and every pro-tier escalation |
| Diff-check | `relay-diffcheck` — Sonnet, xhigh, read-only | light and debug shapes |

Dispatch is always `Agent(subagent_type: "<seat>")`. The seats run with `omitClaudeMd` and a `tools` allowlist, so they start at roughly 8K tokens instead of 35–70K — and they **do not see your CLAUDE.md**. Every project rule a seat must obey goes in the brief. **Always pass `subagent_type`**; an omitted model inherits the session's most expensive one.

## 0. Tier — who is allowed to burn Opus

Relay runs on a subscription window, and Max is sold as 5× or 20× the Pro usage. Opus as a *coder* can run 80 turns of editing; Opus as a *reviewer* is one read-only pass over a diff file. On Pro the coder seat is where the quota dies, so Opus reads and Sonnet types.

Resolve the tier **before the first dispatch of a session**, in this order:

1. The project `CLAUDE.md` has a line that is exactly `relay-tier: max` or exactly `relay-tier: pro` → use it, no question.
2. Otherwise ask **once** per session with `AskUserQuestion` (options `max` · `pro`). If the shape is build, fold it into the one build question.
3. No answer channel (headless, cloud run, hook) → assume `pro`.

| Tier | Sonnet seats | Opus | Top seat |
|---|---|---|---|
| **max** | `relay-coder-lite`, `relay-coder`, `relay-diffcheck` | reviews (`relay-reviewer`) **and** codes when the coder table says so (`relay-coder-opus`) | `relay-coder-top` (Fable on a Fable session) — only after the user says yes |
| **pro** | same; escalation = a **fresh** `relay-coder` seat | **reviews only** (`relay-reviewer`) — never codes until the user says yes in the escalation question | `relay-coder-opus` — only after the user says yes |

## The line the planner does not cross

The planner may Edit/Write: plan files, task briefs, ledgers, notes, docs, skills, agent files, `CLAUDE.md`. Anything else in the project — source, tests, configs, version files, migrations — is **seat work**.

| Rationalization | Reality |
|---|---|
| "It's a one-line fix, dispatching costs more" | A seat costs ~8K to start; the planner's own edit costs a review it skipped plus the context it now carries all session. Dispatch `relay-coder-lite`. |
| "I already know exactly what to change" | Then the brief is trivial to write. Write it; the coder types it. |
| "The coder will just ask me questions" | Answer them in the brief up front — interfaces, exact values, acceptance test. |
| "It's just a version bump / config value" | Configs and version files are app code. Put the bump in the brief. |
| "The reviewer is Opus; it can fix it while it's there" | The reviewer is read-only by design. Findings go back to a coder seat. |
| "Sonnet failed twice, Opus will just fix it" | On pro that is the user's quota, not yours. Ask (§6). |
| "It's 12 files, that's ≥5, so Opus" | Volume is not judgment. Twelve copies of one change are a bulk Sonnet batch; Opus is for changes that depend on each other. |
| "Context is only 30% full, the session is fine" | Every turn re-sends the whole context. Quota drains with turns × context, not with the fill level. Hand off at the thresholds in §8. |

Red flags — stop: `Edit(` or `Write(` on a source path from this session · "let me quickly" · "while I'm here" · a third fix round nobody asked for.

## 1. Choose the shape

| Signal | Shape |
|---|---|
| User asked a question or said "just look / don't change anything" | not relay — answer, no code changes |
| `/relay resume <handoff-file>` or a fresh session opened with a handoff file | **Resume** — read the handoff file, continue at its `Next step`; re-read nothing else (§8) |
| ≤2 files, spec already clear (typo, copy, one guard, a config value) | **Light** — one coder dispatch from an inline brief, then `relay-diffcheck` |
| Bug in existing code | **Debug** — planner diagnoses, coder fixes, diff-check verifies |
| New feature / screen / module, or ≥3 files | **Build** — plan → task loop → final review. Ask **one** question before the first spawn: `full relay (recommended)` · `light` · `plan only` (add the tier to the same question if it is still unknown) |

Coder choice, per dispatch:

| Signal | tier `max` | tier `pro` |
|---|---|---|
| light shape, brief contains the exact change, ≤2 files | `relay-coder-lite` | `relay-coder-lite` |
| complete spec · follows an existing pattern · 1–4 files | `relay-coder` | `relay-coder` |
| **bulk**: many files, the same mechanical change in each (rename, import swap, copy/i18n keys, a config value across services, a pattern applied to N call sites) | `relay-coder`, batches of 5–8 files per dispatch, one `relay-diffcheck` per batch — **never Opus, on any tier** | same |
| design judgment left open · ≥5 files whose changes **depend on each other** (a shared interface, schema or contract changes) · money, auth, tenant, concurrency or data-migration code | `relay-coder-opus` | `relay-coder`, and the check goes to `relay-reviewer` (Opus) instead of `relay-diffcheck` — even in light/debug |
| after two failed fix rounds | see §6 — automatic round 3 = `relay-coder-opus` | see §6 — automatic round 3 = fresh `relay-coder` + `relay-reviewer` |

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
2. `relay-coder-lite` if the brief states the exact change; `relay-coder` otherwise. Pass the brief path and report path. Wait. A `NEEDS_CONTEXT` from the lite seat means the change was not as mechanical as it looked → re-dispatch `relay-coder` with the same files.
3. `git diff -U10 -- <folder>` → `<scratch>/relay-diff-<ts>.patch` → `relay-diffcheck` with brief path + diff path (`relay-reviewer` instead on pro when the change touches money/auth/tenant/concurrency).
4. Findings → the fix loop in §6. Deferred minors go to the user.

## 4. Debug

1. Diagnose in this session: reproduce, trace, name the root cause in ≤2 sentences. Reading, grepping and running tests are planner work; the fix is not. (If `superpowers:systematic-debugging` is installed, use it here.)
2. Brief = symptom + reproduction + root cause + the mechanism to change + the test that proves it. Dispatch per the coder table (money/auth/concurrency path: `relay-coder-opus` on max, `relay-coder` + `relay-reviewer` on pro).
3. Diff to a file → `relay-diffcheck` (or `relay-reviewer`, see step 2) with symptom, root cause, diff path, folder.
4. ❌ verdict or Critical → the fix loop in §6. The diff-check's "same bug class elsewhere" list → one batched coder dispatch, not one per site.

## 5. Build

1. **Plan (this session).** Clarify the request if it is vague, then write a plan file with one task per section: folder, files, exact values, interfaces, acceptance test, and whether it touches UI. (`superpowers:writing-plans` produces exactly this shape.)
2. **Execute.** If `superpowers:subagent-driven-development` is installed, invoke it and state these overrides in your first line; otherwise run the same loop by hand:
   - per task: brief file → coder per the table → diff file → `relay-reviewer` (brief + report + diff paths, plus the plan's global constraints)
   - fix rounds follow §6 — never a third round without the automatic escalation, never a fourth without asking the user
   - never two implementers in parallel · no per-task commits unless your workflow wants them
3. **Final review.** Whole-branch diff → `relay-reviewer` in `final` mode. Findings → **one** fix dispatch with the full list, **one** scoped re-review. Then hand the branch to the user with every ruling you made listed.

## 6. Fix loop — two rounds, one automatic escalation, then ask

Applies to every shape. A "round" = one coder dispatch carrying the open findings verbatim, followed by one check (`relay-diffcheck` or `relay-reviewer` in `re-review` mode).

| Round | tier `max` | tier `pro` |
|---|---|---|
| 1, 2 | same seat that wrote the code, findings verbatim | same |
| 3 (automatic) | `relay-coder-opus`, fresh, with the report file (it holds every attempt) | **fresh** `relay-coder` seat with the report file; the check is `relay-reviewer` (Opus) — Sonnet types, Opus reads |
| still open after 3 | **stop and ask** | **stop and ask** |

The question is one `AskUserQuestion`, and the options depend on the tier:

- **max:** `Fable analyses and fixes (relay-coder-top — most expensive seat)` · `Opus codes once more (relay-coder-opus)` · `revise the plan here, re-dispatch Sonnet once` · `stop, hand over as-is`
- **pro:** `Opus codes (relay-coder-opus — burns Pro quota fast)` · `revise the plan here, re-dispatch a fresh Sonnet seat once` · `stop, hand over as-is`

Rules for the round after the answer:
- The chosen seat gets the brief, the report file with every prior attempt, the open findings, and explicit permission to **re-derive the root cause**. `relay-coder-top` and `relay-coder-opus` may answer `NEEDS_CONTEXT: the diagnosis/plan is wrong because …` — that is a result, not a failure; fix the plan text here.
- One check after it, no further fix rounds. Anything still open → revise the plan text here, record the ruling, re-dispatch once, then stop and list the deferred findings for the user.
- No answer channel → take the "revise the plan" path once, then stop and report. Never pick Opus or Fable on the user's behalf.

## 7. Token rules (each one cost a real session before it became a rule)

1. **Files, not text.** Briefs, reports and diffs travel as paths; pasted text stays in your context all session.
2. **No history in a dispatch.** A seat needs its task, the interfaces it touches, and the rules that bind it. Not "state after tasks 1–3".
3. **Batch same-shape work** into one dispatch and one review.
4. **Never two implementers in parallel** — they collide on the tree.
5. **Turn count beats token price** — Sonnet at xhigh, not Haiku: the cheaper model takes 2–3× the turns on multi-step work. The lite seat is medium only because its brief already contains the answer.
6. **One fix wave after the final review**, one scoped re-review. Never one fixer per finding.
7. **Seats start cold and see no CLAUDE.md** — rules go in the brief; keep briefs small.
8. **Per-spawn floor ≈ 8K** with these agent files (system prompt + skill listing). Light = 2 spawns ≈ 16K; that is the price of the planner not coding — accept it.
9. **Opus reads, Sonnet types on pro.** An Opus coder seat is the user's decision, asked once, never assumed.
10. **Turns drain quota even when the window looks empty.** Σ(context × turns) is the bill; hand off at the §8 thresholds instead of pushing one more task through a 90-turn session.
11. **Volume goes to Sonnet, on every tier.** Bulk same-shape edits are batches of 5–8 files per dispatch; Opus only when changes depend on each other.

## 8. Session length — hand off, don't grow

Each turn re-sends the whole context, so the price of a session is the **sum of context over turns**, not the size of the context at the end. A relay session grows slower than a hand-coding one (seats carry the code; the planner carries short report contracts), but it still grows every dispatch, and long contexts also make the planner worse at ruling on conflicts. Prompt caching cuts the re-send to a fraction, but the cache expires between turns and never shrinks what you carry.

Hand off when **either** threshold is reached — check at every task boundary (after a check passes, before the next brief), never mid fix-loop:

| Tier | planner turns | context used (`/context` or the status line) |
|---|---|---|
| **max** | ~90 | ≥50% |
| **pro** | ~50 | ≥40% |

Seat turns are separate (`maxTurns` in the agent files caps each seat's own context); these numbers are the **planner's** turns in this session. If your workspace rules set a lower split point, theirs wins.

Hand-off procedure:
1. Write `<scratch>/relay-handoff-<ts>.md`: tier · shape · plan file path · task ledger (done / open, with report paths) · open findings verbatim · every ruling made · the exact `Next step` (which task, which seat, which brief).
2. Tell the user in two lines: the handoff path and `open a new session, then /relay resume <path>`. Do not start the next task.
3. The new session resumes from the file and reads nothing else up front — not the plan's finished tasks, not the old reports.

Build shape: write the plan so the ledger lives in the plan file from the start; then the handoff is the plan file plus a `Next step` line.

## Lite alternative (no spawning)

`/model sonnet` + `/advisor opus` (or `/advisor fable` if you have Fable access) — Sonnet is the main model and consults the stronger one at decision points. It also satisfies "the expensive model never codes".

## Why this roster — `research.md`

Effort levels, ultracode, the advisor benchmarks, Sonnet 5 xhigh vs Opus 5 coding scores, the subscription-tier reasoning behind §0 and §6, the turn economics behind §8, and the token traps behind rules 1–11. Read it before changing a seat's model or effort.
