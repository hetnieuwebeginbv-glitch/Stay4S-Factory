"""Status skill — agents, opdrachten, laatste audit."""
import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stay4s:stay4s@postgres:5432/stay4s")

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT slug, status FROM agent_register ORDER BY slug")
    agents = cur.fetchall()
    cur.execute("SELECT assigned_agent, status, COUNT(*) FROM opdrachten GROUP BY assigned_agent, status")
    opdr = cur.fetchall()
    conn.close()
    print("*STAYLM-00 STATUS*")
    print(f"Agents: {len(agents)}")
    for slug, status in agents:
        print(f"- {slug}: {status}")
    print("Opdrachten:")
    for agent, status, n in opdr:
        print(f"- {agent or 'onbekend'}: {n}x {status}")

if __name__ == "__main__":
    main()
