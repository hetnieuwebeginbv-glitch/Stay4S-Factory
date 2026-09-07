# CAPABILITY-PARITEIT: STAY4COMPA -> STAYLM-00
## Wat Stay4Compa (Base44) kan en hoe StayLM-00 hetzelfde leert — 7 september 2026

Mitchell's doel: een eigen AI die alles kan wat Stay4Compa kan, draaiend op eigen infra, naast (hiernaast) het bestaande systeem. Dit is de kaart.

| # | Stay4Compa-capaciteit | StayLM-00-equivalent | Status |
|---|---------------------|---------------------|--------|
| 1 | WhatsApp ontvangen | Cloud API gateway (HMAC, whitelist) | KLAAR (PR #1) |
| 2 | Antwoorden + proactieve berichten | Gateway + 24u-venster/templates | KLAAR (wacht op Meta-verificatie) |
| 3 | Langetermijngeheugen (feiten, beslissingen) | user_facts + conversation_summaries (Postgres) | SCHEMA KLAAR — learning run moet gaan draaien |
| 4 | InfoVault + semantisch zoeken | infovault (Postgres) + Qdrant embeddings | SCHEMA KLAAR — embeddings via rechterhand |
| 5 | Skills (herbruikbare scripts) | skills/ + skills_runner.py | NIEUW GEBOUWD (v0.1) |
| 6 | Workflows/automations (cron + triggers) | scheduler.py + opdrachten-wachtrij | NIEUW GEBOUWD (v0.1) |
| 7 | Entity CRUD | Eigen Postgres — volledige controle | KLAAR (alle tabellen zijn van ons) |
| 8 | Sub-agents + factory | agent_register + linkerhand + rechterhand | KLAAR (v0.1) |
| 9 | Browser/web-onderzoek | browser-service (Playwright container) | FASE 2 |
| 10 | Beeldgeneratie/visie | Eigen modellen op GPU's (Qwen2.5-VL) | FASE 3 (GPU's thuis) |
| 11 | File storage (uploads, links) | MinIO S3 (Stay4S Cloud) | FASE 2 (Cloud-roadmap week 3-4) |
| 12 | OAuth-connectors (Gmail, Drive...) | Sovereignty-first: eigen services vervangen ze | BEWUST ANDERS — Stay4S Mail/Chat vervangen Gmail/WhatsApp op termine |

## WAT STAYLM-00 BETER KAN DAN STAY4COMPA
1. Volledige data-controle: elke byte blijft op eigen hardware (privacy = product)
2. Geen credit-limieten: eigen GPU's = eigen rekenbudget
3. Directe databasetoegang voor skills (geen API-laag nodig)
4. Eigen modellen (StayLM/vLLM) — geen externe AI-afhankelijkheid

## VOLGORDE NAAR PARITEIT
1. NU: skills-runner + scheduler op de stack (dit PR)
2. Meta-verificatie rond -> WhatsApp live
3. Learning run live -> geheugen groeit dagelijks ( zoals Stay4Compa save_memory)
4. Qdrant embeddings -> InfoVault doorzoekbaar op betekenis
5. Fase 2: browser-service, MinIO, dashboard UI (Command Center web)
6. Fase 3: visie/spraak op eigen GPU's — volledige soevereiniteit

## GESPIEGELDE ARCHITECTUUR (geen silo)
Stay4Compa blijft draaien als kwaliteitspoort + back-up + gespiegeld archief.
InfoVault sync: Base44 InfoVault <-> eigen infovault-tabel (export/import klaar).
Failover: valt de eigen infra plat, vangt Stay4Compa de WhatsApp-afhandeling op.
