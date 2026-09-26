# AI Chat

Leichtgewichtige KI-Chat-Webapp: **FastAPI** im Backend, **Svelte + Vite + TypeScript** im Frontend.
Antworten werden per Server-Sent Events live gestreamt. Der LLM-Anbieter ist austauschbar (aktuell OpenAI und ein Fake-Provider zum Testen).

## Struktur

```
backend/app/
├── main.py              # App-Factory, Router, Auslieferung des gebauten Frontends
├── core/config.py       # Einstellungen aus Umgebungsvariablen / .env
├── core/security.py     # Token-Validierung (Dependency get_current_user)
├── api/deps.py          # Dependency-Wiring (Provider, Services)
├── api/routers/         # "Controller": dünne HTTP-Schicht
├── schemas/             # Pydantic-Modelle für Requests/Responses
├── services/            # Geschäftslogik
└── providers/           # LLM-Anbieter hinter einem gemeinsamen Interface
frontend/src/
├── lib/api.ts           # API-Client inkl. SSE-Parser
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

Zwei Terminals:

```bash
# Backend auf http://localhost:8000 (API-Doku unter /docs)
cd backend && uv run fastapi dev app/main.py

# Frontend auf http://localhost:5173 (leitet /api an das Backend weiter)
cd frontend && npm run dev
```

Ohne API-Key testen: in `.env` den Wert `LLM_PROVIDER=fake` setzen. Die Antwort ist dann ein Echo.

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

Danach läuft die App auf http://localhost:8000. Das Image lässt sich direkt auf Fly.io, Render, Railway o.ä. deployen.

## Erweitern

- **Neuer LLM-Anbieter:** Klasse mit `async def stream(messages, system_prompt)` in `providers/` anlegen und in `providers/factory.py` registrieren. Nach dem Text am Ende ein `Usage`-Objekt liefern, damit Tokens und Kosten angezeigt werden.
- **Preise:** Die Kostenanzeige ist eine Schätzung aus Tokens × Preis. Die Preistabelle steht in USD (wie bei OpenAI) in `core/pricing.py` und lässt sich per `LLM_PRICES` in `.env` ergänzen oder überschreiben (siehe `.env.example`). Angezeigt werden die Kosten in CHF, umgerechnet mit dem festen Kurs `USD_TO_CHF` (Standard 0.80, bei Bedarf in `.env` nachführen). Für unbekannte Modelle wird „–“ statt eines Betrags angezeigt.
- **Token-Validierung:** `AUTH_ENABLED=true` setzen und in `core/security.py` beim `TODO` die JWT-Prüfung ergänzen (z.B. mit PyJWT + JWKS des Auth-Anbieters). Im Frontend den Token mit `setAuthToken()` aus `lib/api.ts` setzen.
- **Neuer Endpunkt:** Router in `api/routers/` anlegen, Logik in einen Service in `services/` auslagern, Router in `main.py` einhängen.
