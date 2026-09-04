from __future__ import annotations
import os
import httpx

TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = os.environ.get("GITHUB_OWNER", "hetnieuwebeginbv-glitch")
API = "https://api.github.com"

def _headers():
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Stay4S-pr-reviewer"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h

def list_repos():
    names = []
    url = f"{API}/users/{OWNER}/repos?per_page=50&sort=updated"
    with httpx.Client(timeout=30.0, headers=_headers()) as client:
        resp = client.get(url)
        resp.raise_for_status()
        for repo in resp.json():
            names.append(f"{repo['full_name']} updated={repo.get('updated_at')} open_issues={repo.get('open_issues_count')}")
    return names

def list_pulls(repo: str):
    url = f"{API}/repos/{OWNER}/{repo}/pulls?state=open&per_page=20"
    with httpx.Client(timeout=30.0, headers=_headers()) as client:
        resp = client.get(url)
        if resp.status_code == 404:
            return [f"{repo}: not found"]
        resp.raise_for_status()
        pulls = resp.json()
        if not pulls:
            return [f"{repo}: geen open PRs"]
        return [f"#{p['number']} {p['title']} by {p['user']['login']}" for p in pulls]

def run_repo_check(user_text: str) -> str:
    lines = ["Stay4S GitHub-team rapport", f"Vraag: {user_text}", f"Owner: {OWNER}", ""]
    try:
        repos = list_repos()
    except httpx.HTTPError as exc:
        return f"GitHub API fout: {exc}"
    lines.append(f"{len(repos)} repos:")
    lines.extend(f"- {n}" for n in repos[:15])
    for focus in ("Stay4S-Pixel", "Stay4S-app", "Stay4Grok"):
        lines.append("")
        lines.append(f"Open PRs {focus}:")
        try:
            lines.extend(f"  {p}" for p in list_pulls(focus))
        except httpx.HTTPError as exc:
            lines.append(f"  fout: {exc}")
    lines.append("\nEinde rapport. Writes uit.")
    return "\n".join(lines)
