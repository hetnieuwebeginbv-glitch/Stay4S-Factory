# HET ZOEKTEAM (SEEKER TEAM) — BLAUWDRUK v0.1
## Mitchell's "AI-team dat als een gek met ADHD overal zoekt" — 8 september 2026

# HET CONCEPT

Twee kanten, één team: de JACHT is chaotisch (parallel, breed, associatief, obsessief —
alles wat ook maar riekt naar relevantie wordt gevolgd), de UITKOMST is kalm
(elke vondst wordt bruikbare informatie: getagd, gewogen, actiebaar, in de InfoVault).

Motto: "Zoek als een gek. Rapporteer als een notaris."

# DE ZES TEAMLEDEN

## 1. NOTULIST — de gespreksarchivaris
Inzet: elk gesprek op elk platform (WhatsApp, Grok, ChatGPT, belnotities, meetings).
Doe: samenvatten + extractie van acties, beslissingen, feiten, risico's, deadlines, namen.
Output: InfoVault-entry per gesprek (titel, samenvatting, tags, actie_vereist, ruwe_inhoud).
Rechten: lezen aangeboden materiaal; niets versturen.

## 2. WEB_SEEKER — de web-onderzoeker
Inzet: gerichte jachten ("zoek alles over X", "vergelijk A en B", "check concurrent Y").
Doe: meerdere hoeken per vraag (nieuws, docs, forums, prijzen, reviews), bronnen noemen.
Output: gestructureerde vondsten + bron-URL's; twijfel expliciet markeren.
Rechten: web lezen; geen accounts, geen aankopen.

## 3. GITHUB_SEEKER — de repo-verkenner
Inzet: repos, PR's, issues, releases, profielactiviteit (eigen accounts + relevanten).
Doe: scannen, vergelijken, afwijkende activiteit signaleren (security!).
Output: repo-rapporten + actiepunten; al deels live als wekelijkse workflow.
Rechten: GitHub read-only (matches Groks factory-model).

## 4. PHONE_SEEKER — de toestel-verkenner
Inzet: alles op telefoon/tablet — foto's, screenshots, documenten, PDF's, notities.
Doe: OCR, schema's lezen, document-info extraheren, duplicaten herkennen, ordenen.
Output: bruikbare InfoVault-entries met type bron (foto/document/screenshot).
Nu: via uploads naar Stay4Compa (photo-analyse + phoneDocScanner staan klaar).
Later: op het toestel zelf via Stay4S-app/AetherBridge; op Stay4OS via VaultService-index.
Rechten: eigen toestellen alleen; Guardian-gated; nooit cloud-backups van derden.

## 5. NETWERK_SEEKER — de netwerk-verkenner
Inzet: het eigen netwerk — devices, diensten, poorten, edge nodes, mesh-nodes.
Doe: inventaris (wat hangt er aan), health (wat is degraded, zoals relay-mesh-03),
afwijkend verkeer, kwetsbaarheden (eigen scan, geen aanval).
Output: netwerk-rapport + NodeAlarm's bij afwijkingen (entities bestaan al).
Nu: via de bestaande NetworkNode/NodeAlarm-monitoring (Base44).
Later: volledige LAN-scan vanuit eigen infra (Pi/AX102 agent).
Rechten: ALLEEN eigen netwerk; read-only; elke scan in de audit-log.

## 6. RAPPORTMAKER — de rapporteur
Inzet: na elke jacht (of op afroep: "maak rapport over X").
Doe: vondsten van alle seekers samenvoegen tot één bruikbaar rapport:
samenvatting, bronnen, acties met eigenaar, risico's, beslispunten.
Output: rapport → InfoVault + push naar System-Verslag repo + WhatsApp-samenvatting.
Rechten: lezen alle vondsten; versturen alleen via de Baas.

# DE ADHD-JACHTPROTOCOLLEN (hoe het team "als een gek" zoekt)

1. PARALLEL: alle seekers kunnen tegelijk op verschillende sporen jagen
2. BREDE NETTEN: per vraag minimaal 3 zoekhoeken; zoektermen worden gevarieerd
3. ASSOCIATIEF: een vondst die linkt naar een andere vondst wordt gevolgd (tot 2 sprongen diep)
4. OBSESSIEF VERVOLGEN: openstaande vragen worden herhaald geprikt tot ze dicht zijn
5. NIETS KWIJT: ook "misschien relevant"-vondsten worden opgeslagen met belangrijkheid laag
MAAR: de output-discipline is heilig — geen chaos in de InfoVault, alleen bruikbare entries.

# VEILIGHEIDSREGELS (NON-ONDERHANDBELBAAR)

1. Read-only op alle bronnen; niets wijzigen, niets versturen zonder de Baas
2. Eigen toestellen, eigen accounts, eigen netwerk — NOOIT derden scannen
3. Elke zoekactie in de tool_audit_log (wie, wat, waarom, uitkomst)
4. Geen persoonsgegevens naar buiten; alles blijft op eigen infra
5. Netwerk-scans alleen vanaf eigen apparaten richting eigen apparaten

# INPASSING IN DE ARCHITECTUUR

De Baas (StayLM-00) stuurt het team aan via het opdrachtensysteem; het team zijn
factory-templates (agent_register). VOORSTEL aan [grok]: uitbreiding template-allowlist
met: notulist | web_seeker | github_seeker | phone_seeker | network_seeker | rapportmaker.
 Elk met minimale rechten per Groks beveiligingsmodel (geen shell, read-only, cap 20).

# WAT DRAAIT AL (Stay4Compa, vandaag) → WAT HEEFT INFRA NODIG

NU LIVE: notulist (gesprekken plakken/uploaden), web_seeker (on demand), github_seeker
(wekelijks + on demand), phone_seeker via uploads (photo-analyse), rapportmaker (rapporten + repo-push).
FASE 1 (na PR #1 merge): templates in de factory, aangesproken via opdrachten.
FASE 2 (Stay4S-app op Pixel): echte on-device phone_seeker.
FASE 3 (12m2/Pi's): volledige network_seeker op eigen infra.
