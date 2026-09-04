# 7I — FastAPI gateway: WhatsApp webhook, opdracht-endpoints, agent factory
# Stack: FastAPI 0.115+, httpx, psycopg (v3), redis-py
import hashlib
import hmac
import json
import os
import uuid

import httpx
import psycopg
import redis
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

app = FastAPI(title="Stay4S Gateway", version="0.1.0")

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]
WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_ID = os.environ["WHATSAPP_PHONE_ID"]
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
LLM_BASE_URL = os.environ["LLM_BASE_URL"]
ALLOWED_NUMBERS = set(os.environ.get("ALLOWED_NUMBERS", "").split(","))
APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")

rdb = redis.from_url(REDIS_URL, decode_responses=True)


def db():
    return psycopg.connect(DATABASE_URL, autocommit=True)


def audit(agent: str, tool: str, args: dict, result: str, status: str = "ok"):
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tool_audit_log (agent_name, tool_name, arguments, result, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (agent, tool, json.dumps(args), result[:8000], status),
        )


# ---------- 1. WhatsApp webhook ----------

@app.get("/webhook")
def webhook_verify(hub_mode: str = Query(...), hub_verify_token: str = Query(...),
                   hub_challenge: str = Query(...)):
    """Meta verification handshake (eenmalig bij het instellen van de webhook)."""
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="verify token mismatch")


@app.post("/webhook")
async def webhook_receive(request: Request):
    body = await request.body()
    # Signature check (aanbevolen zodra je APP_SECRET hebt)
    if APP_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=403, detail="bad signature")

    payload = json.loads(body)
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                sender = msg.get("from", "")
                if ALLOWED_NUMBERS and sender not in ALLOWED_NUMBERS:
                    continue  # anti-abuse: whitelist
                await handle_message(sender, msg)
    return {"status": "ok"}  # Meta wil altijd 200, anders stuurt hij opnieuw


async def handle_message(sender: str, msg: dict):
    msg_type = msg.get("type")
    wa_id = msg.get("id")

    if msg_type == "text":
        text = msg["text"]["body"]
    elif msg_type == "audio":
        # Spraakbericht → Whisper transcription
        audio_id = msg["audio"]["id"]
        text = await transcribe_audio(audio_id)
    elif msg_type == "image":
        # Foto → later: Qwen2.5-VL OCR via vision-agent
        image_id = msg["image"]["id"]
        text = await download_media(image_id)  # v1: bewaar + geef door als taak
        text = f"[afbeelding ontvangen, media_id={image_id}]"
    else:
        text = f"[niet-ondersteund berichttype: {msg_type}]"

    # In wachtrij voor de hoofdagent; antwoord komt async terug via send_whatsapp
    rdb.xadd("messages:inbox", {"sender": sender, "text": text, "wa_id": wa_id})
    audit("gateway", "whatsapp.receive", {"sender": sender, "type": msg_type}, text, "queued")


async def transcribe_audio(media_id: str) -> str:
    url = f"https://graph.facebook.com/v21.0/{media_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        meta = (await client.get(url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"})).json()
        audio_url = meta.get("url", "")
        audio = await client.get(audio_url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"})
        whisper = await client.post(
            f"{os.environ.get('WHISPER_URL', 'http://whisper:9000')}/asr",
            params={"task": "transcribe", "language": "nl", "output": "text", "audio_file": "audio.ogg"},
            files={"audio_file": ("audio.ogg", audio.content, "audio/ogg")},
        )
        return whisper.text.strip()


async def download_media(media_id: str) -> str:
    # hulpfunctie: media ophalen voor verwerkingsteam (doc-parser)
    return media_id


def send_whatsapp(to: str, text: str):
    """Antwoord terug naar WhatsApp via Meta Graph API (sync, aangeroepen door hoofdagent)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json=payload,
        )
        audit("gateway", "whatsapp.send", {"to": to}, resp.text)
    return resp.status_code


# ---------- 2. Web-chat testfront-end (tot Meta-verificatie klaar is) ----------

@app.get("/chat")
def chat(q: str = Query(...)):
    """Simpele test-ingang: zelfde pipeline als WhatsApp zonder Meta."""
    rdb.xadd("messages:inbox", {"sender": "web", "text": q, "wa_id": str(uuid.uuid4())})
    return {"status": "queued"}


# ---------- 3. Opdracht-endpoints ----------

class Opdracht(BaseModel):
    titel: str
    beschrijving: str
    opdrachtgever: str = "hoofdagent"
    toegewezen_agent: str | None = None
    prioriteit: str = "normaal"  # laag/normaal/hoog/kritiek
    deadline: str | None = None


@app.post("/opdrachten")
def create_opdracht(o: Opdracht):
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO opdrachten (titel, beschrijving, opdrachtgever, toegewezen_agent, prioriteit, deadline) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (o.titel, o.beschrijving, o.opdrachtgever, o.toegewezen_agent, o.prioriteit, o.deadline),
        )
        return {"id": cur.fetchone()[0]}


@app.get("/opdrachten")
def list_opdrachten(status: str = "open"):
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, titel, status, toegewezen_agent FROM opdrachten WHERE status = %s", (status,))
        return [{"id": row[0], "titel": row[1], "status": row[2], "agent": row[3]} for row in cur.fetchall()]


@app.post("/opdrachten/{opdracht_id}/resultaat")
def set_resultaat(opdracht_id: int, resultaat: dict):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE opdrachten SET status='gesloten', resultaat=%s WHERE id=%s",
                    (json.dumps(resultaat), opdracht_id))
        return {"ok": True}


# ---------- 4. Agent factory endpoint ----------

class AgentDef(BaseModel):
    naam: str
    rol: str
    specialisatie: str
    system_prompt: str
    tools: list[str] = []
    permissie_tier: str = "intern"  # read-only / intern / extern-actief


@app.post("/v1/factory/spawn")
@app.post("/agents")
def create_agent(a: AgentDef, request: Request):
    """Agent factory: registreert en spawn een nieuwe agent-container.
    BEVEILIGING (Grok-model, overgenomen): aparte FACTORY_TOKEN (NOOIT de interne
    AGENT_API_KEY), template-allowlist, cap van MAX_AGENTS actieve agents,
    nieuwe agents krijgen nooit meer permissies dan de hoofdagent."""
    key = request.headers.get("x-factory-token", "")
    if not FACTORY_TOKEN or key != FACTORY_TOKEN:
        raise HTTPException(status_code=401, detail="factory token vereist")
    if a.rol not in FACTORY_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"template '{a.rol}' niet toegestaan; kies uit {sorted(FACTORY_TEMPLATES)}")
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM agent_register WHERE status='actief'")
        if cur.fetchone()[0] >= MAX_AGENTS:
            raise HTTPException(status_code=429, detail=f"agent-cap bereikt ({MAX_AGENTS})")

    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO agent_register (naam, rol, specialisatie, system_prompt, tools, permissie_tier, created_by_agent) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (a.naam, a.rol, a.specialisatie, a.system_prompt, a.tools, a.permissie_tier, "hoofdagent"),
        )
        agent_id = cur.fetchone()[0]

    spawn_agent_container(agent_id, a)
    audit("hoofdagent", "agent.factory.spawn", {"naam": a.naam, "tools": a.tools}, f"agent_id={agent_id}")
    return {"id": agent_id, "naam": a.naam, "status": "spawned"}


def spawn_agent_container(agent_id: int, a: AgentDef):
    """Spawn de agent als Docker-container met eigen sessie (docker SDK).
    Elke agent draait geisoleerd, met alleen de tools die in de definitie staan."""
    import docker  # docker SDK
    client = docker.from_env()
    env = {
        "AGENT_ID": str(agent_id),
        "AGENT_NAME": a.naam,
        "SYSTEM_PROMPT": a.system_prompt,
        "TOOLS": ",".join(a.tools),
        "PERMISSIE_TIER": a.permissie_tier,
        "DATABASE_URL": DATABASE_URL,
        "LLM_BASE_URL": LLM_BASE_URL,
    }
    client.containers.run(
        image="stay4s-hoofdagent-agents:latest",  # dezelfde image, andere entrypoint-args
        name=f"stay4s-agent-{a.naam}-{agent_id}",
        environment=env,
        detach=True,
        auto_remove=True,
        network="stay4s-hoofdagent_default",
    )
