# CLAUDE.md

Lightweight AI chat web app: FastAPI backend (`backend/`), Svelte 5 + Vite + TypeScript frontend (`frontend/`). Answers stream to the browser via Server-Sent Events. The LLM provider is pluggable (OpenAI, plus a `fake` echo provider for tests/dev).

## Commands

Backend (Python 3.12, managed with `uv`; run from `backend/`):

```bash
uv sync                              # install deps
uv run fastapi dev app/main.py       # dev server on :8000, API docs at /docs
uv run pytest                        # all tests
uv run pytest tests/test_chat.py::test_stream_returns_tokens_then_done   # single test
uv run ruff check . && uv run ruff format .
```

Frontend (Node 24+; run from `frontend/`):

```bash
npm install
npm run dev      # :5173, proxies /api -> localhost:8000 (vite.config.ts)
npm run check    # svelte-check + tsc — the only frontend verification (no tests, no linter)
npm run build
```

Docker (single image: built frontend served by FastAPI from `/app/static`):

```bash
docker build -t ai-chat . && docker run -p 8000:8000 --env-file .env ai-chat
```

Configuration comes from `.env` (see `.env.example`); `Settings` reads `.env` or `../.env`, so the root `.env` works when running from `backend/`. Set `LLM_PROVIDER=fake` to run without an API key.

## Backend architecture

Layered, request flows top to bottom:

- `app/main.py` — `create_app()` factory; mounts routers under `/api`; mounts `static/` at `/` only if it exists (i.e. in Docker).
- `app/api/routers/` — thin HTTP layer. `chat.py` is `POST /api/chat/stream`; the whole chat router requires `get_current_user`.
- `app/api/deps.py` — dependency wiring. The provider is built once via `@lru_cache` (`_cached_provider`) so the HTTP client is reused; `ProviderConfigError` becomes HTTP 503.
- `app/services/chat_service.py` — business logic, independent of HTTP and provider. Raises `ValueError` for invalid conversations. Turns the provider's `Usage` into a `UsageReport` with `cost_usd` (estimated via `core/pricing.py`; `None` for models without a known price).
- `app/providers/` — `LLMProvider` is a `Protocol` with `stream(messages, system_prompt) -> AsyncIterator[str | Usage]` (text deltas, then at most one `Usage` with token counts). `factory.create_provider` selects by `settings.llm_provider`. `OpenAIProvider` uses the **Responses API** (`client.responses.create(..., stream=True)`), not Chat Completions.
- `app/schemas/chat.py` — Pydantic request models (roles only `user`/`assistant`; system prompt is injected server-side from settings).
- `app/core/config.py` — `Settings` (pydantic-settings) via cached `get_settings()`; `model_prices` merges `LLM_PRICES` (JSON in `.env`) over `DEFAULT_PRICES` from `core/pricing.py`. `core/security.py` — Bearer auth; with `AUTH_ENABLED=false` every request is `ANONYMOUS_USER`. JWT validation is a **TODO stub**: with auth enabled, any Bearer token is accepted.

### SSE contract (backend ↔ frontend)

Events are `token`*, then at most one `usage` (JSON object: `model`, token counts, `cost_usd` or `null`), followed by exactly one `done` or `error`. Uses FastAPI's built-in `fastapi.sse` (`EventSourceResponse`, `ServerSentEvent`), which **JSON-encodes `data`** — the frontend `JSON.parse`s each data field. Errors after streaming has started are sent as an `error` event (HTTP status stays 200): `ValueError` messages are passed through to the user, other exceptions are logged and replaced by a generic message. Errors raised before streaming (validation → 422, missing API key → 503) are normal HTTP errors with `detail`.

If you change event names or encoding, update both `routers/chat.py` and `frontend/src/lib/api.ts` (and the `parse_sse` helper in `tests/test_chat.py`).

### Adding things

- New provider: class with `async def stream(...)` in `providers/` (yield a `Usage` at the end), add a case in `factory.py`, extend the `llm_provider` `Literal` in `config.py`.
- New endpoint: router in `api/routers/`, logic in a service in `services/`, include the router in `main.py`.

## Tests

`tests/conftest.py` builds the app with `create_app()` and uses `dependency_overrides` to force `Settings(_env_file=None, llm_provider="fake")` and `FakeProvider(delay=0)` — tests never read the real `.env` or call OpenAI. Tests that exercise the real factory must clear `deps._cached_provider.cache_clear()` before and after (see `test_missing_api_key_returns_503`).

## Frontend

- Svelte 5 runes (`$state`, `$effect`, `$props`); no router, no store library. `App.svelte` → `ChatWindow.svelte` holds all chat state.
- `lib/api.ts` — `streamChat()` uses `fetch` + manual SSE parsing (EventSource can't POST). `setAuthToken()` is the hook for future auth. Aborting via `AbortController` implements the Stop button.
- `lib/markdown.ts` — assistant messages are rendered with `marked` and **must** be sanitized with DOMPurify before `{@html}` (done in `renderMarkdown`). Never render model output through `{@html}` without it.
- Theming: CSS custom properties in `app.css`; dark is default, light via `data-theme="light"` on `<html>`, persisted in `localStorage` (inline script in `index.html` prevents a flash).

## Workflow

- **Grill before building.** For every request that changes the repo (new feature, change, refactor, plan/roadmap item), first check whether requirements are clear before writing code. If anything relevant is unclear — scope, behavior, UI placement, naming, edge cases, trade-offs between approaches — ask targeted questions first (prefer the AskUserQuestion tool; one question per decision, recommended option first with a short reason). Resolve decisions you can answer from the code, ROADMAP.md or sensible defaults yourself instead of asking. Don't grill simple questions, confirmations ("yes") or trivial, unambiguous edits. Ask in German, matching how the user writes.
- **Keep the ROADMAP.md overview current.** The "Übersicht" at the top is a table with one row per roadmap item (columns Nr., Punkt, Status, Beschreibung; German text, one-sentence description). Status is "Offen" or "✅ Erledigt"; open rows come first, then finished ones, each group sorted by number. When an item is added, finished (also mark its detail heading "✅ umgesetzt") or dropped, update the overview in the same change.
- After completing any change to the repository, always ask the user whether the change should be committed, and include the ready-to-use commit message in that same question (imperative, English, matching the existing history, e.g. "Add ...", "Fix ..."). Do not commit without an explicit yes; on yes, commit with exactly that message unless the user edits it.

## Conventions

- Code comments and identifiers in English; README and user-facing UI strings are German (e.g. "Neuer Chat", "Schliessen" — Swiss spelling, no ß).
- Ruff: line length 100, rules `E F I B UP ASYNC`; `Depends`/`Security` in defaults are allowed. Prefer `Annotated[...]` dependency aliases (`ChatServiceDep`, `CurrentUser`).
- Frontend style: no semicolons, single quotes, 2-space indent.
