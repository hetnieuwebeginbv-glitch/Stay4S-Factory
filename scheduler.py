"""SCHEDULER — StayLM-00's automations (v0.1). Spiegelt Stay4Compa's workflows.

Elke job maakt een opdracht aan in de wachtrij (auditeerbaar, oneindig herhaalbaar).
De uitvoerende agent (hoofdagent/rechterhand) pakt hem op. Cron-loop om de 60s.
"""
from __future__ import annotations
import datetime as dt
import os
import time

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stay4s:stay4s@postgres:5432/stay4s")
TZ = dt.timezone(dt.timedelta(hours=2))  # Europe/Amsterdam CEST — v0.1; zoneinfo bij v0.2


def db():
    return psycopg2.connect(DATABASE_URL)


def create_opdracht(conn, raw_text: str, agent: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO opdrachten (wa_id, raw_text, intent, assigned_agent, status) "
            "VALUES (%s, %s, 'automation', %s, 'queued')",
            (f"cron-{int(time.time())}", raw_text, agent),
        )
    conn.commit()


def run_job(conn, job) -> None:
    create_opdracht(conn, job["text"], job["agent"])


def main():
    print("[scheduler] gestart")
    while True:
        now = dt.datetime.now(TZ)
        plan = []
        if now.hour == 3 and now.minute < 1:  # nightly learning run 03:00
            plan.append({"key": "learning", "agent": "staylm00",
                         "text": "Learning run: vat de dag samen, werk user_facts bij, verrijk de infovault, "
                                 "vul Qdrant, detecteer patronen en stel het groeirapport op."})
        if now.weekday() == 6 and now.hour == 19 and now.minute < 30:  # zondag 19:00 weekplanning
            plan.append({"key": "weekplan", "agent": "rechterhand",
                         "text": "Weekplanning: maak de gap-analyse per spoor (doel/hebben/missen/volgende stap) "
                                 "en bereid de weekplanning als concept voor."})
        for job in plan:
            conn = db()
            run_job(conn, job)
            conn.close()
            print(f"[scheduler] job aangemaakt: {job['key']}")
            time.sleep(60)  # geen dubbele runs binnen de minuut
        time.sleep(60)


if __name__ == "__main__":
    main()
