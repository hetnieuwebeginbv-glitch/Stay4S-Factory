# 7L — Voorbeeld-agent: complete GitHub PR-reviewer
# Draait als worker: pakt opdrachten uit de 'opdrachten' tabel (team github),
# haalt open PR's op via GitHub REST API, reviewt met de eigen LLM, rapporteert terug.
import json
import os

import httpx
import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
LLM_BASE_URL = os.environ["LLM_BASE_URL"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOS = os.environ.get(
    "GITHUB_REPOS",
    "miesdevries/Stay4s-grokrom,hetnieuwebeginbv-glitch/Stay4S-Pixel,hetnieuwebeginbv-glitch/Stay4S-app",
)

SYSTEM_PROMPT = """Je bent de PR-Reviewer van het Stay4S GitHub-team. Taken:
1. Beoordeel elke open pull request op: correctness, beveiliging (geen gelekte secrets!), code-stijl, testdekking.
2. Rapporteer in Nederlands, max 10 regels per PR.
3. Markeer BLOCKER bij: gelekte API-keys/wachtwoorden, SQL-injectie, shell-injectie, kapotte build.
4. Geef per PR een oordeel: APPROVE / COMMENT / REQUEST_CHANGES met 1-zin uitleg.
Rapportformat:
PR #<nummer> (<repo>) — <oordeel>
<bevindingen, max 3 bullets als tekstregels>
Eindoordeel: <oordeel>"""


def llm(user: str) -> str:
    resp = httpx.post(
        f"{LLM_BASE_URL}/chat/completions",
        json={
            "model": os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct-AWQ"),
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
            "temperature": 0.2,
        },
        timeout=180,
    )
    return resp.json()["choices"][0]["message"]["content"]


def haal_open_prs_op() -> list[dict]:
    prs = []
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    for repo in GITHUB_REPOS.split(","):
        resp = httpx.get(f"https://api.github.com/repos/{repo.strip()}/pulls?state=open",
                         headers=headers, timeout=30)
        for pr in resp.json():
            diff_resp = httpx.get(pr["diff_url"], headers=headers, timeout=30)
            prs.append({
                "repo": repo.strip(),
                "nummer": pr["number"],
                "titel": pr["title"],
                "auteur": pr["user"]["login"],
                "diff": diff_resp.text[:60000],
            })
    return prs


def sla_rapport_op(rapport: str, pr_count: int):
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO infovault (titel, samenvatting, bron, type, belangrijkheid, tags, actie_vereist, ruwe_inhoud, verwerkt) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,true)",
            (
                f"PR-review rapport ({pr_count} PR's)",
                rapport[:500],
                "github-team/pr-reviewer",
                "github-pr-review-" + str(pr_count),
                "technical",
                "medium",
                "{github,pr-review,code-kwaliteit}",
                "REQUEST_CHANGES" in rapport,
                rapport,
            ),
        )


def verwerk_opdracht(opdracht: dict):
    prs = haal_open_prs_op()
    if not prs:
        rapport = "Geen open pull requests gevonden. Alles schoon."
    else:
        user = "\n\n".join(
            f"PR #{p['nummer']} in {p['repo']} door {p['auteur']}: {p['titel']}\nDIFF:\n{p['diff']}"
            for p in prs
        )
        rapport = llm(f"Review deze {len(prs)} pull request(s):\n\n{user}")
    sla_rapport_op(rapport, len(prs))
    return rapport


def main():
    """Worker-loop: pakt github-team opdrachten op uit de database."""
    print("PR-reviewer worker draait...")
    while True:
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, beschrijving FROM opdrachten WHERE status='open' AND toegewezen_agent='pr-reviewer' LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                import time
                time.sleep(30)
                continue
            opdracht_id, beschrijving = row
            cur.execute("UPDATE opdrachten SET status='bezig' WHERE id=%s", (opdracht_id,))
        rapport = verwerk_opdracht({"id": opdracht_id, "beschrijving": beschrijving})
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE opdrachten SET status='gesloten', resultaat=%s WHERE id=%s",
                (json.dumps({"rapport": rapport[:4000]}), opdracht_id),
            )
            cur.execute("UPDATE agent_register SET tasks_completed = tasks_completed + 1 WHERE naam='pr-reviewer'")
        print(f"[pr-reviewer] opdracht {opdracht_id} afgerond")


if __name__ == "__main__":
    main()
