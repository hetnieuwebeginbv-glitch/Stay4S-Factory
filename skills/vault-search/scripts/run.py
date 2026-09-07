"""Vault-search skill — doorzoek de eigen InfoVault (direct DB-toegang, geen API-laag)."""
import os
import sys
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stay4s:stay4s@postgres:5432/stay4s")

def main():
    term = " ".join(sys.argv[1:]).strip()
    if not term:
        print("Gebruik: vault-search <zoekterm>")
        return
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, substring(body from 1 for 120) FROM infovault "
            "WHERE title ILIKE %s OR body ILIKE %s OR tags::text ILIKE %s "
            "ORDER BY found_at DESC NULLS LAST LIMIT 10",
            (f"%{term}%", f"%{term}%", f"%{term}%"),
        )
        rows = cur.fetchall()
    conn.close()
    if not rows:
        print(f"Niets gevonden voor '{term}'.")
        return
    print(f"*INFOVAULT '{term}'* ({len(rows)} treffers)")
    for vid, title, body in rows:
        print(f"{title} — {body}")

if __name__ == "__main__":
    main()
