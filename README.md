# Relay — plan on your main model, code on Sonnet, review on Opus

A Claude Code plugin: one skill (`/relay`) + four subagent seats. **The expensive main model never writes application code.** It plans, writes a brief, dispatches a Sonnet (xhigh) coder, and lets an Opus reviewer check the diff. Small fixes, bug fixes and full features all go through a seat.

Why it pays: Anthropic's own advisor benchmarks show Sonnet doing the work with Opus at decision points beats Sonnet alone by **+2.7 pt SWE-bench Multilingual at −11.9% cost per task**. Implementation is where the tokens go, so that is the seat that gets the cheaper model. Full numbers and sources: [`skills/relay/research.md`](skills/relay/research.md).

## Install

```
/plugin marketplace add chantanawat/claude-relay
/plugin install relay@claude-relay
```

Then restart Claude Code (agent files load at session start). Optional but recommended: the official `superpowers` plugin — relay uses its `writing-plans`, `subagent-driven-development` and `systematic-debugging` skills when present, and falls back to a manual loop when not.

Requirements: Claude Code **v2.1.271+** (for `omitClaudeMd`; older versions still work, the seats just cost more), and a plan with Opus access (Pro/Max/Team/API). On a Sonnet-only plan, change `model: opus` to `model: sonnet` in `agents/relay-reviewer.md` and `agents/relay-coder-opus.md`.

## Use

- Just ask for code: "add a CSV export to the orders page", "fix the login redirect bug". The skill triggers itself on build/fix/debug requests; `/relay` forces it.
- Three shapes, chosen automatically: **light** (≤2 files → one coder + diff-check), **debug** (planner diagnoses, coder fixes, diff-check verifies), **build** (plan → task loop → final Opus review; asks one question first).
- Seats: `relay-coder` Sonnet xhigh · `relay-coder-opus` Opus (escalation) · `relay-reviewer` Opus, read-only · `relay-diffcheck` Sonnet xhigh, read-only.

## What makes it cheap

| Lever | Effect |
|---|---|
| `omitClaudeMd: true` + `tools:` allowlist on every seat | a fresh seat starts at **~8K tokens** instead of 35–70K (no CLAUDE.md, no MCP catalog) |
| briefs, reports, diffs travel as **files**, never pasted text | the planner's context stays small all session |
| fix loop capped at 2 rounds, then Opus once, then fix the plan | no ping-pong |
| one fix wave after the final review | no fixer-per-finding |

Because the seats never see your CLAUDE.md, **put the project rules in the brief** — the skill has a brief template with a `Project rules` section.

## FAQ

**Does relay force a specific planner model?** No. A skill cannot change the session model. The planner is whatever `/model` you opened the session with; only the four seats are pinned (`model: sonnet` / `model: opus` in their frontmatter — aliases that resolve to the newest model your plan has). Best results with Opus or Fable as the planner; on Sonnet it still enforces the split and keeps your main context clean.

**Why Sonnet xhigh and not Opus as the default coder?** For pattern-following work (1–4 files, complete spec) Sonnet 5 xhigh is close enough on the benchmarks and 2.5× cheaper per token. Opus 5 wins clearly on long, hard tasks (SWE-bench Pro ~63% vs ~79%), so relay escalates to `relay-coder-opus` for design judgment, ≥5 integrated files, money/auth/concurrency code, and after two failed Sonnet rounds. See `research.md`.

**Can I change a seat's model or effort?** Yes — edit the frontmatter in `agents/*.md`. Note that edited agent files do not reload mid-session; restart Claude Code.

**Does it work without superpowers?** Yes. The skill describes the manual loop (brief file → coder → diff file → reviewer).

## ภาษาไทย

Plugin นี้บังคับให้ **โมเดลแพง (Opus/Fable) ที่คุณเปิด session อยู่ ไม่เขียนโค้ดเอง** — มันวางแผน เขียน brief แล้วส่งให้ Sonnet 5 (xhigh) พิมพ์โค้ด และให้ Opus 5 ตรวจ diff (read-only) ทุกงานไม่ว่าเล็กหรือใหญ่

- ติดตั้ง: `/plugin marketplace add chantanawat/claude-relay` → `/plugin install relay@claude-relay` → เปิด Claude Code ใหม่
- ใช้: สั่งงานโค้ดตามปกติ ("เพิ่มหน้า…", "แก้บั๊ก…") skill จะทำงานเอง หรือพิมพ์ `/relay`
- ไม่ได้บังคับ model ของ planner — planner = model ที่คุณเลือกใน `/model` · seat ทั้ง 4 ตัว pin model ไว้ในไฟล์ `agents/*.md`
- แพ็กเกจ Free (มีแค่ Sonnet): แก้ `model: opus` → `model: sonnet` ใน `relay-reviewer.md` และ `relay-coder-opus.md`
- ทำไมประหยัด: seat เริ่มที่ ~8K tokens (ไม่โหลด CLAUDE.md/MCP) · ส่งงานเป็นไฟล์ไม่ paste · วน fix ได้แค่ 2 รอบ · เหตุผลและตัวเลข bench อยู่ใน `skills/relay/research.md` (มีสรุปไทย)

## License

MIT
