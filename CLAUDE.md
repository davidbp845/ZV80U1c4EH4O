# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A hexagonal-architecture (ports & adapters) skeleton for an "agentic orchestrator" — a chat-first AI assistant for AI-first small businesses (the example config is a massage center). The same domain/application code serves any business vertical; only `config/business.yaml` and the Obsidian vault of business knowledge change. Code, comments, and identifiers are in Spanish; keep new code consistent with that.

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-...
export TELEGRAM_BOT_TOKEN=...   # optional, only if canales.telegram is enabled

# Index the Obsidian vault into the RAG (Chroma) before first run
python -m adapters.out.obsidian_ingest --vault ./vault_negocio

# Run the system (starts FastAPI on :8000, and Telegram polling if configured)
python main.py

# Tests
pip install -r requirements-dev.txt
pytest                                  # run the whole suite
pytest tests/01_domain                  # run one layer only
pytest tests/03_application/test_orchestrator.py::test_da_mensaje_de_fallback_tras_agotar_iteraciones  # single test
```

There is no lint config or CI yet in this repo — don't assume `ruff`/`mypy` are wired up; check `requirements-dev.txt` before assuming a tool is available.

### Tests

`tests/` mirrors the dependency order of the architecture, and directories are numbered (`01_domain`, `02_config`, `03_application`, `04_adapters_out`, `05_adapters_in`, `06_main`) so the suite runs innermost-layer-first — the same order you'd want to debug a failure in. Domain tests use small hand-written fakes of the ports instead of the real adapters; adapter tests mock the external SDK/client (`anthropic.Anthropic`, `chromadb.PersistentClient`) rather than hitting real network or requiring credentials — nothing in the suite needs `ANTHROPIC_API_KEY` set or a running Chroma/Telegram backend. A root `conftest.py` puts the repo root on `sys.path` so `domain`/`application`/`adapters`/`config` are importable without installing the project as a package.

One gotcha the tests work around: `adapters/in_/fastapi_app.py` defines `app` and `_sesiones` at module scope, and `crear_router()` adds routes to that same shared `app` on every call — calling it twice registers duplicate routes, and Starlette keeps routing to whichever was registered first. `tests/05_adapters_in/test_fastapi_app.py` reloads the module per test to get an isolated `app`/`_sesiones` each time; keep that pattern if you add more tests there.

The web chat endpoint is `POST http://localhost:8000/chat` with body `{"usuario_id": "...", "mensaje": "..."}`.

## Architecture

Strict hexagonal architecture with dependency direction always pointing inward. Read `domain/ports.py` first — it's the contract every adapter must satisfy, and the fastest way to see the whole system's shape.

- **`domain/`** — entities (`entities.py`), abstract ports (`ports.py`), and use cases (`use_cases.py`). Pure Python, zero external dependencies (no LLM SDK, no DB driver, no web framework). This is the only layer that meaningfully differs between businesses (e.g. "book a table" instead of "book an appointment").
- **`application/`** — the agent orchestrator (`orchestrator.py`), the tool schema + tool executor that bridges LLM tool calls to domain use cases (`tools.py`), and system-prompt construction from business config (`prompts.py`). Knows about the LLM tool-calling protocol but not about any specific channel (web vs Telegram) or specific LLM vendor.
- **`adapters/in_/`** — inbound adapters (FastAPI web chat, Telegram bot). Pure translation layers: HTTP/Telegram ↔ `OrquestadorAgente.responder()`. No business logic ever belongs here.
- **`adapters/out/`** — outbound adapters: `llm_anthropic.py` (Anthropic SDK implementing `ProveedorLLM`), `vector_store.py` (Chroma implementing `RepositorioConocimiento`), `obsidian_ingest.py` (chunks and indexes the Obsidian vault — the vault is the single source of truth for business knowledge/FAQs/pricing), `repositorios_memoria.py` (in-memory repos for citas/clientes/pedidos/servicios/profesionales, meant to be swapped for Postgres without touching domain or application code).
- **`config/`** — `business.yaml` declares one business's services, professionals, tone, and channels; `loader.py` parses it into domain entities.
- **`main.py`** — the composition root. This is the *only* file allowed to know about concrete implementations; it wires adapters into use cases into the orchestrator. Swapping an adapter (e.g. Chroma → Qdrant, in-memory → Postgres, Telegram → WhatsApp) means writing a new class satisfying the same port and changing its instantiation here — nothing in `domain/` or `application/` changes.

### Request flow

Inbound adapter → `OrquestadorAgente.responder(sesion, mensaje)` → calls the LLM with `TOOLS_SCHEMA` → for each `tool_use` block, `EjecutorHerramientas.ejecutar()` dispatches to the matching domain use case → tool results are fed back to the LLM → loop (bounded by `max_iteraciones_tool`, default 4) until the LLM replies with plain text.

### Extending to a new business

1. Duplicate `config/business.yaml`, adjust services/professionals/tone.
2. Create a new Obsidian vault with that business's knowledge, point `vault_obsidian` at it, and re-run `obsidian_ingest`.
3. If the business needs a genuinely different use case (e.g. "reserve a table" instead of "reserve an appointment"), add it in `domain/use_cases.py` and expose a corresponding tool in `application/tools.py` (both the `TOOLS_SCHEMA` entry and the dispatch branch in `EjecutorHerramientas.ejecutar`). Nothing else in the system needs to change.

### Replacing an adapter

Example: swapping in-memory repos for Postgres — implement the same interfaces from `domain/ports.py` (`RepositorioCitas`, etc.) in a new `adapters/out/repositorios_postgres.py`, then change the instantiation in `main.py::construir_sistema()`. Domain and application code stay untouched.

## Conventions worth knowing

- `ProveedorLLM.generar_respuesta` returns a plain dict (not the Anthropic SDK's response object) — this keeps the orchestrator decoupled from the Anthropic SDK's types, so swapping LLM providers only requires a new adapter matching this same normalized shape.
- Day-of-week lookups use `date.weekday()` mapped through `_DIAS_SEMANA_ES` in `domain/use_cases.py`, not `strftime('%A')`, because the latter depends on OS locale and won't reliably match the Spanish day names used in `config/business.yaml`.
- Conversation sessions (`SesionConversacion`) live in an in-process dict in both inbound adapters — noted in-code as needing to move to Redis/DB for production multi-process deployments.
- `EjecutorHerramientas.ejecutar` catches all exceptions and returns `{"error": str(exc)}` rather than raising, so tool failures become a message the LLM can react to instead of crashing the conversation.
