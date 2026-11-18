# Relay — วางแผนด้วยโมเดลหลัก · เขียนโค้ดด้วย Sonnet · ตรวจด้วย Opus

🇹🇭 ภาษาไทยอยู่ด้านบน · 🇬🇧 [English below ↓](#english)

Plugin สำหรับ Claude Code: skill เดียว (`/relay`) + subagent 7 ที่นั่ง (seat) · เวอร์ชันปัจจุบัน **1.2.0** ([มีอะไรใหม่](#มีอะไรใหม่))
**โมเดลแพงที่คุณเปิด session อยู่ (Opus / Fable) จะไม่เขียนโค้ดแอปเองเลย** — มันวางแผน เขียน brief แล้วส่งให้ Sonnet (xhigh) พิมพ์โค้ด และให้ Opus ตรวจ diff แบบ read-only ไม่ว่างานเล็กหรือใหญ่

ทำไมคุ้ม: benchmark ของ Anthropic เอง — Sonnet ทำงานโดยมี Opus ช่วยตัดสินใจ ชนะ Sonnet เดี่ยว **+2.7 pt บน SWE-bench Multilingual และถูกกว่า 11.9% ต่องาน** ส่วนที่กิน token มากที่สุดคือตอนพิมพ์โค้ด จึงเอาโมเดลถูกไปนั่งตรงนั้น ตัวเลขและแหล่งอ้างอิงทั้งหมดอยู่ใน [`skills/relay/research.md`](skills/relay/research.md) (มีสรุปไทย)

**ใหม่ใน 1.2.0 — ออกแบบครั้งเดียว ตรวจที่จุดชี้ขาด:** ถ้าคุณมีโมเดลที่แรงกว่า Opus (Fable) ให้มัน*ออกแบบครั้งเดียว*ใน session สั้น แล้วให้ Opus เป็นหัวหน้างานคุมลูปทั้งหมด โมเดลแรงสุดจะกลับมา*อ่านอย่างเดียว*แค่ 2 จุด: งานที่แก้ 3 รอบแล้วยังไม่ผ่าน และงานเสี่ยง (เงิน / auth / tenant / concurrency / migration) ก่อนส่งมอบ — ได้การตัดสินใจของตัวแรงสุดโดยไม่ต้องจ่ายราคาตัวแรงสุดทุกเทิน

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

ทุกแบบใช้ **fix loop เดียวกัน**: แก้ซ้ำได้ 2 รอบบน seat เดิม → รอบ 3 escalate อัตโนมัติ (Max: Opus เขียน · Pro: Sonnet ตัวใหม่เขียน + Opus ตรวจ) → ยังไม่ผ่าน: บน Max โมเดลแรงสุด**วินิจฉัยแบบอ่านอย่างเดียว 1 รอบ** (`relay-checkpoint`) ว่า plan ผิดหรือคนพิมพ์พลาด แล้ว Opus แก้ตามคำวินิจฉัยอีก 1 รอบ → ยังไม่ผ่านอีก **relay หยุดแล้วถามคุณ** (บน Pro ถามทันทีหลังรอบ 3) — ไม่ส่งโมเดลแพง*ลงมือเขียน*เองเด็ดขาด

seat ทั้ง 7:

| seat | โมเดล | หน้าที่ |
|---|---|---|
| `relay-coder-lite` | Sonnet, medium, ≤30 turns | light เท่านั้น เมื่อ brief บอกการแก้ที่แน่นอนแล้ว (copy / guard / config / bump version) |
| `relay-coder` | Sonnet, xhigh | เขียนโค้ด 1 task ต่อครั้ง (ค่าเริ่มต้น) |
| `relay-coder-opus` | Opus, high | **Max:** เขียนเมื่องานต้องตัดสินใจ design / ≥5 ไฟล์ / เงิน-auth-concurrency / Sonnet แก้ไม่ผ่าน 2 รอบ · **Pro:** เฉพาะเมื่อคุณตอบ "ใช้ Opus" ในคำถาม escalation |
| `relay-coder-top` | `model: inherit` — โมเดลแรงสุดที่คุณมี (session Opus จะสั่งด้วย `model: "fable"`) | เฉพาะเมื่อคุณตอบ "ให้ตัวแรงสุดแก้เอง" ในคำถาม escalation · วิเคราะห์ root cause ใหม่ก่อนแก้ |
| `relay-reviewer` | Opus, read-only | ตรวจ spec + คุณภาพ ให้ verdict Critical / Important / Minor · บน Pro คือที่นั่งเดียวของ Opus |
| `relay-diffcheck` | Sonnet, xhigh, read-only | ตรวจ bug fix: ตรง root cause ไหม, regression, มีที่อื่นอีกไหม |
| `relay-checkpoint` | โมเดลแรงสุดที่คุณมี, read-only, รอบเดียว ≤40 turns | **ใหม่ 1.2.0** — จุดชี้ขาด 2 จุด: `diagnose` (งานติดหลังรอบ 3) และ `acceptance` (ตรวจปิดงานเสี่ยงเทียบกับเจตนาของ design) · ไม่เขียนโค้ด ไม่คุมลูป |

### ออกแบบครั้งเดียว ตรวจที่จุดชี้ขาด (1.2.0)

"คุมงาน" มีสองส่วนที่ราคาต่างกันมาก: **ลูป** (เขียน brief, สั่งงาน, จด ledger, ตัดสินเรื่องทั่วไป) ใช้หลายสิบเทินบน context ที่โตขึ้นเรื่อยๆ แต่แทบไม่ต้องใช้วิจารณญาณ ส่วน**จุดชี้ขาด** (plan ผิดไหม, งานที่เสร็จยังตรงเจตนาของ design ไหม) อ่านครั้งเดียวจบ และเป็นจุดที่โมเดลแรงสุดคุ้มราคา

| บทบาท | โมเดล | เมื่อไหร่ | ลักษณะต้นทุน |
|---|---|---|---|
| **ผู้ออกแบบ** | ตัวแรงสุดที่คุณมี (Fable; ถ้าไม่มีก็ Opus) | ครั้งเดียวต่อ build ใน session สั้นที่เปิดใหม่ จบเมื่อคุณอนุมัติ plan | ≤ ~40 เทิน context เล็ก |
| **หัวหน้างาน** (planner ของ relay) | Opus | ทั้งลูป | ยาว แต่ราคาต่อ token ราวครึ่งเดียว |
| **ผู้ตรวจจุดชี้ขาด** | ตัวแรงสุด, `relay-checkpoint`, read-only | `diagnose` หลังรอบ 3 ไม่ผ่าน · `acceptance` หลัง final review ของงานเสี่ยง | อ่านรอบเดียวต่อครั้ง |

- plan ต้องมี `## Design intent` — เงื่อนไขไม่เกิน 10 ข้อที่งานเสร็จแล้วต้องยังเป็นจริง (ตรวจได้จาก diff) และทุก task ระบุ `checkpoint: yes — <เหตุผล>` หรือ `checkpoint: no`
- ออกแบบเสร็จ → เขียนไฟล์ handoff → เปิด **session Opus ใหม่** แล้ว `/relay resume <path>` (อย่าใช้ `/model` สลับกลาง session เพราะโมเดลใหม่ต้องอ่านประวัติทั้งหมดแบบไม่มี cache)
- `acceptance` รันเฉพาะ build ที่ plan ติดธง `checkpoint: yes` หรือแตะเงิน / auth / tenant / concurrency / migration — งานเล็ก งาน debug งาน bulk ไม่รัน
- ผล `Confirmed` = จบ · `built-wrong` = แก้ 1 wave + Opus ตรวจซ้ำ 1 ครั้ง · `design-defect` = หยุด ให้ผู้ออกแบบแก้ design ไม่ให้หัวหน้างานปะเอง
- ข้อจำกัด: acceptance 1 ครั้งต่อ build · diagnose 1 ครั้งต่อ task และ 2 ครั้งต่อ build · บน Pro ทั้งสองอย่างรันเมื่อคุณตอบตกลงเท่านั้น
- ยังเป็น**สมมติฐาน**: ยังไม่มีข้อมูลว่า acceptance จับสิ่งที่ Opus review พลาดได้บ่อยแค่ไหน ถ้า 5 ครั้งติดกันไม่เจอ Blocker เลย ให้ตัดออกหรือทำให้เงื่อนไขแคบลง

เหตุผลและตัวเลขอยู่ใน `research.md` §8

### Tier: Max vs Pro

| | Max | Pro |
|---|---|---|
| Sonnet | เขียนโค้ด + diffcheck | เขียนโค้ด + diffcheck |
| Opus | ตรวจ **และ** เขียนเมื่องานยาก / รอบ 3 | **ตรวจอย่างเดียว** — เขียนเฉพาะเมื่อคุณสั่ง |
| escalate อัตโนมัติ (รอบ 3) | Opus เขียน | Sonnet ตัวใหม่เขียน + Opus ตรวจ |
| หลังรอบ 3 ไม่ผ่าน | ตัวแรงสุดวินิจฉัยแบบอ่านอย่างเดียว (`relay-checkpoint`) → Opus แก้ตามนั้น 1 รอบ (อัตโนมัติ) | ถามคุณทันที |
| ถามคุณเมื่อยังไม่ผ่าน | ตัวแรงสุดแก้เอง (`relay-coder-top`) / แก้ plan / กลับไปแก้ design / หยุด | ตัวแรงสุดวินิจฉัยก่อน / Opus เขียน / แก้ plan / หยุด |
| ตรวจปิดงานเสี่ยง (`acceptance`) | อัตโนมัติ | เมื่อคุณตอบตกลง |

เหตุผล: ที่นั่ง coder วิ่งได้ถึง 80 turn ส่วนที่นั่ง reviewer อ่าน diff รอบเดียว (cap 40 turn) — โมเดลเดียวกันแต่ค่าใช้จ่ายต่างกันหลายเท่า บน Pro quota หมดที่ตรง coder จึงให้ "Opus อ่าน Sonnet พิมพ์" ดู `research.md` §6

**งานซ้ำๆ เยอะๆ ไม่ซับซ้อน = Sonnet ทุก tier** (rename, สลับ import, ใส่ key i18n, แก้ config ซ้ำหลาย service) — relay แบ่งเป็น batch 5–8 ไฟล์ต่อ dispatch + diffcheck ต่อ batch ไม่ส่ง Opus แม้บน Max เพราะ Opus คือที่นั่งสำหรับ "งานที่ต้องตัดสินใจ" ไม่ใช่ "งานเยอะ"

### Session ยาว: hand-off ไม่ใช่ลากต่อ

ทุกเทินส่ง context ทั้งก้อนซ้ำ ค่าใช้จ่ายของ session = ผลรวม context ต่อเทิน **ไม่ใช่** ขนาด context ตอนจบ — เทินเยอะก็กิน quota แม้หน้าต่างยังไม่เต็ม relay จึงให้ planner หยุดที่ขอบ task (ไม่ใช่กลาง fix loop) เมื่อถึง**อย่างใดอย่างหนึ่ง**:

| tier | เทินของ planner | context ที่ใช้ |
|---|---|---|
| Max | ~90 | ≥50% |
| Pro | ~50 | ≥40% |

แล้วเขียนไฟล์ handoff (tier, shape, plan, ledger งานที่เสร็จ/ค้าง, finding ที่เปิดอยู่, ruling ทุกข้อ, `Next step`) → เปิด session ใหม่ → `/relay resume <path>` session ใหม่อ่านแค่ไฟล์นั้น ไม่อ่าน report เก่า (เทินของ seat แยกต่างหาก ถูก cap ด้วย `maxTurns` ในไฟล์ agent อยู่แล้ว) ดู `research.md` §7

## ทำไมประหยัด

| กลไก | ผล |
|---|---|
| `omitClaudeMd: true` + `tools:` allowlist ในทุก seat | seat เริ่มที่ **~8K tokens** แทน 35–70K (ไม่โหลด CLAUDE.md, ไม่โหลด MCP catalog) |
| brief / report / diff ส่งเป็น**ไฟล์** ไม่ paste ข้อความ | context ของ planner ไม่บวมตลอด session |
| วน fix ได้ 2 รอบ → escalate อัตโนมัติ 1 รอบ → วินิจฉัยแบบอ่านอย่างเดียว 1 รอบ (Max) → **ถามคุณ** ก่อนให้โมเดลแพงลงมือเขียน | ไม่ ping-pong ไม่เผา quota ลับหลัง |
| หลัง final review แก้เป็น wave เดียว | ไม่แยก fixer ต่อ finding |
| โมเดลแรงสุด "อ่าน ไม่วนลูป" — ออกแบบครั้งเดียว + ตรวจจุดชี้ขาด | ไม่จ่ายราคา 2 เท่าต่อ token คูณด้วยจำนวนเทินของลูป (การวัดจริง 1 งาน: planner ตัวแรงสุดกิน 57% ของทั้งงาน) |

เพราะ seat ไม่เห็น CLAUDE.md ของคุณ → **กฎของโปรเจกต์ต้องใส่ใน brief** — skill มี template brief พร้อม section `Project rules` ให้แล้ว

## คำถามที่พบบ่อย

**relay บังคับให้ planner เป็นโมเดลไหนไหม?** ไม่ — skill เปลี่ยนโมเดลของ session ไม่ได้ planner = โมเดลที่คุณเลือกด้วย `/model` ตอนเปิด session มีแค่ seat 4 ตัวที่ pin ไว้ (`model: sonnet` / `model: opus` ใน frontmatter — alias จะชี้ไปรุ่นใหม่สุดที่ plan ของคุณมี) ได้ผลดีสุดเมื่อ planner เป็น Opus หรือ Fable ถ้าเปิดด้วย Sonnet ก็ยังบังคับการแบ่งงานและรักษา context หลักให้เล็กอยู่

**ต้องมี Fable ไหม?** ไม่ต้อง — ถ้า Opus คือตัวแรงสุดที่คุณมี ผู้ออกแบบกับหัวหน้างานคือโมเดลเดียวกัน ไม่ต้อง handoff ส่วน `relay-checkpoint` จะรันบน Opus: ยังมีประโยชน์เพราะเป็นที่นั่งที่เริ่มจาก context ว่าง อ่านแค่ design กับ diff จึงเห็นสิ่งที่ planner ซึ่งทำงานมา 90 เทินมองข้ามไปแล้ว

**ทำไมไม่ให้โมเดลแรงสุดคุมงานทั้งหมดไปเลย?** เพราะต้นทุนของ session = ผลรวม context ทุกเทิน × ราคา และลูปของ planner คือส่วนที่เทินเยอะที่สุด การวัดจริงใน workspace หนึ่ง: planner ตัวแรงสุดกิน 57% ของค่าใช้จ่ายทั้งงาน ในขณะที่อัตราผ่านรีวิวรอบแรกไม่ต่างจากตอนใช้ Opus คุม (48% เทียบ 44% — ไม่ใช่การทดลองควบคุม) ดู `research.md` §8

**ใช้แผน Pro ได้ไหม?** ได้ — ใส่ `relay-tier: pro` ใน `CLAUDE.md` แล้ว Opus จะนั่งแค่ reviewer ส่วน Sonnet เขียนทั้งหมด relay จะไม่สั่ง Opus เขียนโค้ดเองเลยจนกว่าคุณจะตอบ "ใช้ Opus" ในคำถาม escalation

**ทำไม coder หลักเป็น Sonnet xhigh ไม่ใช่ Opus?** งานตาม pattern เดิม (1–4 ไฟล์ spec ครบ) Sonnet 5 xhigh คะแนนใกล้เคียงและถูกกว่า 2.5× ต่อ token · Opus 5 ชนะชัดในงานยาว/ยาก (SWE-bench Pro ~63% vs ~79%) relay จึง escalate ไป `relay-coder-opus` เมื่อต้องตัดสินใจ design, ≥5 ไฟล์, โค้ดเงิน/auth/concurrency, หรือ Sonnet แก้ไม่ผ่าน 2 รอบ ดู `research.md`

**เปลี่ยนโมเดล/effort ของ seat ได้ไหม?** ได้ — แก้ frontmatter ใน `agents/*.md` แล้วเปิด Claude Code ใหม่ (ไฟล์ agent ที่แก้จะไม่ reload กลาง session)

**ไม่มี superpowers ใช้ได้ไหม?** ได้ — skill อธิบาย loop แบบ manual ไว้แล้ว (brief file → coder → diff file → reviewer)

**แก้ไฟล์ agent แล้วอยากเช็กว่าไม่พัง?** `python3 -I tests/check_plugin.py` — ตรวจ frontmatter ทุก seat (YAML, model/effort, tools, maxTurns), ชื่อ seat ที่อ้างถึงในเอกสาร และเวอร์ชันใน manifest

## มีอะไรใหม่

| เวอร์ชัน | สรุป |
|---|---|
| **1.2.0** | ออกแบบครั้งเดียว ตรวจที่จุดชี้ขาด: seat ใหม่ `relay-checkpoint` (ตัวแรงสุด อ่านอย่างเดียว) · `diagnose` อัตโนมัติหลังรอบ 3 บน Max · `acceptance` สำหรับงานเสี่ยง · plan มี `## Design intent` · session ตัวแรงสุดออกแบบแล้ว handoff ให้ Opus คุมลูป |
| 1.1.0 | แยก tier Max / Pro · seat `relay-coder-lite` และ `relay-coder-top` · ถามก่อนใช้ Fable/Opus หลังแก้ไม่ผ่าน 3 รอบ · งาน bulk อยู่ที่ Sonnet ทุก tier · handoff เมื่อ session ยาว |
| 1.0.0 | รุ่นแรก: planner ไม่เขียนโค้ด · Sonnet เขียน · Opus ตรวจ |

รายละเอียดทุกเวอร์ชัน: [`CHANGELOG.md`](CHANGELOG.md) · อัปเดต plugin: `/plugin marketplace update claude-relay` แล้วเปิด Claude Code ใหม่

## License

MIT

---

<a id="english"></a>

# English

Relay is a Claude Code plugin: one skill (`/relay`) + seven subagent seats. Current version **1.2.0** ([what's new](#whats-new)). **The expensive main model never writes application code.** It plans, writes a brief, dispatches a Sonnet (xhigh) coder, and lets an Opus reviewer check the diff. Small fixes, bug fixes and full features all go through a seat.

Why it pays: Anthropic's own advisor benchmarks show Sonnet doing the work with Opus at decision points beats Sonnet alone by **+2.7 pt SWE-bench Multilingual at −11.9% cost per task**. Implementation is where the tokens go, so that is the seat that gets the cheaper model. Full numbers and sources: [`skills/relay/research.md`](skills/relay/research.md).

**New in 1.2.0 — design once, check at decision points:** if you have a model above Opus (Fable), it *designs once* in a short session and an Opus foreman runs the whole loop. The strongest model comes back *read-only* at just two points: a task still failing after three rounds, and a risk-path build (money / auth / tenant / concurrency / migration) before hand-over. You get the top model's judgment without paying the top model's price on every turn.

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

Every shape shares one **fix loop**: two rounds on the same seat → round 3 escalates automatically (max: Opus codes · pro: a fresh Sonnet seat codes, Opus reviews) → still failing: on max the strongest model **diagnoses read-only, once** (`relay-checkpoint`) — is the plan wrong or the typing — and Opus runs one round to that ruling → still failing, **relay stops and asks you** (on pro it asks right after round 3). It never puts an expensive model *in a coder seat* on its own.

The seven seats:

| Seat | Model | Role |
|---|---|---|
| `relay-coder-lite` | Sonnet, medium, ≤30 turns | light shape only, when the brief already states the exact change (copy / guard / config / version bump) |
| `relay-coder` | Sonnet, xhigh | writes the code, one task per dispatch (default) |
| `relay-coder-opus` | Opus, high | **max:** design judgment / ≥5 files / money-auth-concurrency / after two failed Sonnet rounds · **pro:** only after you pick "Opus" in the escalation question |
| `relay-coder-top` | `model: inherit` — the strongest model you have (an Opus session dispatches it with `model: "fable"`) | only after you pick "strongest model codes the fix" in the escalation question · re-derives the root cause before fixing |
| `relay-reviewer` | Opus, read-only | spec + quality review, Critical / Important / Minor verdicts · on pro this is Opus's only seat |
| `relay-diffcheck` | Sonnet, xhigh, read-only | bug-fix check: root cause, regressions, same bug elsewhere |
| `relay-checkpoint` | the strongest model you have, read-only, one pass, ≤40 turns | **new in 1.2.0** — two decision points: `diagnose` (stuck after round 3) and `acceptance` (a finished risk-path build checked against the design's intent) · never codes, never runs the loop |

### Design once, check at decision points (1.2.0)

"Supervising" is two jobs with very different prices. **The loop** (write a brief, dispatch, keep the ledger, make routine rulings) is dozens of turns on a growing context and needs little judgment per turn. **The decision points** (is the plan wrong, does the finished work still keep the design's intent) are one read each — and that is where the strongest model earns its price.

| Role | Model | When | Shape of the cost |
|---|---|---|---|
| **Designer** | the strongest model you have (Fable; Opus if that is your top) | once per build, in a short fresh session; ends when you approve the plan | ≤ ~40 turns, small context |
| **Foreman** (the relay planner) | Opus | the whole loop | long, at about half the price per token |
| **Checkpoint** | the strongest model, `relay-checkpoint`, read-only | `diagnose` after a failed round 3 · `acceptance` after the final review of a risk-path build | one pass each |

- The plan carries `## Design intent` — up to 10 invariants the finished work must keep, each checkable from a diff — and every task says `checkpoint: yes — <reason>` or `checkpoint: no`.
- Design done → handoff file → open a **new Opus session** and run `/relay resume <path>`. Do not switch with `/model` mid-session: the new model re-reads the whole history uncached.
- `acceptance` runs only for a build whose plan flags `checkpoint: yes` or that touches money / auth / tenant / concurrency / migration. Light, debug and bulk work never get one.
- `Confirmed` = done · `built-wrong` = one fix wave + one Opus re-review · `design-defect` = stop; the designer amends the design, the foreman does not patch around it.
- Caps: one acceptance per build · one diagnosis per task, two per build · on pro both run only when you say yes.
- Still a **hypothesis**: nothing yet shows how often acceptance catches what the Opus review missed. Five passes in a row with no Blocker → drop it or narrow the trigger.

Reasoning and numbers: `research.md` §8.

### Tier: max vs pro

| | max | pro |
|---|---|---|
| Sonnet | codes + diff-checks | codes + diff-checks |
| Opus | reviews **and** codes on hard tasks / round 3 | **reviews only** — codes only when you say so |
| automatic escalation (round 3) | Opus codes | fresh Sonnet seat codes, Opus reviews |
| after a failed round 3 | strongest model diagnoses read-only (`relay-checkpoint`) → Opus runs one round to its ruling (automatic) | asks you right away |
| the question when still failing | strongest model codes (`relay-coder-top`) / revise plan / back to the design / stop | strongest model diagnoses first / Opus codes / revise plan / stop |
| acceptance check on risk-path builds | automatic | when you say yes |

Why: a coder seat can run 80 turns of editing; a reviewer seat is one read-only pass over a diff (40-turn cap). Same model, several times the cost. On pro the quota dies in the coder seat, so Opus reads and Sonnet types. See `research.md` §6.

**Bulk, repetitive, simple work is Sonnet on every tier** (renames, import swaps, i18n keys, the same config value across services): relay batches it 5–8 files per dispatch with one diff-check per batch and never sends it to Opus, even on max. Opus is the judgment seat, not the volume seat.

### Long sessions: hand off, don't grow

Every turn re-sends the whole context, so a session costs the **sum of context over turns**, not the size of the window at the end: many turns drain quota even while the window looks half empty. Relay has the planner stop at a task boundary (never mid fix-loop) when **either** threshold is hit:

| tier | planner turns | context used |
|---|---|---|
| max | ~90 | ≥50% |
| pro | ~50 | ≥40% |

It writes a handoff file (tier, shape, plan, done/open ledger, open findings, every ruling, `Next step`) → you open a new session → `/relay resume <path>`. The new session reads only that file, not the old reports. (Seat turns are separate and already capped by `maxTurns` in the agent files.) See `research.md` §7.

## What makes it cheap

| Lever | Effect |
|---|---|
| `omitClaudeMd: true` + `tools:` allowlist on every seat | a fresh seat starts at **~8K tokens** instead of 35–70K (no CLAUDE.md, no MCP catalog) |
| briefs, reports, diffs travel as **files**, never pasted text | the planner's context stays small all session |
| fix loop: 2 rounds → one automatic escalation → one read-only diagnosis (max) → **asks you** before an expensive model types | no ping-pong, no quota burned behind your back |
| one fix wave after the final review | no fixer-per-finding |
| the strongest model reads, never loops — design once + decision-point checks | no 2×-per-token price multiplied by the loop's turn count (one measured run: the top-model planner was 57% of the bill) |

Because the seats never see your CLAUDE.md, **put the project rules in the brief** — the skill has a brief template with a `Project rules` section.

## FAQ

**Does relay force a specific planner model?** No. A skill cannot change the session model. The planner is whatever `/model` you opened the session with; only the four seats are pinned (`model: sonnet` / `model: opus` in their frontmatter — aliases that resolve to the newest model your plan has). Best results with Opus or Fable as the planner; on Sonnet it still enforces the split and keeps your main context clean.

**Do I need Fable?** No. If Opus is the strongest model you have, designer and foreman are the same model and there is no hand-off. `relay-checkpoint` then runs on Opus — still useful, because it is a cold seat that reads only the design and the diff, so it sees what a planner 90 turns into the work no longer does.

**Why not let the strongest model supervise everything?** Because a session costs the sum of context over turns × price, and the planner loop is where the turns are. One workspace's measurement: the top-model planner took 57% of a whole run, while first-round review approval was no better than with an Opus planner (48% vs 44% — not a controlled experiment). See `research.md` §8.

**Does it work on Pro?** Yes — set `relay-tier: pro` in `CLAUDE.md`. Opus then holds only the reviewer seat and Sonnet writes everything; relay never dispatches an Opus coder until you answer "Opus" in the escalation question.

**Why Sonnet xhigh and not Opus as the default coder?** For pattern-following work (1–4 files, complete spec) Sonnet 5 xhigh is close on the benchmarks and 2.5× cheaper per token. Opus 5 wins clearly on long, hard tasks (SWE-bench Pro ~63% vs ~79%), so relay escalates to `relay-coder-opus` for design judgment, ≥5 integrated files, money/auth/concurrency code, and after two failed Sonnet rounds. See `research.md`.

**Can I change a seat's model or effort?** Yes — edit the frontmatter in `agents/*.md`, then restart Claude Code (edited agent files do not reload mid-session).

**Does it work without superpowers?** Yes. The skill describes the manual loop (brief file → coder → diff file → reviewer).

**Edited an agent file and want to know it still loads?** `python3 -I tests/check_plugin.py` checks every seat's frontmatter (YAML, model/effort, tools, maxTurns), every seat name referenced in the docs, and the manifest versions.

<a id="whats-new"></a>

## What's new

| Version | Summary |
|---|---|
| **1.2.0** | Design once, check at decision points: new `relay-checkpoint` seat (strongest model, read-only) · automatic `diagnose` after round 3 on max · `acceptance` for risk-path builds · plans carry `## Design intent` · a top-model session designs, then hands the loop to Opus |
| 1.1.0 | max / pro tiers · `relay-coder-lite` and `relay-coder-top` seats · asks before spending Fable/Opus after three failed rounds · bulk work stays on Sonnet on every tier · long-session hand-off |
| 1.0.0 | first release: the planner never codes · Sonnet writes · Opus reviews |

Full notes: [`CHANGELOG.md`](CHANGELOG.md) · update the plugin with `/plugin marketplace update claude-relay`, then restart Claude Code.

## License

MIT
