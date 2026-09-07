# 7N — Testplan: bewijs dat het systeem werkt

HOOFDSCENARIO (end-to-end):
"Stuur via WhatsApp: 'check de repos'" -> hoofdagent -> GitHub team -> rapport terug in WhatsApp.

FASE 0 — Infra (voor Meta-verificatie, via web-chat)
1. docker compose up -d postgres redis qdrant; init.sql draait automatisch
2. Start gateway en hoofdagent; check logs op "Hoofdagent draait"
3. curl "http://localhost:8000/chat?q=hallo" -> antwoord komt van de LLM (bewijst: queue -> graph -> LLM -> geheugen)

FASE 1 — Hoofdagent kan-heid
4. Test: "wat weet je over mij?" -> antwoord bevat feiten uit user_facts (bewijst geheugen-laag)
5. Test: "onthoud dat ik een Pixel 9 Pro ga kopen" -> controleer user_facts tabel (bewijst geheugen-schrijven)

FASE 2 — Teams
6. Maak opdracht via API: POST /opdrachten {"titel":"PR-check","beschrijving":"check repos","toegewezen_agent":"pr-reviewer"} -> PR-reviewer worker verwerkt en sluit af (bewijst team-laag)
7. Controleer infovault: PR-rapport staat erin (bewijft opslag-laag)

FASE 3 — Agent factory
8. POST /agents met een nieuwe agent-definitie -> container wordt gespawnd + registratie in agent_register (bewijst factory)
9. Security-test: POST /agents met verkeerde x-agent-key -> 401 (bewijst permissie-afscherming)
10. Audit-test: alle stappen staan in tool_audit_log (bewijst audit-laag)

FASE 4 — Echte WhatsApp
11. Zodra Meta-verificatie klaar is: stuur "check de repos" vanaf telefoon -> rapport terug in WhatsApp (bewijst het volledige scenario)
12. Spraaktest: stuur voice-note "check de repos" -> Whisper transcribeert -> zelfde flow

ACCEPTATIE: alle 12 stappen groen = systeem werkt. Elke fase levert bewijs op; vastlopers worden als opdracht aan Mitchell geëscaleerd.
