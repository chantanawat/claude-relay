# Why relay is shaped this way — research notes (September 2026)

Reference for the seat roster in `SKILL.md`. Numbers are dated; re-verify before quoting them elsewhere. §6 added October 2026 (v1.1.0).

## สรุปสั้น (ไทย)
- Effort คือ "คิดลึกแค่ไหน" ภายในเพดานของโมเดล ไม่ใช่การเปลี่ยนโมเดล · Opus 5 default = `high`
- Ultracode ไม่ใช่ effort ระดับที่ 6 — คือ `xhigh` + ให้ Claude สั่ง multi-agent workflow เองทุกงาน กิน quota หนัก
- ตัวแรงวางแผน/ตรวจ ตัวถูกลงมือ = ถูกกว่าและดีกว่า (ตัวเลข official ของ Anthropic เอง)
- Sonnet 5 xhigh เป็น coder หลักคุ้มจริงสำหรับงานตาม pattern · Opus 5 ชนะชัดในงานยาว/ยาก และอาจถูกกว่าเมื่อ Sonnet ต้องวน fix หลายรอบ
- แผน Pro: Opus นั่งแค่ตำแหน่ง reviewer (อ่านอย่างเดียว) ไม่พิมพ์โค้ด — ที่นั่ง coder คือจุดที่ quota หมด · แผน Max ใช้ roster เดิม · แก้ไม่ผ่าน 3 รอบ → ถามผู้ใช้ก่อนเสมอ (Fable บน Max / Opus บน Pro / แก้ plan) ดู §6

## 1. Effort levels (official)
`low · medium · high (default; same as omitting the parameter) · xhigh · max` — all five on Sonnet 5, Opus 5, Fable 5/5.1.
- Effort is a behavioral signal: thinking depth **and** tool-call appetite. Lower effort = fewer, terser tool calls.
- Sonnet 5: `medium` ≈ Sonnet 4.6 `high`; `high` ≈ Sonnet 4.6 `max`; `xhigh` is Anthropic's recommendation for the hardest coding/agentic work and "shows substantially more tool usage".
- Opus 5: API and Claude Code default `high`; thinking cannot be disabled at `xhigh`/`max`.
- `max` on most workloads adds cost for small gains and can overthink.

## 2. Ultracode and the advisor tool (official)
- **Ultracode** = a Claude Code *setting*: sends `xhigh` and lets Claude plan/run dynamic workflows (JS scripts orchestrating `agent()/pipeline()/parallel()`, ≤16 concurrent, ≤1000 agents/run, intermediate results stay in script variables). `/effort ultracode` = whole session; the word `ultracode` in a prompt = one task. The `Large workflow` warning (>25 agents / 1.5M tokens) is suppressed while ultracode is on. Community reports: 62 Opus subagents hit a 5-hour cap in 18 minutes; ~90 agents to review a small package.
- **Advisor tool** (`/advisor <model>`): the main model consults a stronger one at decision points; the advisor re-reads the whole transcript (uncached) and returns ~400–700 tokens. Pairing must be ≥ main (Sonnet 5 main accepts Fable / Opus 4.7+ / Sonnet 5; Fable 5.1 main accepts only Fable 5.1). Toggling the advisor keeps the prompt cache; switching `/model` does not.

## 3. Strong plans/reviews, cheap implements — the numbers
| Pairing | vs. baseline | Source |
|---|---|---|
| Sonnet + Opus advisor | **−11.9% cost/task, +2.7 pt SWE-bench Multilingual** vs Sonnet alone; also better on BrowseComp and Terminal-Bench 2.0 at lower cost | Anthropic, *The advisor strategy* |
| Haiku + Opus advisor | BrowseComp 41.2% vs 19.7% solo, −85% cost vs Sonnet solo | same |
| `opusplan` | Opus in plan mode, Sonnet for execution — Anthropic's built-in version of the split | Claude Code model-config docs |

Implementation is where the tokens go, so the cheap seat sits there; the reviewer must be at least as strong as the implementer.

## 4. Sonnet 5 xhigh vs Opus 5 high as the coder
| Benchmark | Sonnet 5 | Opus 5 | Note |
|---|---|---|---|
| SWE-bench Pro | 63.2% | 79.2% (third-party); Opus 4.8 69.2%, Fable 5 80.3% | Sonnet figure consistent across sources |
| SWE-bench Verified | 72.7–85.2% (sources disagree) | 96% (third-party) | **Anthropic did not publish a Verified score for Opus 5** (it reported Frontier-Bench and CursorBench 3.2) |
| Terminal-Bench 2.1 | 74.5% | 84.6% | Vals via benchlm |
| LiveCodeBench | 82.4% | 89.0% | Vals via benchlm |

- Anthropic's own wording: Sonnet 5 at higher effort "may match **Opus 4.8** on some tasks" — not Opus 5.
- Price: Sonnet $2/$10, Opus $5/$25 per MTok → Opus 2.5× per token. But `xhigh` on Sonnet costs "meaningfully more tokens than high", and Opus 5 is token-frugal per task (Anthropic: 26% fewer tokens than Opus 4.8 on legal work; ~1/7 the reasoning tokens on a trading benchmark). A Sonnet task that needs two fix rounds can cost more than one Opus pass.
- Subscription limits: one shared 5-hour/weekly window across models plus model-family limits; per-model weighting is not published. Anthropic made Opus 5 the default on Max.

**Verdict:** Sonnet 5 xhigh as the default coder is right for pattern-following work (1–4 files, complete spec). Escalate to Opus 5 for design judgment, ≥5 integrated files, money/auth/concurrency paths, and after two failed Sonnet fix rounds. Measure with `/usage` attribution per subagent rather than trusting the price ratio.

## 5. Token traps that shaped the rules
- A dispatch prompt once reached 42k chars, 99% pasted history (superpowers SDD field notes) → files, not text; no history in a dispatch.
- One fixer per finding rebuilt context each time; a final-review fix wave cost more than all tasks combined → one fix wave, one scoped re-review.
- Parallel fan-out measured 2.6–5.9× a sequential pass and not faster (Systima) → never two implementers at once; small tasks stay cheap.
- Subagent baseline measured in a real workspace: 35–71K tokens for a one-line reply (system prompt + skill listing + CLAUDE.md + full MCP catalog). `omitClaudeMd: true` + a `tools:` allowlist brought a fresh seat to **~8K**. Edited agent files do not reload mid-session; new files do.

## 6. Subscription tiers — why Opus reads but does not type on Pro (October 2026)
- Claude subscriptions share one 5-hour / weekly usage window across models; Max is sold as **5× or 20× the Pro usage**. Anthropic does not publish the per-model weighting, but Opus costs 2.5× Sonnet per token on the API and the same ratio is the safe assumption for the window.
- A coder seat is the expensive shape of a dispatch: up to 80 turns of Read/Edit/Bash, every turn re-sending the growing context. A reviewer seat is one read-only pass over a diff file with a hard turn cap (40). The same Opus model costs several times more in the coder seat than in the reviewer seat — and the advisor numbers in §3 say the review is where the strong model pays for itself.
- Hence §0 of `SKILL.md`: on `pro` Opus holds only the reviewer seat; the automatic escalation after two failed Sonnet rounds is a **fresh Sonnet seat checked by Opus**, and an Opus *coder* round is a question to the user, never a default. On `max` the roster of v1.0 stays (Opus coder on judgment-heavy tasks and as automatic round 3).
- The question after round 3 (`SKILL.md` §6) exists because every further round costs more than the three before it: the context is bigger, and a third failure usually means the diagnosis or the plan is wrong rather than the typing. The user chooses between the next model up (Fable on max, Opus on pro) and fixing the plan.
- `relay-coder-top` uses `model: inherit` (documented sub-agent frontmatter value) so it runs on whatever the session runs on — Fable on a Fable session. The `Agent` tool on recent builds also accepts `model: "fable"` as a per-call override; use that instead if your build lists it and your planner is not Fable. The tier itself cannot be detected from inside a session, which is why it is a `CLAUDE.md` line or a one-time question.
- `relay-coder-lite` (Sonnet, medium, 30 turns) exists for the light shape only: when the brief already contains the exact change, rule 5 ("turn count beats token price") no longer applies — there is nothing to figure out, so the medium effort is enough and the turn cap keeps a confused seat from wandering.

## Sources
- platform.claude.com/docs/en/build-with-claude/effort · …/prompt-engineering/prompting-claude-sonnet-5
- code.claude.com/docs/en/workflows · …/advisor · …/model-config · …/sub-agents · …/costs
- claude.com/blog/the-advisor-strategy · anthropic.com/news/claude-opus-5 · anthropic.com/news/claude-sonnet-5
- benchlm.ai/compare/claude-opus-5-vs-claude-sonnet-5 (third-party aggregate) · systima.ai/blog/subagent-tax
