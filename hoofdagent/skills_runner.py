"""SKILLS RUNNER — StayLM-00's skillsysteem (v0.1).

Spiegelt Stay4Compa's .agents/skills: elke skill is een map met SKILL.md
(frontmatter: name, description, argument-hint) en scripts/run.py.
De hoofdagent-graph roept run_skill() aan; of de poller pakt opdrachten die
beginnen met '!' (commando's van Mitchell, zoals bij Stay4Compa).
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stay4s:stay4s@postgres:5432/stay4s")
SKILLS_DIR = os.environ.get("SKILLS_DIR", os.path.join(os.path.dirname(__file__), "..", "skills"))
POLL_SECONDS = int(os.environ.get("SKILLS_POLL", "5"))
MY_NAME = "skills_runner"


def load_skills():
    skills = {}
    if not os.path.isdir(SKILLS_DIR):
        return skills
    for name in os.listdir(SKILLS_DIR):
        skill_md = os.path.join(SKILLS_DIR, name, "SKILL.md")
        run_py = os.path.join(SKILLS_DIR, name, "scripts", "run.py")
        if os.path.isfile(skill_md) and os.path.isfile(run_py):
            with open(skill_md, errors="ignore") as f:
                head = f.read(2000)
            desc_m = re.search(r"description:\s*(.+)", head)
            skills[name] = {
                "script": run_py,
                "description": desc_m.group(1).strip() if desc_m else "",
            }
    return skills


def run_skill(skills: dict, command: str) -> str:
    cmd, _, args = command.strip().lstrip("!").strip().partition(" ")
    if cmd in ("help", ""):
        lines = ["*STAYLM-00 COMMANDO'S*"]
        for i, (name, s) in enumerate(sorted(skills.items()), 1):
            lines.append(f"{i}. !{name} — {s['description'][:70]}")
        return "\n".join(lines) if len(lines) > 1 else "Geen skills geinstalleerd in skills/."
    skill = skills.get(cmd)
    if not skill:
        return f"Onbekend commando '{cmd}'. Typ !help."
    try:
        out = subprocess.run(
            [sys.executable, skill["script"], args.strip()],
            capture_output=True, text=True, timeout=120,
        )
        return out.stdout.strip() or out.stderr.strip()[:500] or "(geen output)"
    except subprocess.TimeoutExpired:
        return f"Skill '{cmd}' duurde te lang (timeout 120s)."
    except Exception as exc:  # v0.1: rapporteren, niet crashen
        return f"Skill '{cmd}' fout: {exc}"


def main():
    skills = load_skills()
    print(f"[{MY_NAME}] {len(skills)} skills geladen: {', '.join(sorted(skills))}")
    if os.environ.get("SKILLS_ONCE"):
        print(run_skill(skills, os.environ["SKILLS_ONCE"]))
        return
    import time
    while True:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, raw_text FROM opdrachten WHERE assigned_agent='staylm00' AND status='queued' AND raw_text LIKE '!%' ORDER BY created_at LIMIT 1"
                )
                row = cur.fetchone()
            if not row:
                conn.close()
                time.sleep(POLL_SECONDS)
                continue
            oid, raw = row
            result = run_skill(skills, raw)
            with conn.cursor() as cur:
                cur.execute("UPDATE opdrachten SET status='done', result_text=%s WHERE id=%s", (result, oid))
                cur.execute(
                    "INSERT INTO tool_audit_log (agent_slug, tool_name, arguments, outcome) VALUES (%s,%s,%s,%s)",
                    (MY_NAME, "skill_run", json.dumps({"id": str(oid), "cmd": raw[:120]}), "done"),
                )
            conn.commit()
            conn.close()
            # refresh: nieuwe skills zijn live herlaadbaar
            skills = load_skills()
        except psycopg2.Error as exc:
            print(f"[{MY_NAME}] db-fout: {exc}")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
