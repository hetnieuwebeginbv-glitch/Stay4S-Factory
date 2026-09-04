# Stay4S Agent Factory (7G–7N)

WhatsApp Cloud API v23.0 → FastAPI gateway → Redis Streams → LangGraph hoofdagent → PR-reviewer → Postgres/Qdrant → WhatsApp.

```bash
cp .env.example .env
docker compose up -d postgres redis qdrant gateway hoofdagent
```

Docs: docs/7G_ARCHITECTUUR.md, docs/7M_WHATSAPP_CLOUD_SETUP.md, docs/7N_TESTPLAN.md

Meta Business-verificatie kan weken duren — start die eerst.
