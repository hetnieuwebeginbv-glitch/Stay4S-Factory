"""LINKERHAND — De Bouwer (worker v0.1, StayLM-00 trio).

Pakt bouw-opdrachten (assigned_agent='linkerhand', status='queued') uit de
opdrachten-wachtrij, voert ze uit en rapporteert terug. De Baas (StayLM-00)
of Mitchell maakt de opdrachten aan via de gateway.

Rechten (least privilege): GitHub read-only (list/get). Geen shell, geen writes,
geen externe communicatie. Escalatie: onbekende taak -> status 'failed' met
uitleg voor de Baas.
"""
from __future__ import annotations
import json
import os
import time
import urllib.request

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stay4s:stay4s@postgres:5432/stay4s")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "hetnieuwebeginbv-glitch")
API = "https://api.github.com"
POLL_SECONDS = int(os.environ.get("LINKERHAND_POLL", "5"))
MY_NAME = "linkerhand"


def db():
    return psycopg2.connect(DATABASE_URL)


def gh_get(url: str):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "stay4s-linkerhand",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as exc:  # v0.1: alles rapporteren, niet crashen
        return {"_error": str(exc)}


def audit(conn, tool: str, arguments: dict, outcome: str, http_status=None):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tool_audit_log (agent_slug, tool_name, arguments, outcome, http_status) VALUES (%s,%s,%s,%s,%s)",
            (MY_NAME, tool, json.dumps(arguments), outcome, http_status),
        )
    conn.commit()


def handler_repo_scan(opdracht) -> str:
    repos = gh_get(f"{API}/users/{GITHUB_OWNER}/repos?per_page=50&sort=updated")
    if isinstance(repos, dict) and "_error" in repos:
        return f"GitHub-fout: {repos['_error']}"
    lines = [f"Repo-scan {GITHUB_OWNER} ({len(repos)} repos):"]
    for repo in repos[:15]:
        lines.append(f"- {repo['name']} upd={repo['updated_at'][:10]} open_issues={repo['open_issues_count']}")
    return "\n".join(lines)


def handler_pr_check(opdracht) -> str:
    key_repos = os.environ.get("KEY_REPOS", "Stay4S-Factory,Stay4S-Pixel,Stay4S-app").split(",")
    lines = ["Open pull requests:"]
    found = 0
    for repo in key_repos:
        pulls = gh_get(f"{API}/repos/{GITHUB_OWNER}/{repo.strip()}/pulls?state=open")
        if isinstance(pulls, list):
            for p in pulls:
                found += 1
                lines.append(f"#{p['number']} {repo.strip()} - {p['title']} ({p['user']['login']})")
        else:
            lines.append(f"{repo.strip()}: fout {pulls.get('_error')}")
    if not found:
        lines.append("geen open PR's")
    return "\n".join(lines)


HANDLERS = {
    "repo": handler_repo_scan,
    "github": handler_repo_scan,
    "pr": handler_pr_check,
}


def pick_handler(beschrijving: str):
    low = (beschrijving or "").lower()
    for key, fn in HANDLERS.items():
        if key in low:
            return fn
    return None


def main():
    print(f"[{MY_NAME}] worker gestart - poll {POLL_SECONDS}s")
    while True:
        try:
            conn = db()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, titel, beschrijving FROM opdrachten WHERE assigned_agent=%s AND status='queued' ORDER BY created_at LIMIT 1",
                    (MY_NAME,),
                )
                row = cur.fetchone()
            if not row:
                conn.close()
                time.sleep(POLL_SECONDS)
                continue
            oid, titel, beschrijving = row
            print(f"[{MY_NAME}] opdracht {oid}: {titel}")
            handler = pick_handler(beschrijving)
            if handler is None:
                result = "Geen handler voor dit type taak - Baas moet handler definieren of zelf uitvoeren."
                status = "failed"
            else:
                try:
                    result = handler(row)
                    status = "done"
                except Exception as exc:
                    result = f"Uitvoeringsfout: {exc}"
                    status = "failed"
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE opdrachten SET status=%s, result_text=%s, error_text=NULL WHERE id=%s",
                    (status, result, oid),
                )
                cur.execute(
                    "INSERT INTO tool_audit_log (agent_slug, tool_name, arguments, outcome) VALUES (%s,%s,%s,%s)",
                    (MY_NAME, "opdracht_execute", json.dumps({"id": str(oid), "titel": titel}), status),
                )
            conn.commit()
            conn.close()
        except psycopg2.Error as exc:
            print(f"[{MY_NAME}] db-fout: {exc} - opnieuw in {POLL_SECONDS}s")
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print(f"[{MY_NAME}] gestopt")
            break


if __name__ == "__main__":
    main()
