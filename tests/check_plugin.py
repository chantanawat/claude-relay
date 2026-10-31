#!/usr/bin/env python3
"""Static checks for the relay plugin: agent frontmatter, seat references, manifests.

Run from the repo root:  python3 -I tests/check_plugin.py
Exit code 0 = all checks passed; 1 = at least one failure (listed on stderr).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
SKILL = ROOT / "skills" / "relay" / "SKILL.md"
RESEARCH = ROOT / "skills" / "relay" / "research.md"
README = ROOT / "README.md"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKET = ROOT / ".claude-plugin" / "marketplace.json"

MODELS = {"sonnet", "opus", "haiku", "inherit"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
TOOLS = {"Read", "Edit", "Write", "Grep", "Glob", "Bash"}
WRITE_TOOLS = {"Edit", "Write"}
REQUIRED_KEYS = {"name", "description", "model", "effort", "maxTurns", "tools", "omitClaudeMd"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def frontmatter(path: Path) -> dict:
    """Parse the flat YAML frontmatter the agent files use (no external deps)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        fail(f"{path.name}: missing frontmatter")
        return {}
    data: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith(" "):
            continue  # nested keys (experimental.cacheTtl) are not validated here
        key, _, value = line.partition(":")
        value = value.strip()
        # An unquoted scalar containing ': ' is a YAML mapping error - Claude Code then skips the agent file.
        if ": " in value and not (value.startswith(('"', "'")) and value.endswith(('"', "'"))):
            fail(f"{path.name}: value of '{key.strip()}' contains ': ' - quote it or remove the colon")
        data[key.strip()] = value
    try:  # strict parse when PyYAML is installed; the flat parser above is the no-dependency fallback
        import yaml  # type: ignore

        yaml.safe_load(m.group(1))
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        fail(f"{path.name}: frontmatter is not valid YAML ({exc.__class__.__name__})")
    return data


def check_agent(path: Path) -> str | None:
    fm = frontmatter(path)
    if not fm:
        return None
    name = fm.get("name")
    if name != path.stem:
        fail(f"{path.name}: name '{name}' != filename")
    missing = REQUIRED_KEYS - fm.keys()
    if missing:
        fail(f"{path.name}: missing frontmatter keys {sorted(missing)}")
    if fm.get("model") not in MODELS:
        fail(f"{path.name}: model '{fm.get('model')}' not in {sorted(MODELS)}")
    if fm.get("effort") not in EFFORTS:
        fail(f"{path.name}: effort '{fm.get('effort')}' not in {sorted(EFFORTS)}")
    if not fm.get("maxTurns", "").isdigit():
        fail(f"{path.name}: maxTurns must be an integer")
    if fm.get("omitClaudeMd") != "true":
        fail(f"{path.name}: omitClaudeMd must be true (seat cost)")
    tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
    if not tools or not tools <= TOOLS:
        fail(f"{path.name}: tools {sorted(tools)} not a subset of {sorted(TOOLS)}")
    read_only = "read-only" in fm.get("description", "").lower() or "Read-only" in fm.get("description", "")
    if read_only and tools & WRITE_TOOLS:
        fail(f"{path.name}: described as read-only but has {sorted(tools & WRITE_TOOLS)}")
    if not read_only and not tools >= WRITE_TOOLS:
        fail(f"{path.name}: coder seat lacks Edit/Write")
    body = path.read_text(encoding="utf-8").split("---\n", 2)[2]
    if not read_only and "REPORT_FILE" not in body:
        fail(f"{path.name}: coder seat body never mentions REPORT_FILE")
    return name


def main() -> int:
    seats = {check_agent(p) for p in sorted(AGENTS.glob("*.md"))} - {None}
    expected = {"relay-coder-lite", "relay-coder", "relay-coder-opus", "relay-coder-top", "relay-reviewer", "relay-diffcheck"}
    if seats != expected:
        fail(f"agents/: seats {sorted(seats)} != expected {sorted(expected)}")

    # every seat referenced in the docs must exist, and every seat must be documented in SKILL.md and README
    for doc in (SKILL, README, RESEARCH, *AGENTS.glob("*.md")):
        # seat names are always written in backticks; scratch paths like relay-light-<ts> are not seats
        for ref in set(re.findall(r"`(relay-[a-z-]+)`", doc.read_text(encoding="utf-8"))):
            if ref not in seats and ref != "relay-tier":
                fail(f"{doc.relative_to(ROOT)}: references unknown seat '{ref}'")
    for seat in seats:
        for doc in (SKILL, README):
            if f"`{seat}`" not in doc.read_text(encoding="utf-8"):
                fail(f"{doc.relative_to(ROOT)}: seat '{seat}' is not documented")

    skill_fm = frontmatter(SKILL)
    if skill_fm.get("name") != "relay" or not skill_fm.get("description"):
        fail("SKILL.md: frontmatter must have name: relay and a description")
    skill = SKILL.read_text(encoding="utf-8")
    for needle in ("relay-tier: max", "relay-tier: pro", "AskUserQuestion", "## 6. Fix loop", "## 0. Tier"):
        if needle not in skill:
            fail(f"SKILL.md: missing '{needle}'")

    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    market = json.loads(MARKET.read_text(encoding="utf-8"))
    pv, mv = plugin.get("version"), market["plugins"][0].get("version")
    if pv != mv:
        fail(f"version mismatch: plugin.json {pv} vs marketplace.json {mv}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", pv or ""):
        fail(f"plugin.json: version '{pv}' is not semver")
    if plugin.get("name") != "relay" or market["plugins"][0].get("name") != "relay":
        fail("manifests: plugin name must be 'relay'")

    if failures:
        print("\n".join(f"FAIL {f}" for f in failures), file=sys.stderr)
        return 1
    print(f"OK: {len(seats)} seats, SKILL.md, README.md, manifests v{pv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
