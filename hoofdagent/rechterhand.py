"""RECHTERHAND — De Denker (worker v0.1, StayLM-00 trio).

Pakt denk-opdrachten (assigned_agent='rechterhand', status='queued'): research,
samenvattingen en InfoVault-verrijking. Alles lezen, niets versturen zonder de Baas.

v0.1-handlers (zonder LLM - de echte taalverwerking doet de hoofdagent/later vLLM;
deze worker structureert):
  - samenvat: extractieve samenvatting van de taaktekst
  - vault: verrijkt onverwerkte InfoVault-entries (auto-tags, belangrijkheid, verwerkt)
Escalatie: onbekende taak -> failed met uitleg.
"""
from __future__ import annotations
import json
import os
import re
import time

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stay4s:stay4s@postgres:5432/stay4s")
POLL_SECONDS = int(os.environ.get("RECHTERHAND_POLL", "5"))
MY_NAME = "rechterhand"

KEYWORD_TAGS = {
    "pixel": "pixel", "caiman": "pixel", "rom": "rom", "lineage": "rom",
    "whatsapp": "whatsapp", "meta": "whatsapp", "github": "github",
    "esim": "esim", "technokas": "industrieel", "kas": "industrieel",
    "gpu": "thuis", "staylm": "ai", "agent": "ai", "factory": "ai",
    "domein": "cloud", "nextcloud": "cloud", "subsidie": "financiering",
}


def db():
    return psycopg2.connect(DATABASE_URL)


def handler_samenvat(beschrijving: str) -> str:
    text = beschrijving or ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    lines = ["Samenvatting (extractief):"]
    for i, p in enumerate(paragraphs[:10], 1):
        first = re.split(r"(?<=[.!?])\s+", p)[0]
        lines.append(f"{i}. {first[:160]}")
    if len(paragraphs) > 10:
        lines.append(f"(+ {len(paragraphs) - 10} alinea's niet getoond)")
    return "\n".join(lines)


def handler_vault(conn, beschrijving: str) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT id, titel, body FROM infovault WHERE metadata->>'verwerkt' IS DISTINCT FROM 'true' LIMIT 20")
        rows = cur.fetchall()
    processed = 0
    for vid, titel, body in rows:
        combined = f"{titel} {body}".lower()
        tags = sorted({tag for kw, tag in KEYWORD_TAGS.items() if kw in combined})
        belang = "hoog" if any(k in combined for k in ("kritiek", "blokkeer", "security", "fout")) else "gemiddeld"
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE infovault SET metadata = metadata || %s::jsonb WHERE id=%s",
                (json.dumps({"tags_auto": tags, "belangrijkheid_auto": belang, "verwerkt": "true"}), vid),
            )
        processed += 1
    return f"InfoVault: {processed} entries verrijkt (auto-tags, belangrijkheid, verwerkt=true)."


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
            low = (beschrijving or "").lower()
            if "samenvat" in low or "summar" in low:
                result, status = handler_samenvat(beschrijving), "done"
            elif "vault" in low or "verrijk" in low:
                result, status = handler_vault(conn, beschrijving), "done"
            else:
                result = "Geen handler - Baas definieert de taak of voert zelf uit."
                status = "failed"
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE opdrachten SET status=%s, result_text=%s WHERE id=%s",
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
