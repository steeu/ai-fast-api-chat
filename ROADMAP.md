# Roadmap

## Übersicht

| Nr. | Punkt | Status | Beschreibung |
|---|---|---|---|
| 2 | Login mit Zitadel | Offen | Anmeldung über Zitadel Cloud, nur Benutzer mit Projektrolle dürfen chatten; ersetzt den Auth-Platzhalter. |
| 3 | Deployment auf Railway | Offen | Docker-Image automatisch bei jedem Push auf `main` auf Railway deployen, sobald die Checks in GitHub Actions grün sind. |
| 4 | RAG: Fragen an eigene Dokumente | Offen | Word-, Excel- und PDF-Dateien aus einem Ordner indexieren und per Schalter im Chat mit Quellenangaben befragen. |
| 1 | Kosten- und Token-Anzeige | ✅ Erledigt | Modell, Input-/Output-Tokens und geschätzte Kosten unter jeder Antwort, Summe pro Chat im Header. |

## 1. Kosten- und Token-Anzeige ✅ umgesetzt

Nach jeder Antwort unter der Nachricht anzeigen: Input Tokens, Output Tokens, geschätzte Kosten, verwendetes Modell.

### Was die API liefert

Die OpenAI Responses API liefert **keine Kosten**, nur Token-Zahlen. Am Ende des Streams kommt ein `response.completed`-Event mit:

- `response.model` – das tatsächlich verwendete Modell (kann ein Snapshot-Name wie `gpt-5.5-2026-…` sein)
- `response.usage.input_tokens`, davon `input_tokens_details.cached_tokens` (günstiger abgerechnet)
- `response.usage.output_tokens`, davon `output_tokens_details.reasoning_tokens` (werden als Output abgerechnet, erscheinen aber nicht im Text)

Die Kosten müssen wir selbst aus Tokens × Preis berechnen.

Angezeigt werden die Kosten in **CHF**: Die Preistabelle bleibt in USD, umgerechnet wird mit einem festen Kurs (`USD_TO_CHF`, Standard 0.80, per `.env` anpassbar).

### Preise (Stand 2026-09, [OpenAI-Doku](https://developers.openai.com/api/docs/models/gpt-5.5))

| Modell | Input / 1 Mio. | Cached Input / 1 Mio. | Output / 1 Mio. |
|---|---|---|---|
| gpt-5.5 | $5.00 | $0.50 | $30.00 |

Sonderfälle: Prompts über 272K Input-Tokens kosten 2× Input und 1.5× Output; Data-Residency-Endpunkte +10 %. Für diesen Chat vernachlässigbar, aber die Anzeige bleibt deshalb eine **Schätzung**.

Beispiel: 1’000 Input- + 500 Output-Tokens ≈ 0.005 $ + 0.015 $ = **0.02 $**.

### Umsetzung

- **Preise konfigurierbar:** Kleine Preistabelle pro Modell in `core/` (Input, Cached Input, Output pro 1 Mio. Tokens), überschreibbar per `.env`. Nicht fest verdrahtet, weil sich Preise ändern. Snapshot-Namen auf das Basismodell abbilden. Unbekanntes Modell → Kosten „–“ statt falscher Zahl.
- **Provider:** `LLMProvider.stream()` in `providers/base.py` liefert heute nur Text (`AsyncIterator[str]`). Erweitern auf `AsyncIterator[str | Usage]` mit neuem Schema `Usage(model, input_tokens, cached_tokens, output_tokens, reasoning_tokens)`. `OpenAIProvider` liest das `response.completed`-Event aus; `FakeProvider` liefert geschätzte Werte (Wortanzahl), damit Tests und Entwicklung ohne API-Key funktionieren.
- **Kosten berechnen:** Im `ChatService` (nicht im Provider), damit es für künftige Anbieter gleich funktioniert. Formel: `(input − cached) × Input-Preis + cached × Cached-Preis + output × Output-Preis`.
- **SSE:** Neues Event `usage` vor `done` in `routers/chat.py`, Daten als JSON-Objekt inkl. `cost_usd` (oder `null`). SSE-Vertrag in `frontend/src/lib/api.ts` und im `parse_sse`-Helper der Tests nachziehen.
- **Frontend:** `streamChat()` bekommt einen `onUsage`-Handler; `ChatMessage` im Frontend erhält ein optionales `usage`-Feld; `MessageList.svelte` zeigt eine dezente Meta-Zeile, z.B. `gpt-5.5 · 1’000 → 500 Tokens · ~0.02 $`. Optional: Summe für den ganzen Chat im Header.
- **Tests:** Usage-Event kommt vor `done`; Kostenberechnung inkl. Cached Tokens und unbekanntem Modell.

## 2. Login mit Zitadel

Nur angemeldete Benutzer mit der passenden Projektrolle dürfen chatten. Der Login läuft über Zitadel Cloud und ersetzt den heutigen Platzhalter in `core/security.py`, der mit `AUTH_ENABLED=true` jeden Bearer-Token akzeptiert. Weil jede Anfrage OpenAI-Kosten verursacht und mit RAG (Punkt 4) Dokumenteninhalte sichtbar werden, kommt der Login vor RAG.

### Passt das zur Architektur?

Ja, die Anwendung ist darauf vorbereitet:

- **Backend:** `get_current_user` hängt bereits am ganzen Chat-Router; es fehlt nur die echte Token-Prüfung beim `TODO`.
- **Frontend:** `setAuthToken()` in `lib/api.ts` setzt den Bearer-Header. Weil der Stream über `fetch` statt `EventSource` läuft, geht der Header problemlos mit.
- **Docker:** Frontend und API laufen auf derselben Adresse – eine Redirect-URI pro Umgebung, kein CORS.

### Entscheidungen

| Frage | Entscheidung | Grund |
|---|---|---|
| Welche Instanz? | Zitadel Cloud | Kein eigener Betrieb (Datenbank, Updates); im Code ändert sich nur die Issuer-URL, ein Wechsel auf self-hosted bleibt möglich |
| Wie prüft das Backend Tokens? | Access Token als **JWT**, lokal geprüft mit den öffentlichen Schlüsseln (JWKS) | Kein Aufruf an Zitadel pro Anfrage; Introspection bräuchte einen Backend-Schlüssel und einen Netzwerkaufruf pro Request |
| Wer darf chatten? | Nur Benutzer mit Projektrolle `chat-user` | Kontrolle darüber, wer Kosten verursacht und (mit RAG) Dokumente sieht |
| Login-Ablauf | Ohne Session direkt zur Zitadel-Loginseite weiterleiten | Einfachster und sicherster Weg, keine eigene Loginseite |
| Woher kennt das Frontend die Zitadel-Daten? | Öffentlicher Endpunkt `GET /api/auth/config` | Ein Docker-Image für alle Umgebungen; Build-Variablen (`VITE_…`) würden die Werte ins Image brennen |

### Ablauf

```
Login:    Browser → Zitadel-Loginseite (Authorization Code + PKCE) → Access Token (JWT) im Browser
Anfrage:  Bearer-Token → /api/chat/stream → Backend prüft Signatur (JWKS), iss, aud, exp und Rolle
```

### Einrichtung in Zitadel (Console)

- **Projekt** anlegen, Rolle `chat-user` hinzufügen, „Rollen bei der Authentifizierung zusichern“ aktivieren (damit das Rollen-Claim im Token steht).
- **Applikation** vom Typ „User Agent“ (Single Page App): PKCE, kein Client Secret, Auth Token Type **JWT**, Refresh Token aktiv.
- **Redirect-URIs** und Post-Logout-URIs: `http://localhost:5173/` (Entwicklung, dafür „Development Mode“ für `http` einschalten), `http://localhost:8000/` (Docker), später die Railway-URL (Punkt 3).
- **Berechtigung:** Den gewünschten Benutzern die Rolle `chat-user` erteilen.
- **Token-Lebensdauer:** Access Token kurz halten (z.B. 1 h) und per Refresh Token erneuern, weil ein Token nach dem Abmelden bis zum Ablauf gültig bleibt.

### Umsetzung

**Konfiguration** (`core/config.py`, `.env.example`):
`AUTH_ENABLED=true`, `ZITADEL_ISSUER` (z.B. `https://<instanz>.zitadel.cloud`), `ZITADEL_CLIENT_ID` (für das Frontend), `ZITADEL_PROJECT_ID` (Audience und Rollen-Claim), `AUTH_REQUIRED_ROLE=chat-user`. Mit `AUTH_ENABLED=true` und fehlenden Werten startet das Backend mit klarer Fehlermeldung statt still unsicher.

**Backend:**
- `core/security.py`: Token mit `PyJWT[crypto]` prüfen; Schlüssel über `PyJWKClient("<issuer>/oauth/v2/keys")` laden und cachen (bei unbekannter `kid` neu laden, Schlüsselrotation). Geprüft werden Signatur (RS256), `iss`, `aud` (muss die Projekt-ID enthalten) und `exp`.
- Rolle aus dem Claim `urn:zitadel:iam:org:project:roles` lesen. Ungültiges/abgelaufenes Token → **401**, fehlende Rolle → **403**.
- `User` erhält `id` (`sub`) und die Rollen; mit `AUTH_ENABLED=false` bleibt alles wie heute (`ANONYMOUS_USER`).
- Neuer Router `routers/auth.py` mit `GET /api/auth/config` (öffentlich): `enabled`, `issuer`, `client_id`, `project_id`. `/api/health` bleibt ebenfalls öffentlich.

**Frontend:**
- `oidc-client-ts` mit `UserManager` (Authorization Code + PKCE ist Standard). Scopes: `openid profile email offline_access urn:zitadel:iam:org:project:id:<projectId>:aud`.
- Neues `lib/auth.ts`, aufgerufen in `main.ts` vor dem Mounten: Config laden; ist Auth aus, normal starten. Sonst Rückkehr von Zitadel verarbeiten (`?code=…`, danach URL bereinigen), vorhandene Session laden oder zu Zitadel weiterleiten. Token per `setAuthToken()` setzen und bei jeder Erneuerung aktualisieren (`automaticSilentRenew` mit Refresh Token).
- Header: Benutzername und Button „Abmelden“ (`signoutRedirect`).
- Fehler: 401 → erneut anmelden; 403 → Meldung „Kein Zugriff. Bitte beim Administrator die Freigabe anfragen.“ statt leerem Chat.

**Tests:** Im Test ein eigenes RSA-Schlüsselpaar erzeugen, Tokens damit signieren und den JWKS-Client ersetzen. Prüfen: gültiges Token mit Rolle → 200; abgelaufen, falsche Audience, falscher Issuer oder falsche Signatur → 401; ohne Rolle → 403; `AUTH_ENABLED=false` → anonym; `/api/auth/config` ohne Token erreichbar.

### Sicherheit

- Öffentlicher Client ohne Secret im Browser (PKCE); das Backend vertraut nur signierten Tokens von Zitadel.
- Rollen prüft ausschliesslich das Backend – Ausblenden im Frontend ist nur Komfort.
- `oidc-client-ts` speichert Tokens standardmässig im `sessionStorage`. Ein XSS-Fehler könnte sie auslesen; deshalb bleibt das Sanitizing der Modellantworten mit DOMPurify zwingend.
- Tokens nie loggen.

### Etappen

1. **Zitadel einrichten + Backend-Prüfung** – Projekt, Rolle, App; JWT-Prüfung und Rollencheck, testbar mit einem Token aus der Zitadel-Console bzw. per `curl`.
2. **Frontend-Login** – `auth.ts`, Weiterleitung, Token-Erneuerung, Abmelden.
3. **Feinschliff** – 403-Meldung, Anzeige des Benutzers, Doku in README und CLAUDE.md.

## 3. Deployment auf Railway

Die App läuft öffentlich auf Railway. Grundlage ist das bestehende `Dockerfile` (Frontend-Build + FastAPI in einem Image); Railway baut es bei jedem Push auf `main` und stellt es unter einer Railway-Subdomain mit HTTPS bereit. Kommt nach dem Login (Punkt 2), damit die öffentliche URL nicht ohne Schutz OpenAI-Kosten verursacht.

### Entscheidungen

| Frage | Entscheidung | Grund |
|---|---|---|
| Wie wird deployt? | Auto-Deploy aus GitHub (`main`) mit „Wait for CI“ | Kein manueller Schritt; ein Commit mit roten Tests wird nicht deployt |
| Welche Adresse? | Railway-Subdomain (z.B. `ai-chat.up.railway.app`) | HTTPS inklusive, sofort verfügbar; eigene Domain lässt sich später ergänzen |
| Welche Umgebungen? | Nur Produktion | Für eine kleine App reicht es, lokal zu testen; Staging lässt sich später als zweite Railway-Umgebung ergänzen |
| Wie wird gebaut? | Bestehendes `Dockerfile`, Einstellungen als Code in `railway.toml` | Gleiches Image lokal und auf Railway; Einstellungen versioniert statt nur im Dashboard |

### Umsetzung

**Image an Railway anpassen:**
- Railway gibt den Port über die Variable `PORT` vor. `CMD` im `Dockerfile` so ändern, dass `uvicorn` `${PORT:-8000}` verwendet (Shell-Form nötig, damit die Variable ausgewertet wird); lokal bleibt es bei 8000.
- Railway leitet Anfragen über einen Proxy weiter. `--proxy-headers` ist schon gesetzt; zusätzlich `--forwarded-allow-ips="*"`, damit FastAPI `https` und die echte Client-IP erkennt.
- SSE durch den Proxy prüfen: Die Antwort muss Stück für Stück ankommen und darf nicht gepuffert werden.

**`railway.toml`** im Repo-Root:
- Build mit dem `Dockerfile`.
- Healthcheck auf `/api/health`, damit Railway erst auf das neue Deployment umschaltet, wenn es antwortet.
- Neustart bei Fehlern (`restartPolicyType = "ON_FAILURE"`).

**CI** (`.github/workflows/ci.yml`, neu): Bei Push und Pull Request Backend (`ruff check`, `ruff format --check`, `pytest`) und Frontend (`npm run check`, `npm run build`) prüfen. „Wait for CI“ in Railway aktivieren, damit nur grüne Commits deployt werden.

**Einrichtung auf Railway:**
- Projekt anlegen, Service aus dem GitHub-Repo erstellen (Railway-GitHub-App für das Repo freigeben), Branch `main`.
- Region **EU West** wählen (nahe bei der Schweiz).
- Variablen im Service setzen statt `.env`: `OPENAI_API_KEY`, `LLM_MODEL`, `USD_TO_CHF`, `AUTH_ENABLED=true` und die `ZITADEL_*`-Werte aus Punkt 2. Die `.env` wird nicht ins Image kopiert (`.dockerignore`).
- Railway-Domain generieren und in Zitadel als Redirect- und Post-Logout-URI eintragen.

**Doku:** Abschnitt „Deployment auf Railway“ im README (Einrichtung, Variablen, Ablauf); Befehle und `railway.toml` in CLAUDE.md erwähnen.

### Kosten

- Railway rechnet nach Verbrauch ab (CPU, RAM, Traffic), mit einem Mindestbetrag je nach Plan. Für eine kleine App mit wenigen Benutzern bleibt das im Rahmen des Einstiegsplans; aktuelle Preise vor dem Start auf railway.com prüfen.
- Die OpenAI-Kosten kommen unabhängig davon dazu; die Kostenanzeige aus Punkt 1 macht sie sichtbar.

### Sicherheit

- Erst mit aktivem Login (Punkt 2) deployen: `AUTH_ENABLED=true` ist Pflicht, sonst kann jeder mit der URL auf deine Kosten chatten.
- Den API-Key nur als Railway-Variable hinterlegen, nie im Repo oder Image.
- Die API-Doku (`/docs`, `/openapi.json`) ist öffentlich erreichbar. Sie verrät keine Geheimnisse, lässt sich aber in Produktion abschalten (z.B. `docs_url=None`, per Setting).

### Etappen

1. **Image + CI** – `PORT`, Proxy-Einstellungen, `railway.toml`, GitHub-Actions-Workflow; lokal mit `docker run -e PORT=…` prüfen.
2. **Railway einrichten** – Service, Region, Variablen, Domain, Zitadel-Redirect-URIs; erstes Deployment inkl. Login und Streaming testen.
3. **Feinschliff** – README, optional API-Doku in Produktion abschalten.

## 4. RAG: Fragen an eigene Dokumente

Ein Ordner mit Dokumenten wird indexiert; im Chat kann man per Schalter „Mit Dokumenten antworten“ Fragen dazu stellen. Die Antwort zeigt, aus welchen Dateien (und Seiten/Blättern) sie stammt. Zuerst unterstützt: **Word (.docx), Excel (.xlsx), PDF**.

### Entscheidungen

| Frage | Entscheidung | Grund |
|---|---|---|
| Wo wird indexiert? | Lokal im Backend (eigene Embeddings + SQLite) | Volle Kontrolle über Chunking und Quellen; der OpenAI Vector Store (`file_search`) unterstützt kein `.xlsx`, und Dokumente lägen dauerhaft bei OpenAI |
| Woher kommen die Dokumente? | Fester Ordner, Pfad in `.env` (`DOCS_DIR`) | Einfach; in Docker als Volume eingebunden |
| Wann wird indexiert? | Beim Backend-Start + „Neu indexieren“-Button | Nur neue/geänderte Dateien, erkannt per Hash |
| Wann werden Dokumente genutzt? | Schalter im Chat-UI | Normale Fragen bleiben günstig und unbeeinflusst |

### Ablauf

```
Indexierung:  Ordner → Datei auslesen → in Abschnitte (Chunks) teilen → Embeddings (OpenAI) → SQLite
Frage:        Frage → Embedding → ähnlichste Chunks suchen → als Kontext + Quellen ans Modell → Antwort mit [1], [2]
```

### Umsetzung

**Konfiguration** (`core/config.py`, `.env.example`):
`DOCS_DIR` (z.B. `./docs`), `RAG_INDEX_PATH` (z.B. `./data/rag.sqlite`), `RAG_EMBEDDING_MODEL=text-embedding-3-small`, `RAG_TOP_K=5`. Ohne `DOCS_DIR` ist RAG deaktiviert und der Schalter im UI ausgeblendet.

**Dokumente auslesen** (neues Paket `app/rag/`, je Format ein Loader):

| Format | Bibliothek | Einheit für Quellenangabe | Hinweise |
|---|---|---|---|
| PDF | `pypdf` | Seite | Gescannte PDFs ohne Textebene liefern keinen Text → werden mit Warnung übersprungen (OCR ggf. später) |
| Word | `python-docx` | Überschrift/Abschnitt | Absätze **und Tabellen** auslesen, Überschriften als Kontext behalten |
| Excel | `openpyxl` (`read_only`, `data_only=True`) | Blatt + Zeilenbereich | Zeilen als „Spalte: Wert“-Text mit Kopfzeile, damit das Modell die Zahlen zuordnen kann; `data_only` liefert berechnete Werte statt Formeln |

Alte Formate (`.doc`, `.xls`) werden übersprungen und im Status gemeldet. Weitere Formate (`.txt`, `.md`, `.pptx`) lassen sich später als zusätzlicher Loader ergänzen.

**Chunking:** Abschnitte von ca. 500–800 Tokens mit etwas Überlappung, jeweils mit Metadaten (Datei, Seite/Blatt/Abschnitt). Excel-Chunks nie mitten in einer Zeile trennen und die Kopfzeile in jedem Chunk wiederholen.

**Embeddings:** Hinter einem kleinen Interface analog zu `LLMProvider` (`EmbeddingProvider`), mit OpenAI-Implementierung und einem deterministischen Fake für Tests. Aufrufe bündeln (viele Chunks pro Request).

**Speicher:** SQLite mit Tabellen `documents` (Pfad, Hash, Änderungsdatum, Status/Fehler) und `chunks` (Text, Metadaten, Embedding als Blob). Suche per Kosinus-Ähnlichkeit mit `numpy` über alle Vektoren im Speicher – reicht problemlos für einige zehntausend Chunks. Erst bei deutlich mehr auf eine Vektor-Erweiterung (z.B. `sqlite-vec`) wechseln.

**Indexierung:**
- Beim Start im FastAPI-`lifespan` als Hintergrundaufgabe, damit der Server nicht blockiert.
- Nur neue/geänderte Dateien (Hash-Vergleich); gelöschte Dateien aus dem Index entfernen.
- `POST /api/rag/reindex` startet eine Indexierung, `GET /api/rag/status` liefert Anzahl Dokumente/Chunks, letzten Lauf, laufend ja/nein und übersprungene Dateien mit Grund.

**Chat-Integration:**
- `ChatRequest` erhält `use_documents: bool = False`.
- `ChatService`: Bei aktivem Schalter die letzte Nutzerfrage einbetten, Top-k Chunks holen und als nummerierte Quellen in die Instruktionen einfügen, mit der Anweisung: nur auf Basis der Quellen antworten, mit `[1]`, `[2]` zitieren und sagen, wenn die Dokumente die Antwort nicht enthalten.
- Neues SSE-Event `sources` vor den `token`-Events (Liste mit Nummer, Dateiname, Seite/Blatt). SSE-Vertrag in `api.ts` und Tests nachziehen.

**Frontend:**
- Schalter „Mit Dokumenten antworten“ beim Eingabefeld (nur sichtbar, wenn RAG aktiv ist).
- Quellenliste unter der Antwort.
- Kleine Statusanzeige (z.B. „42 Dokumente indexiert“) mit „Neu indexieren“-Button.

**Docker:** `DOCS_DIR` und den Ordner des Index als Volumes einbinden, z.B. `-v ./docs:/app/docs:ro -v ./data:/app/data`. Die Dokumente nur lesend einbinden.

**Railway:** Pro Service ist nur ein Volume möglich, Dokumente und Index liegen dort also gemeinsam (z.B. `/app/data/docs` und `/app/data/rag.sqlite`). Wie die Dokumente auf das Volume kommen, ist bei der Umsetzung zu entscheiden (siehe Punkt 3).

### Kosten

- **Indexieren** ist günstig: `text-embedding-3-small` schafft laut OpenAI ca. 62’500 Seiten pro Dollar. Dank Hash-Vergleich wird nur Neues bezahlt.
- **Fragen mit Dokumenten** kosten spürbar mehr, weil die Chunks als Input mitgehen: 5 Chunks à ~700 Tokens ≈ 3’500 zusätzliche Input-Tokens ≈ 0.018 $ pro Frage mit gpt-5.5. Die Anzeige aus Punkt 1 macht das sichtbar – deshalb Punkt 1 zuerst umsetzen.

### Sicherheit

- Der Ordner ist nur serverseitig konfiguriert; der Client schickt nie Pfade. Das UI zeigt nur Dateinamen, keine vollständigen Pfade.
- Dokumenteninhalt ist ungeprüfte Eingabe: Text in Dokumenten kann versuchen, dem Modell Anweisungen zu geben (Prompt Injection). Quellen deshalb klar als Daten abgrenzen, nicht als Anweisungen.
- Textabschnitte der Dokumente werden zum Einbetten und bei Fragen an OpenAI gesendet – vertrauliche Dokumente entsprechend auswählen.
- Solange die Authentifizierung ein Platzhalter ist, sieht jeder mit Zugriff auf die App die Inhalte aller indexierten Dokumente (siehe Punkt 2).

### Etappen

1. **Indexierung** – Loader für PDF/Word/Excel, Chunking, Embeddings, SQLite, Status-Endpunkt; testbar ohne UI.
2. **Chat-Integration** – `use_documents`, Suche, Prompt mit Quellen, `sources`-Event.
3. **UI** – Schalter, Quellenliste, Status und Neu-indexieren-Button.
4. **Feinschliff** – Chunk-Grösse und Top-k anhand echter Dokumente abstimmen.

### Tests

Kleine Beispieldateien (je eine `.docx`, `.xlsx`, `.pdf`) als Test-Fixtures; Fake-Embeddings für deterministische Suche. Prüfen: Loader liefern Text + korrekte Seiten/Blätter, geänderte Dateien werden neu indexiert und gelöschte entfernt, `sources` kommt vor den Tokens, ohne `DOCS_DIR` ist RAG sauber deaktiviert.
