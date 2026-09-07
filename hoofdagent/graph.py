# 7J — LangGraph hoofdagent skeleton
# Pakketten: langgraph>=0.2.60, langchain-core>=0.3, httpx, psycopg[binary], redis, qdrant-client
import json
import os
import uuid
from typing import Annotated, TypedDict

import httpx
import psycopg
import redis
from langgraph.graph import END, StateGraph

DATABASE_URL = os.environ["DATABASE_URL"]
LLM_BASE_URL = os.environ["LLM_BASE_URL"]
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8000")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOS = os.environ.get("GITHUB_REPOS", "miesdevries/Stay4s-grokrom,hetnieuwebeginbv-glitch/Stay4S-Pixel,hetnieuwebeginbv-glitch/Stay4S-app")

rdb = redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)


def db():
    return psycopg.connect(DATABASE_URL, autocommit=True)


# ---------- LLM (eigen vLLM, geen externe API) ----------

def llm(system: str, user: str, json_mode: bool = False) -> str:
    body = {
        "model": "Qwen/Qwen2.5-72B-Instruct-AWQ",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.3,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    resp = httpx.post(f"{LLM_BASE_URL}/chat/completions", json=body, timeout=120)
    return resp.json()["choices"][0]["message"]["content"]


# ---------- State ----------

class AgentState(TypedDict):
    sender: str
    text: str
    intentie: dict          # {type, onderwerp, urgentie}
    geheugen: str           # relevante feiten + samenvattingen
    plan: list              # stappen: zelf doen / delegeren / alleen antwoorden
    resultaten: Annotated[list, lambda a, b: a + b]
    antwoord: str


# ---------- Node 1: intentie-herkenning ----------

def intentie_node(state: AgentState) -> dict:
    prompt = f"""Classificeer dit WhatsApp-bericht van Mitchell. Antwoord ALLEEN als JSON:
{{"type": "vraag|opdracht|informatie_delen|status_verzoek", "onderwerp": "...", "urgentie": "laag|normaal|hoog", "delegeren": true|false, "team": "github|verwerking|geen"}}
Bericht: {state['text']}"""
    out = llm("Je bent de intentie-classificeerder van het Stay4S-hoofdagentsysteem. Nederlands, exact, geen uitleg.", prompt, json_mode=True)
    return {"intentie": json.loads(out)}


# ---------- Node 2: geheugen ophalen ----------

def geheugen_node(state: AgentState) -> dict:
    # 1. recente feiten uit user_facts
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT inhoud FROM user_facts WHERE gebruiker=%s ORDER BY created_at DESC LIMIT 20", ("mitchell",))
        feiten = "\n".join(f"- {r[0]}" for r in cur.fetchall())
        cur.execute("SELECT samenvatting FROM conversation_summaries ORDER BY created_at DESC LIMIT 3")
        samenv = "\n".join(f"- {r[0]}" for r in cur.fetchall())
    # 2. Qdrant RAG (aanbeveling: sentence-transformers all-MiniLM-L6-v2 voor embeddings)
    #    qdrant_client via QDRANT_URL, collectie 'infovault'
    return {"geheugen": f"BEKEND OVER MITCHELL:\n{feiten}\n\nRECENTE GESPREKKEN:\n{samenv}"}


# ---------- Node 3: planning ----------

def planning_node(state: AgentState) -> dict:
    i = state["intentie"]
    if not i.get("delegeren"):
        return {"plan": ["zelf_antwoorden"]}
    team = i.get("team", "github")
    stappen = [
        {"actie": "opdracht_aanmaken", "team": team},
        {"actie": "wachten_op_resultaat"},
        {"actie": "kwaliteitscontrole"},
        {"actie": "antwoorden"},
    ]
    return {"plan": stappen}


# ---------- Node 4: delegatie ----------

def delegatie_node(state: AgentState) -> dict:
    plan = state["plan"]
    if plan == ["zelf_antwoorden"]:
        return {"resultaten": []}
    i = state["intentie"]
    opdracht = {
        "titel": f"WhatsApp-verzoek: {i.get('onderwerp', 'onbekend')[:80]}",
        "beschrijving": state["text"],
        "opdrachtgever": "hoofdagent",
        "prioriteit": i.get("urgentie", "normaal"),
    }
    resp = httpx.post(f"{GATEWAY_URL}/opdrachten", json=opdracht, timeout=30)
    opdracht_id = resp.json()["id"]
    # worker pakt de opdracht op uit de wachtrij (zie pr_reviewer.py / agents-worker)
    return {"resultaten": [{"opdracht_id": opdracht_id, "team": i.get("team")}]}


# ---------- Node 5: uitvoering + kwaliteitscontrole ----------

def uitvoeren_node(state: AgentState) -> dict:
    i = state["intentie"]
    if not i.get("delegeren"):
        return {}
    # directe tools (alleen intern): GitHub check via REST — geen MCP nodig voor simpele scans
    if i.get("team") == "github" and "repo" in (i.get("onderwerp", "") + state["text"]).lower():
        resultaten = []
        for repo in GITHUB_REPOS.split(","):
            resp = httpx.get(f"https://api.github.com/repos/{repo}/commits?per_page=3",
                             headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}, timeout=30)
            for c in resp.json():
                resultaten.append(f"{repo}: {c['commit']['message'][:100]}")
        return {"resultaten": resultaten}
    return {}


def kwaliteitscontrole_node(state: AgentState) -> dict:
    # Controleer resultaat opdrachten; mislukte opdrachten -> escalatie naar Mitchell
    for res in state["resultaten"]:
        if isinstance(res, dict) and res.get("opdracht_id"):
            resp = httpx.get(f"{GATEWAY_URL}/opdrachten", timeout=30)
            # volledige fetch + check status='gesloten'; bij 'gefaald' -> markeer escalatie
    return {}


# ---------- Node 6: terugkoppeling naar WhatsApp ----------

def antwoord_node(state: AgentState) -> dict:
    systeem = f"""Je bent de Stay4S hoofdagent: warm, proactief, actiegericht, in het Nederlands.
Je antwoordt Mitchell alsof je een collega bent die doorpakt. Gebruik het geheugen en de resultaten.
Max 8 regels, WhatsApp-stijl (geen markdown behalve *vet*).
{state['geheugen']}"""
    resultaten = "\n".join(str(r) for r in state["resultaten"]) or "(geen teamresultaten)"
    antwoord = llm(systeem, f"BERICHT: {state['text']}\n\nRESULTATEN:\n{resultaten}")
    # stuur terug via gateway (WhatsApp indien echte zender, anders print voor web-test)
    if state["sender"] and state["sender"] != "web":
        httpx.post(f"{GATEWAY_URL}/webhook/send", json={"to": state["sender"], "text": antwoord}, timeout=30)
    # geheugen opslaan: samenvatting van dit gesprek
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO conversation_summaries (kanaal, kanaal_id, samenvatting) VALUES (%s,%s,%s)",
            ("whatsapp", state["sender"], f"Bericht: {state['text'][:200]} -> Antwoord: {antwoord[:200]}"),
        )
    return {"antwoord": antwoord}


# ---------- Graph bouwen ----------

graph = StateGraph(AgentState)
graph.add_node("intentie", intentie_node)
graph.add_node("geheugen", geheugen_node)
graph.add_node("planning", planning_node)
graph.add_node("delegatie", delegatie_node)
graph.add_node("uitvoeren", uitvoeren_node)
graph.add_node("kwaliteit", kwaliteitscontrole_node)
graph.add_node("antwoord", antwoord_node)

graph.set_entry_point("intentie")
graph.add_edge("intentie", "geheugen")
graph.add_edge("geheugen", "planning")
graph.add_edge("planning", "delegatie")
graph.add_edge("delegatie", "uitvoeren")
graph.add_edge("uitvoeren", "kwaliteit")
graph.add_edge("kwaliteit", "antwoord")
graph.add_edge("antwoord", END)

app_graph = graph.compile()


# ---------- Main loop: luister naar de gateway-queue ----------

def main():
    print("Hoofdagent draait. Wacht op berichten...")
    while True:
        # Redis Streams consumer (blockend)
        entries = rdb.xread({"messages:inbox": "$"}, block=5000, count=10)
        for stream, msgs in entries or []:
            for msg_id, fields in msgs:
                result = app_graph.invoke({
                    "sender": fields["sender"],
                    "text": fields["text"],
                    "resultaten": [],
                    "antwoord": "",
                })
                print(f"[hoofdagent] -> {result['antwoord'][:120]}")


if __name__ == "__main__":
    main()
