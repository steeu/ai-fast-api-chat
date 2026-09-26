# Roadmap

## 1. Kosten- und Token-Anzeige ✅ umgesetzt

Nach jeder Antwort unter der Nachricht anzeigen: Input Tokens, Output Tokens, geschätzte Kosten, verwendetes Modell.

### Was die API liefert

Die OpenAI Responses API liefert **keine Kosten**, nur Token-Zahlen. Am Ende des Streams kommt ein `response.completed`-Event mit:

- `response.model` – das tatsächlich verwendete Modell (kann ein Snapshot-Name wie `gpt-5.5-2026-…` sein)
- `response.usage.input_tokens`, davon `input_tokens_details.cached_tokens` (günstiger abgerechnet)
- `response.usage.output_tokens`, davon `output_tokens_details.reasoning_tokens` (werden als Output abgerechnet, erscheinen aber nicht im Text)

Die Kosten müssen wir selbst aus Tokens × Preis berechnen.

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

## 2. RAG: Fragen an eigene Dokumente

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

### Kosten

- **Indexieren** ist günstig: `text-embedding-3-small` schafft laut OpenAI ca. 62’500 Seiten pro Dollar. Dank Hash-Vergleich wird nur Neues bezahlt.
- **Fragen mit Dokumenten** kosten spürbar mehr, weil die Chunks als Input mitgehen: 5 Chunks à ~700 Tokens ≈ 3’500 zusätzliche Input-Tokens ≈ 0.018 $ pro Frage mit gpt-5.5. Die Anzeige aus Punkt 1 macht das sichtbar – deshalb Punkt 1 zuerst umsetzen.

### Sicherheit

- Der Ordner ist nur serverseitig konfiguriert; der Client schickt nie Pfade. Das UI zeigt nur Dateinamen, keine vollständigen Pfade.
- Dokumenteninhalt ist ungeprüfte Eingabe: Text in Dokumenten kann versuchen, dem Modell Anweisungen zu geben (Prompt Injection). Quellen deshalb klar als Daten abgrenzen, nicht als Anweisungen.
- Textabschnitte der Dokumente werden zum Einbetten und bei Fragen an OpenAI gesendet – vertrauliche Dokumente entsprechend auswählen.
- Solange die Authentifizierung ein Platzhalter ist, sieht jeder mit Zugriff auf die App die Inhalte aller indexierten Dokumente.

### Etappen

1. **Indexierung** – Loader für PDF/Word/Excel, Chunking, Embeddings, SQLite, Status-Endpunkt; testbar ohne UI.
2. **Chat-Integration** – `use_documents`, Suche, Prompt mit Quellen, `sources`-Event.
3. **UI** – Schalter, Quellenliste, Status und Neu-indexieren-Button.
4. **Feinschliff** – Chunk-Grösse und Top-k anhand echter Dokumente abstimmen.

### Tests

Kleine Beispieldateien (je eine `.docx`, `.xlsx`, `.pdf`) als Test-Fixtures; Fake-Embeddings für deterministische Suche. Prüfen: Loader liefern Text + korrekte Seiten/Blätter, geänderte Dateien werden neu indexiert und gelöschte entfernt, `sources` kommt vor den Tokens, ohne `DOCS_DIR` ist RAG sauber deaktiviert.
