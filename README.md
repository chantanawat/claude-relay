# Relay — วางแผนด้วยโมเดลหลัก · เขียนโค้ดด้วย Sonnet · ตรวจด้วย Opus

🇹🇭 ภาษาไทยอยู่ด้านบน · 🇬🇧 [English below ↓](#english)

Plugin สำหรับ Claude Code: skill เดียว (`/relay`) + subagent 6 ที่นั่ง (seat)
**โมเดลแพงที่คุณเปิด session อยู่ (Opus / Fable) จะไม่เขียนโค้ดแอปเองเลย** — มันวางแผน เขียน brief แล้วส่งให้ Sonnet (xhigh) พิมพ์โค้ด และให้ Opus ตรวจ diff แบบ read-only ไม่ว่างานเล็กหรือใหญ่

ทำไมคุ้ม: benchmark ของ Anthropic เอง — Sonnet ทำงานโดยมี Opus ช่วยตัดสินใจ ชนะ Sonnet เดี่ยว **+2.7 pt บน SWE-bench Multilingual และถูกกว่า 11.9% ต่องาน** ส่วนที่กิน token มากที่สุดคือตอนพิมพ์โค้ด จึงเอาโมเดลถูกไปนั่งตรงนั้น ตัวเลขและแหล่งอ้างอิงทั้งหมดอยู่ใน [`skills/relay/research.md`](skills/relay/research.md) (มีสรุปไทย)

## ติดตั้ง

```
/plugin marketplace add chantanawat/claude-relay
/plugin install relay@claude-relay
```

แล้วเปิด Claude Code ใหม่ (ไฟล์ agent โหลดตอนเริ่ม session เท่านั้น)

- แนะนำให้ติดตั้ง plugin `superpowers` (official) ด้วย — relay จะใช้ skill `writing-plans`, `subagent-driven-development`, `systematic-debugging` ของมันเมื่อมี ถ้าไม่มีจะใช้ loop แบบ manual แทน
- ต้องใช้ Claude Code **v2.1.271 ขึ้นไป** (สำหรับ `omitClaudeMd` — รุ่นเก่ากว่านี้ยังใช้ได้ แค่ seat แพงขึ้น) และ plan ที่มี Opus (Pro / Max / Team / API)
- plan ที่มีแค่ Sonnet: แก้ `model: opus` → `model: sonnet` ใน `agents/relay-reviewer.md` และ `agents/relay-coder-opus.md`
- **บอก tier ให้ relay รู้** — ใส่บรรทัด `relay-tier: pro` หรือ `relay-tier: max` (บรรทัดเดียว ไม่มีอย่างอื่น) ใน `CLAUDE.md` ของโปรเจกต์ ถ้าไม่ใส่ relay จะถาม 1 ครั้งต่อ session · ไม่มีช่องให้ตอบ (headless) = ถือเป็น `pro`

## วิธีใช้

สั่งงานโค้ดตามปกติ: "เพิ่มปุ่ม export CSV ในหน้า orders", "แก้บั๊ก login redirect" — skill จะทำงานเองเมื่อเจอคำสั่ง build / fix / debug หรือพิมพ์ `/relay` เพื่อบังคับ

relay เลือกรูปแบบให้เอง 3 แบบ:

| แบบ | เมื่อไหร่ | เกิดอะไรขึ้น |
|---|---|---|
| **light** | ≤2 ไฟล์ spec ชัด | brief → `relay-coder` → `relay-diffcheck` ตรวจ diff |
| **debug** | บั๊กในโค้ดเดิม | planner หา root cause → coder แก้ → diffcheck ยืนยันว่าแก้ตรงสาเหตุ + หา bug แบบเดียวกันที่อื่น |
| **build** | ฟีเจอร์ใหม่ / ≥3 ไฟล์ | plan → วน task (coder → reviewer) → final review โดย Opus · ถามคุณ 1 คำถามก่อนเริ่ม |

ทุกแบบใช้ **fix loop เดียวกัน**: แก้ซ้ำได้ 2 รอบบน seat เดิม → รอบ 3 escalate อัตโนมัติ (Max: Opus เขียน · Pro: Sonnet ตัวใหม่เขียน + Opus ตรวจ) → ยังไม่ผ่าน **relay หยุดแล้วถามคุณ** ว่าจะใช้ Fable (Max) / Opus (Pro) / แก้ plan / หยุด — ไม่เผา quota ต่อเองเด็ดขาด

seat ทั้ง 6:

| seat | โมเดล | หน้าที่ |
|---|---|---|
| `relay-coder-lite` | Sonnet, medium, ≤30 turns | light เท่านั้น เมื่อ brief บอกการแก้ที่แน่นอนแล้ว (copy / guard / config / bump version) |
| `relay-coder` | Sonnet, xhigh | เขียนโค้ด 1 task ต่อครั้ง (ค่าเริ่มต้น) |
| `relay-coder-opus` | Opus, high | **Max:** เขียนเมื่องานต้องตัดสินใจ design / ≥5 ไฟล์ / เงิน-auth-concurrency / Sonnet แก้ไม่ผ่าน 2 รอบ · **Pro:** เฉพาะเมื่อคุณตอบ "ใช้ Opus" ในคำถาม escalation |
| `relay-coder-top` | `model: inherit` = โมเดลหลักของ session (Fable ถ้าเปิดด้วย Fable) | เฉพาะเมื่อคุณตอบ "ใช้ Fable" ในคำถาม escalation · วิเคราะห์ root cause ใหม่ก่อนแก้ |
| `relay-reviewer` | Opus, read-only | ตรวจ spec + คุณภาพ ให้ verdict Critical / Important / Minor · บน Pro คือที่นั่งเดียวของ Opus |
| `relay-diffcheck` | Sonnet, xhigh, read-only | ตรวจ bug fix: ตรง root cause ไหม, regression, มีที่อื่นอีกไหม |

### Tier: Max vs Pro

| | Max | Pro |
|---|---|---|
| Sonnet | เขียนโค้ด + diffcheck | เขียนโค้ด + diffcheck |
| Opus | ตรวจ **และ** เขียนเมื่องานยาก / รอบ 3 | **ตรวจอย่างเดียว** — เขียนเฉพาะเมื่อคุณสั่ง |
| escalate อัตโนมัติ (รอบ 3) | Opus เขียน | Sonnet ตัวใหม่เขียน + Opus ตรวจ |
| ถามคุณเมื่อยังไม่ผ่าน | Fable (`relay-coder-top`) / Opus / แก้ plan / หยุด | Opus / แก้ plan / หยุด |

เหตุผล: ที่นั่ง coder วิ่งได้ถึง 80 turn ส่วนที่นั่ง reviewer อ่าน diff รอบเดียว (cap 40 turn) — โมเดลเดียวกันแต่ค่าใช้จ่ายต่างกันหลายเท่า บน Pro quota หมดที่ตรง coder จึงให้ "Opus อ่าน Sonnet พิมพ์" ดู `research.md` §6

## ทำไมประหยัด

| กลไก | ผล |
|---|---|
| `omitClaudeMd: true` + `tools:` allowlist ในทุก seat | seat เริ่มที่ **~8K tokens** แทน 35–70K (ไม่โหลด CLAUDE.md, ไม่โหลด MCP catalog) |
| brief / report / diff ส่งเป็น**ไฟล์** ไม่ paste ข้อความ | context ของ planner ไม่บวมตลอด session |
| วน fix ได้ 2 รอบ → escalate อัตโนมัติ 1 รอบ → **ถามคุณ** ก่อนใช้ Fable/Opus → แล้วไปแก้ plan | ไม่ ping-pong ไม่เผา quota ลับหลัง |
| หลัง final review แก้เป็น wave เดียว | ไม่แยก fixer ต่อ finding |

เพราะ seat ไม่เห็น CLAUDE.md ของคุณ → **กฎของโปรเจกต์ต้องใส่ใน brief** — skill มี template brief พร้อม section `Project rules` ให้แล้ว

## คำถามที่พบบ่อย

**relay บังคับให้ planner เป็นโมเดลไหนไหม?** ไม่ — skill เปลี่ยนโมเดลของ session ไม่ได้ planner = โมเดลที่คุณเลือกด้วย `/model` ตอนเปิด session มีแค่ seat 4 ตัวที่ pin ไว้ (`model: sonnet` / `model: opus` ใน frontmatter — alias จะชี้ไปรุ่นใหม่สุดที่ plan ของคุณมี) ได้ผลดีสุดเมื่อ planner เป็น Opus หรือ Fable ถ้าเปิดด้วย Sonnet ก็ยังบังคับการแบ่งงานและรักษา context หลักให้เล็กอยู่

**ใช้แผน Pro ได้ไหม?** ได้ — ใส่ `relay-tier: pro` ใน `CLAUDE.md` แล้ว Opus จะนั่งแค่ reviewer ส่วน Sonnet เขียนทั้งหมด relay จะไม่สั่ง Opus เขียนโค้ดเองเลยจนกว่าคุณจะตอบ "ใช้ Opus" ในคำถาม escalation

**ทำไม coder หลักเป็น Sonnet xhigh ไม่ใช่ Opus?** งานตาม pattern เดิม (1–4 ไฟล์ spec ครบ) Sonnet 5 xhigh คะแนนใกล้เคียงและถูกกว่า 2.5× ต่อ token · Opus 5 ชนะชัดในงานยาว/ยาก (SWE-bench Pro ~63% vs ~79%) relay จึง escalate ไป `relay-coder-opus` เมื่อต้องตัดสินใจ design, ≥5 ไฟล์, โค้ดเงิน/auth/concurrency, หรือ Sonnet แก้ไม่ผ่าน 2 รอบ ดู `research.md`

**เปลี่ยนโมเดล/effort ของ seat ได้ไหม?** ได้ — แก้ frontmatter ใน `agents/*.md` แล้วเปิด Claude Code ใหม่ (ไฟล์ agent ที่แก้จะไม่ reload กลาง session)

**ไม่มี superpowers ใช้ได้ไหม?** ได้ — skill อธิบาย loop แบบ manual ไว้แล้ว (brief file → coder → diff file → reviewer)

**แก้ไฟล์ agent แล้วอยากเช็กว่าไม่พัง?** `python3 -I tests/check_plugin.py` — ตรวจ frontmatter ทุก seat (YAML, model/effort, tools, maxTurns), ชื่อ seat ที่อ้างถึงในเอกสาร และเวอร์ชันใน manifest

## License

MIT

---

<a id="english"></a>

# English

Relay is a Claude Code plugin: one skill (`/relay`) + six subagent seats. **The expensive main model never writes application code.** It plans, writes a brief, dispatches a Sonnet (xhigh) coder, and lets an Opus reviewer check the diff. Small fixes, bug fixes and full features all go through a seat.

Why it pays: Anthropic's own advisor benchmarks show Sonnet doing the work with Opus at decision points beats Sonnet alone by **+2.7 pt SWE-bench Multilingual at −11.9% cost per task**. Implementation is where the tokens go, so that is the seat that gets the cheaper model. Full numbers and sources: [`skills/relay/research.md`](skills/relay/research.md).

## Install

```
/plugin marketplace add chantanawat/claude-relay
/plugin install relay@claude-relay
```

Then restart Claude Code (agent files load at session start).

- Recommended: the official `superpowers` plugin — relay uses its `writing-plans`, `subagent-driven-development` and `systematic-debugging` skills when present, and falls back to a manual loop when not.
- Requires Claude Code **v2.1.271+** (for `omitClaudeMd`; older versions still work, the seats just cost more) and a plan with Opus access (Pro / Max / Team / API).
- Sonnet-only plan: change `model: opus` to `model: sonnet` in `agents/relay-reviewer.md` and `agents/relay-coder-opus.md`.
- **Tell relay your tier** — add a line that is exactly `relay-tier: pro` or exactly `relay-tier: max` to the project `CLAUDE.md`. Without it relay asks once per session; with no answer channel (headless) it assumes `pro`.

## Use

Just ask for code: "add a CSV export to the orders page", "fix the login redirect bug". The skill triggers itself on build / fix / debug requests; `/relay` forces it.

Three shapes, chosen automatically:

| Shape | When | What happens |
|---|---|---|
| **light** | ≤2 files, clear spec | brief → `relay-coder` → `relay-diffcheck` |
| **debug** | bug in existing code | planner diagnoses the root cause → coder fixes → diffcheck verifies the fix hits the cause and hunts siblings |
| **build** | new feature / ≥3 files | plan → task loop (coder → reviewer) → final Opus review · asks you one question first |

Every shape shares one **fix loop**: two rounds on the same seat → round 3 escalates automatically (max: Opus codes · pro: a fresh Sonnet seat codes, Opus reviews) → still failing, **relay stops and asks you**: Fable (max) / Opus (pro) / revise the plan / stop. It never spends the next model up on its own.

The six seats:

| Seat | Model | Role |
|---|---|---|
| `relay-coder-lite` | Sonnet, medium, ≤30 turns | light shape only, when the brief already states the exact change (copy / guard / config / version bump) |
| `relay-coder` | Sonnet, xhigh | writes the code, one task per dispatch (default) |
| `relay-coder-opus` | Opus, high | **max:** design judgment / ≥5 files / money-auth-concurrency / after two failed Sonnet rounds · **pro:** only after you pick "Opus" in the escalation question |
| `relay-coder-top` | `model: inherit` = the session's main model (Fable on a Fable session) | only after you pick "Fable" in the escalation question · re-derives the root cause before fixing |
| `relay-reviewer` | Opus, read-only | spec + quality review, Critical / Important / Minor verdicts · on pro this is Opus's only seat |
| `relay-diffcheck` | Sonnet, xhigh, read-only | bug-fix check: root cause, regressions, same bug elsewhere |

### Tier: max vs pro

| | max | pro |
|---|---|---|
| Sonnet | codes + diff-checks | codes + diff-checks |
| Opus | reviews **and** codes on hard tasks / round 3 | **reviews only** — codes only when you say so |
| automatic escalation (round 3) | Opus codes | fresh Sonnet seat codes, Opus reviews |
| the question when still failing | Fable (`relay-coder-top`) / Opus / revise plan / stop | Opus / revise plan / stop |

Why: a coder seat can run 80 turns of editing; a reviewer seat is one read-only pass over a diff (40-turn cap). Same model, several times the cost. On pro the quota dies in the coder seat, so Opus reads and Sonnet types. See `research.md` §6.

## What makes it cheap

| Lever | Effect |
|---|---|
| `omitClaudeMd: true` + `tools:` allowlist on every seat | a fresh seat starts at **~8K tokens** instead of 35–70K (no CLAUDE.md, no MCP catalog) |
| briefs, reports, diffs travel as **files**, never pasted text | the planner's context stays small all session |
| fix loop: 2 rounds → one automatic escalation → **asks you** before spending Fable/Opus → then fix the plan | no ping-pong, no quota burned behind your back |
| one fix wave after the final review | no fixer-per-finding |

Because the seats never see your CLAUDE.md, **put the project rules in the brief** — the skill has a brief template with a `Project rules` section.

## FAQ

**Does relay force a specific planner model?** No. A skill cannot change the session model. The planner is whatever `/model` you opened the session with; only the four seats are pinned (`model: sonnet` / `model: opus` in their frontmatter — aliases that resolve to the newest model your plan has). Best results with Opus or Fable as the planner; on Sonnet it still enforces the split and keeps your main context clean.

**Does it work on Pro?** Yes — set `relay-tier: pro` in `CLAUDE.md`. Opus then holds only the reviewer seat and Sonnet writes everything; relay never dispatches an Opus coder until you answer "Opus" in the escalation question.

**Why Sonnet xhigh and not Opus as the default coder?** For pattern-following work (1–4 files, complete spec) Sonnet 5 xhigh is close on the benchmarks and 2.5× cheaper per token. Opus 5 wins clearly on long, hard tasks (SWE-bench Pro ~63% vs ~79%), so relay escalates to `relay-coder-opus` for design judgment, ≥5 integrated files, money/auth/concurrency code, and after two failed Sonnet rounds. See `research.md`.

**Can I change a seat's model or effort?** Yes — edit the frontmatter in `agents/*.md`, then restart Claude Code (edited agent files do not reload mid-session).

**Does it work without superpowers?** Yes. The skill describes the manual loop (brief file → coder → diff file → reviewer).

**Edited an agent file and want to know it still loads?** `python3 -I tests/check_plugin.py` checks every seat's frontmatter (YAML, model/effort, tools, maxTurns), every seat name referenced in the docs, and the manifest versions.

## License

MIT
