# Changelog

🇹🇭 สรุปไทยอยู่ใต้หัวข้อของแต่ละเวอร์ชัน · 🇬🇧 English notes follow each Thai summary.

## 1.2.0 — 2026-11-19 · Design once, check at decision points

**สรุป (ไทย):** ถ้าคุณมีโมเดลที่แรงกว่า Opus (Fable) เวอร์ชันนี้ตอบคำถามว่า "ควรให้มันทำอะไร" — คำตอบคือ *ออกแบบครั้งเดียว แล้วกลับมาอ่านอย่างเดียวที่จุดชี้ขาด* ไม่ใช่นั่งคุมงานทั้งลูป

- **ทำไมเปลี่ยน:** การวัดจริงในงานหนึ่ง planner ที่เป็นโมเดลแรงสุดกิน 57% ของค่าใช้จ่ายทั้งงาน (context โตจาก 68K เป็น 346K ใน 157 เทิน) แต่อัตราผ่านรีวิวรอบแรกไม่ได้ดีกว่าตอนให้ Opus คุม (48% เทียบ 44% จาก 361 dispatch — ไม่ใช่การทดลองควบคุม) ลูปคือที่ที่ token ไป ส่วนวิจารณญาณของตัวแรงสุดมีค่าที่จุดตัดสินใจไม่กี่จุด
- **seat ใหม่ `relay-checkpoint`:** โมเดลแรงสุดที่คุณมี อ่านอย่างเดียว รอบเดียว ≤40 turns มี 2 โหมด
  - `diagnose` — งานที่แก้ 3 รอบแล้วไม่ผ่าน: ชี้ว่า `plan-wrong` (plan/brief ผิด พร้อมข้อความแก้) · `execution` (plan ถูก คนพิมพ์พลาด พร้อมรายการแก้) หรือ `stop`
  - `acceptance` — build ที่เสี่ยง (เงิน / auth / tenant / concurrency / migration หรือ plan ติดธง `checkpoint: yes`) หลัง final review ผ่านแล้ว: ตรวจงานทั้งก้อนเทียบกับ `## Design intent` ของ plan ซึ่งเป็นสิ่งที่รีวิวราย task มองไม่เห็น
- **fix loop เปลี่ยน:** บน Max หลังรอบ 3 ไม่ผ่าน จะ `diagnose` อัตโนมัติ 1 ครั้ง แล้ว Opus แก้ตามคำวินิจฉัย 1 รอบ (รอบ 4) ก่อนจะหยุดถามคุณ · บน Pro ยังถามทันทีหลังรอบ 3 และมีตัวเลือก "วินิจฉัยก่อน" เพิ่มมา · relay ยังคง**ไม่ส่งโมเดลแพงลงมือเขียนโค้ดเอง**โดยไม่ถาม
- **plan เปลี่ยน:** ต้องมี `## Design intent` (ไม่เกิน 10 ข้อ ตรวจได้จาก diff) และทุก task ระบุ `checkpoint: yes/no`
- **session ของตัวแรงสุด + งาน build:** ออกแบบ → ให้คุณอนุมัติ → เขียน handoff → หยุด ให้เปิด session Opus ใหม่แล้ว `/relay resume` (ไม่ใช้ `/model` สลับกลาง session เพราะต้องอ่านประวัติใหม่ทั้งหมดแบบไม่มี cache)
- **ข้อจำกัดต้นทุน:** acceptance 1 ครั้งต่อ build · diagnose 1 ครั้งต่อ task, 2 ครั้งต่อ build · บน Pro ทั้งสองรันเมื่อคุณตอบตกลง
- **สิ่งที่ยังไม่พิสูจน์:** ยังไม่มีข้อมูลว่า acceptance จับสิ่งที่ Opus review พลาดได้บ่อยแค่ไหน skill จึงบอกให้นับผล — 5 ครั้งติดกันไม่เจอ Blocker ให้ตัดออก
- **ไม่มี Fable ก็ใช้ได้:** `relay-checkpoint` รันบน Opus แทน (ที่นั่ง context ว่างที่อ่านแค่ design กับ diff)

**อัปเดต:** `/plugin marketplace update claude-relay` แล้วเปิด Claude Code ใหม่ (ไฟล์ agent โหลดตอนเริ่ม session) · ไม่มีอะไรต้องแก้ใน `CLAUDE.md` ของคุณ · plan เก่าที่ไม่มี `## Design intent` ยังใช้ได้ — หัวหน้างานจะเขียนให้ก่อนเริ่ม task แรก

### Added
- `agents/relay-checkpoint.md` — read-only checkpoint seat (`model: inherit`, dispatched on the strongest model available via the Agent tool's `model` override), modes `acceptance` and `diagnose`.
- `SKILL.md` §9 *Design once, check at decision points*: the designer / foreman / checkpoint roles, the `## Design intent` contract, when acceptance runs, the `CHECK_FILE` format, verdict handling, caps, and how to measure whether the pass pays for itself.
- `research.md` §8 — the evidence: price ratio, a measured run where the top-model planner was 57% of the bill, a 361-dispatch ledger showing no first-round-approval gain from a stronger foreman, and the reasoning for a cold subagent over `/advisor`.
- Token rule 12: the strongest model reads, never loops.
- `CHANGELOG.md` (this file); `tests/check_plugin.py` now requires a changelog entry for the manifest version.

### Changed
- **Fix loop (§6), tier `max`:** after a failed round 3, `relay-checkpoint` diagnoses automatically (read-only, one pass) and round 4 follows its ruling; the question to the user moves to after round 4 and offers *strongest model codes · revise the plan · back to the design · stop*.
- **Fix loop, tier `pro`:** the question after round 3 gains a first option — *strongest model diagnoses first, read-only*.
- **Shapes (§1):** a session on a model above Opus that would start a build now designs and hands off instead of running the loop.
- **Build (§5):** the plan opens with `## Design intent` and marks each task `checkpoint: yes/no`; an acceptance checkpoint follows the final review when §9 calls for one.
- `relay-coder-top` is dispatched with `model: "fable"` from an Opus session (it used to assume the session itself was the top model).
- Headless runs on `max` still run the diagnosis and round 4 (both bounded); nothing else is chosen on the user's behalf.

### Unchanged
- The planner never edits application code. Seats, tiers, the hand-off thresholds and the brief format are as in 1.1.0.

## 1.1.0 — 2026-10-31 · Tiers

**สรุป (ไทย):** แยก tier Max / Pro — บน Pro ให้ Opus อ่านอย่างเดียว Sonnet เป็นคนพิมพ์ · เพิ่ม seat `relay-coder-lite` (งาน light) และ `relay-coder-top` (ตัวแรงสุด เฉพาะเมื่อคุณเลือก) · แก้ไม่ผ่าน 3 รอบแล้วหยุดถามคุณก่อนใช้ Fable/Opus · งานซ้ำจำนวนมากอยู่ที่ Sonnet ทุก tier · planner ส่งต่อ session เมื่อถึง ~90 เทิน / 50% (Max) หรือ ~50 เทิน / 40% (Pro)

- Tier resolution from a `relay-tier: max|pro` line in `CLAUDE.md`, or one question per session; headless assumes `pro`.
- New seats `relay-coder-lite` (Sonnet, medium) and `relay-coder-top` (`model: inherit`).
- Fix loop: two rounds, one automatic escalation, then ask the user.
- Bulk same-shape work is batched on Sonnet on every tier; `/relay resume <handoff-file>`.
- `tests/check_plugin.py`.

## 1.0.0 — 2026-09-15 · First release

**สรุป (ไทย):** รุ่นแรก — โมเดลหลักวางแผนและเขียน brief ไม่เขียนโค้ดแอปเอง · Sonnet xhigh เขียน · Opus ตรวจแบบ read-only · 3 รูปแบบ light / debug / build

- Planner never writes application code; `relay-coder` (Sonnet xhigh), `relay-coder-opus`, `relay-reviewer` (Opus, read-only), `relay-diffcheck`.
