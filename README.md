# AI Chat

Leichtgewichtige KI-Chat-Webapp: **FastAPI** im Backend, **Svelte + Vite + TypeScript** im Frontend.
Antworten werden per Server-Sent Events live gestreamt. Der LLM-Anbieter ist austauschbar (aktuell OpenAI und ein Fake-Provider zum Testen).

## Struktur

```
backend/app/
├── main.py              # App-Factory, Router, Auslieferung des gebauten Frontends
├── core/config.py       # Einstellungen aus Umgebungsvariablen / .env
├── core/security.py     # Prüfung der Zitadel-Tokens (Dependency get_current_user)
├── api/deps.py          # Dependency-Wiring (Provider, Services)
├── api/routers/         # "Controller": dünne HTTP-Schicht
├── schemas/             # Pydantic-Modelle für Requests/Responses
├── services/            # Geschäftslogik
└── providers/           # LLM-Anbieter hinter einem gemeinsamen Interface
frontend/src/
├── lib/api.ts           # API-Client inkl. SSE-Parser
├── lib/auth.ts          # Login mit Zitadel (oidc-client-ts)
└── lib/components/      # Chat-UI
```

## Setup

Voraussetzungen: [uv](https://docs.astral.sh/uv/) und Node.js 24+.

```bash
cp .env.example .env          # OPENAI_API_KEY eintragen (oder LLM_PROVIDER=fake)
cd backend && uv sync
cd ../frontend && npm install
```

## Entwicklung

Backend und Frontend zusammen starten (Ctrl+C beendet beide), dann http://localhost:5173 öffnen:

```bash
./dev.sh
```

Oder einzeln in zwei Terminals:

```bash
# Backend auf http://localhost:8000 (API-Doku unter /docs, wenn API_DOCS_ENABLED=true)
cd backend && uv run fastapi dev app/main.py

# Frontend auf http://localhost:5173 (leitet /api an das Backend weiter)
cd frontend && npm run dev
```

Ohne API-Key testen: in `.env` den Wert `LLM_PROVIDER=fake` setzen. Die Antwort ist dann ein Echo.

## Login mit Zitadel

Ohne `AUTH_ENABLED=true` ist die App offen (praktisch für die Entwicklung). Mit Login darf nur chatten, wer in Zitadel die Projektrolle `chat-user` hat. Die App leitet ohne Session direkt zur Zitadel-Loginseite weiter; im Header stehen danach Name und „Abmelden“.

Einrichtung in der Zitadel-Console:

1. **Projekt** anlegen, Rolle `chat-user` hinzufügen und „Assert Roles on Authentication“ aktivieren.
2. Im Projekt eine **Applikation** vom Typ „User Agent“ anlegen: Authentifizierung „PKCE“, in den Token-Einstellungen **Auth Token Type „JWT“** und **Refresh Token** aktivieren.
3. **Redirect-URIs** und **Post-Logout-URIs**: `http://localhost:5173` und `http://localhost:8000` – exakt so, **ohne** `/` am Ende, Zitadel vergleicht Zeichen für Zeichen (dafür „Development Mode“ einschalten, weil `http`). Später die Produktions-URL.
4. Den gewünschten Benutzern unter **Authorizations** die Rolle `chat-user` geben.
5. Empfohlen: Lebensdauer des Access Tokens kurz halten (z.B. 1 h), die Erneuerung läuft per Refresh Token.

Dann in `.env` setzen:

```bash
AUTH_ENABLED=true
ZITADEL_ISSUER=https://<instanz>.zitadel.cloud
ZITADEL_CLIENT_ID=<Client-ID der App>
ZITADEL_PROJECT_ID=<Resource-ID des Projekts>
```

Das Backend prüft jedes Token lokal mit den öffentlichen Schlüsseln von Zitadel (Signatur, Issuer, Audience, Ablauf) und die Rolle. Ungültiges Token → 401 (die App leitet neu zur Anmeldung), fehlende Rolle → 403 („Kein Zugriff“). Das Frontend holt die Zitadel-Daten zur Laufzeit von `/api/auth/config`, dasselbe Docker-Image funktioniert also in jeder Umgebung.

## Tests & Linting

```bash
cd backend
uv run pytest
uv run ruff check . && uv run ruff format .

cd ../frontend && npm run check
```

## Docker

Ein Container enthält Backend und gebautes Frontend:

```bash
docker build -t ai-chat .
docker run -p 8000:8000 --env-file .env ai-chat
```

Danach läuft die App auf http://localhost:8000. Den Port gibt die Variable `PORT` vor (Standard 8000), wie es Railway erwartet.

## Deployment auf Railway

Railway baut das `Dockerfile` bei jedem Push auf `main` und stellt die App unter einer Railway-Subdomain mit HTTPS bereit. Build, Healthcheck (`/api/health`) und Neustart-Regel stehen in `railway.toml`. GitHub Actions (`.github/workflows/ci.yml`) prüft bei jedem Push Backend (Ruff, Pytest) und Frontend (`npm run check`, Build).

Einmalige Einrichtung:

1. Auf [railway.com](https://railway.com) ein Projekt anlegen, **Deploy from GitHub repo** wählen, das Repo freigeben, Branch `main`.
2. Im Service unter **Settings**: Region **EU West** wählen und **Wait for CI** aktivieren, damit nur Commits mit grünen Checks deployt werden.
3. Unter **Variables** setzen (die `.env` kommt nicht ins Image):
   ```bash
   OPENAI_API_KEY=...
   LLM_MODEL=gpt-5.5
   AUTH_ENABLED=true
   ZITADEL_ISSUER=https://<instanz>.zitadel.cloud
   ZITADEL_CLIENT_ID=<Client-ID der App>
   ZITADEL_PROJECT_ID=<Resource-ID des Projekts>
   ```
   Optional `SYSTEM_PROMPT`, `USD_TO_CHF`, `LLM_PRICES`. `PORT` setzt Railway selbst.
4. Unter **Settings → Networking** eine Domain generieren (z.B. `ai-chat.up.railway.app`).
5. In Zitadel `https://<domain>` (ohne `/` am Ende) als Redirect- und Post-Logout-URI der App eintragen.

Wichtig: Nie mit `AUTH_ENABLED=false` deployen, sonst kann jeder mit der URL auf deine Kosten chatten. Die API-Doku (`/docs`, `/openapi.json`) ist standardmässig aus; lokal lässt sie sich mit `API_DOCS_ENABLED=true` einschalten.

## Erweitern

- **Neuer LLM-Anbieter:** Klasse mit `async def stream(messages, system_prompt)` in `providers/` anlegen und in `providers/factory.py` registrieren. Nach dem Text am Ende ein `Usage`-Objekt liefern, damit Tokens und Kosten angezeigt werden.
- **Preise:** Die Kostenanzeige ist eine Schätzung aus Tokens × Preis. Die Preistabelle steht in USD (wie bei OpenAI) in `core/pricing.py` und lässt sich per `LLM_PRICES` in `.env` ergänzen oder überschreiben (siehe `.env.example`). Angezeigt werden die Kosten in CHF, umgerechnet mit dem festen Kurs `USD_TO_CHF` (Standard 0.80, bei Bedarf in `.env` nachführen). Für unbekannte Modelle wird „–“ statt eines Betrags angezeigt.
- **Benutzer im Code:** `CurrentUser` aus `core/security.py` als Parameter eines Endpunkts liefert `id` (Zitadel-`sub`) und `roles`; ohne Login ist es ein anonymer Benutzer.
- **Neuer Endpunkt:** Router in `api/routers/` anlegen, Logik in einen Service in `services/` auslagern, Router in `main.py` einhängen.
