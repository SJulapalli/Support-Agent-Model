# NorthShop Support Agent — Project Spec

## Overview

A replica of Giga's (GigaML) enterprise AI support agent, built for portfolio demonstration. The agent resolves customer support tickets autonomously by **controlling a browser** — it never calls the backend API directly. The hero demo: a customer requests a refund, the agent navigates the internal ShopAdmin portal, looks up the order, verifies eligibility, and processes the refund end-to-end without human intervention.

The system layers three reliability mechanisms on top of the core agent loop:
1. **A second-pass verifier** that inspects every final response for policy violations, self-contradictions, and unverified claims before the user sees it.
2. **A structured escalation handoff** that produces a machine-readable summary for the human agent who picks up the conversation.
3. **Full action-event logging** so every browser step the agent took is auditable from the admin portal.

---

## Goals

- Demonstrate a full-stack, production-shaped AI agent
- Showcase browser-based task execution (Giga's core differentiator)
- Show production concerns: response verification, escalation handoff, and an auditable action log
- Complete and demoable within 2 weeks for job applications

---

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| LLM | Claude (Anthropic) | Prompt engineering only, no fine-tuning |
| Agent / browser / verifier model | `claude-sonnet-4-6` | Used by the main loop, the browser sub-agent, and the verifier |
| Embeddings | Voyage AI `voyage-3-lite` | 512-dim, used for RAG over policy docs |
| Backend | Python + FastAPI | Async, SSE streaming |
| Database | PostgreSQL + pgvector | Orders, customers, refunds, agent events, handoffs, embeddings |
| ORM / Migrations | SQLAlchemy (async) + Alembic | `asyncpg` driver |
| Browser automation | Playwright (async, headless Chromium) | DOM text extraction (not screenshots) |
| Frontend | React + TypeScript + Vite + React Router | |
| Monorepo | Single repo, two top-level packages | `backend/` and `frontend/` |

> **Note on models:** there is no cheap-routing / Haiku tier. Every Claude call — main loop, browser sub-agent, and verifier — uses `claude-sonnet-4-6`.

---

## Architecture

```
Customer (browser)
  │
  │  POST /api/chat  { conversation_id, message }
  ▼
[ChatWidget] ──SSE──▶ [run_agent()  (agent/loop.py)]
  ▲   │                      │
  │   │            ┌─────────┴──────────┐
  │   │       [retrieve_context]   [Claude loop  (claude-sonnet-4-6)]
  │   │            │ (RAG)              │  one tool: execute_browser_task
  │   │        [pgvector]              │
  │   │                          tool_use │
  │   │                                   ▼
  │   │                     [run_browser_task()  (browser/agent.py)]
  │   │                          │  inner Claude loop (≤15 steps)
  │   │                     [Playwright headless Chromium]
  │   │                          │  navigate / click / fill / read DOM
  │   │                          ▼
  │   │                     [ShopAdmin UI  (React /admin)]
  │   │                          │  fetch /admin/api/*
  │   │                          ▼
  │   │                     [Postgres]
  │   │
  │   ├─ every step ─▶ [log_event] ─▶ agent_events table
  │   │
  │   └─ final text ─▶ [verify_response] ──(correction?)──┐
  │                                                        │
  └──── SSE events: text · status · action_log · ─────────┘
        correction · handoff · done

  Escalation: final text contains [ESCALATE] + JSON block
    → parsed → escalation_handoffs table → handoff SSE event
```

### Key design principle
Claude has exactly **one tool**: `execute_browser_task(task: str) → str`. It never queries the database directly. All reads and writes happen through a **second, independent browser agent** that drives the ShopAdmin UI with Playwright. This replicates Giga's "no APIs required" value proposition — the agent operates the same UI a human support rep would.

---

## Control Flow (main agent loop)

`backend/app/agent/loop.py :: run_agent(conversation_id, user_message)` is an async generator that yields SSE frames. Per turn:

1. **Append** the user message to in-memory conversation history (`_conversations: dict[str, list]`, keyed by client-generated UUID).
2. **RAG**: `retrieve_context(user_message)` embeds the query and pulls the top-3 policy chunks; they are appended to the system prompt for this turn.
3. **Stream loop** (`client.messages.stream`):
   - Text deltas are forwarded immediately as `text` SSE events and accumulated into `full_text`.
   - On `stop_reason == "tool_use"`: emit `status: agent_working`, log a `tool_call` event, run the browser sub-agent, log a `tool_result` event, append both the assistant tool-use block and the `tool_result` to history, and **loop again**.
   - On a normal end-of-turn text response: break out to finalization.
4. **Finalization** of a text response:
   - **Escalation path** — if `full_text` contains `[ESCALATE]`: extract the JSON handoff block, strip the raw JSON + marker from the text, persist an `EscalationHandoff` row, log `agent_escalate`, then emit `correction` (clean text), `handoff` (structured card), `status: escalated`, and `done`.
   - **Normal path** — run `verify_response(full_text, history, system)`. If it returns corrected text, emit a `correction` event (the frontend replaces what it was rendering). Then emit `done`.

### SSE event protocol
All frames are `data: {"type": <t>, "content": <c>}\n\n`.

| `type` | Meaning | Frontend effect |
|--------|---------|-----------------|
| `text` | Streamed assistant token(s) | Queued into the paced typewriter |
| `status` | `agent_working` / `escalated` | Shows the activity panel / escalation banner |
| `action_log` | One browser/tool step `{event_type, payload}` | Appended to the live `AgentActivityPanel` |
| `correction` | Full replacement text (verifier or escalation) | Stops pacing, re-renders the message from scratch |
| `handoff` | Structured escalation card | Stored for handoff display |
| `done` | Turn complete | Status → `idle` |

---

## Components

### 1. Chat page (`frontend/src/pages/Chat.tsx` → `components/chat/ChatWidget.tsx`)
- Customer-facing chat UI, mounted at `/`.
- Streams responses via `fetch` + a manual `ReadableStream` reader parsing SSE lines (`hooks/useChat.ts`).
- **Paced rendering**: incoming `text` tokens are buffered and drained at ~13 chars/sec (≈150 wpm) for a natural typewriter feel; clicking the transcript flushes the queue instantly (`skipPacing`).
- **Correction handling**: a `correction` event stops pacing, clears the displayed text, and re-types the corrected version.
- Shows `AgentActivityPanel` while `status === 'agent_working'`, a `TypingIndicator` while streaming, and an escalation banner when escalated.

### 2. Agent Activity Panel (`components/chat/AgentActivityPanel.tsx`)
- Live, collapsible feed of the agent's browser steps during a turn, built from `action_log` SSE events.
- Humanizes each event (e.g. `navigate` → "Navigated to: orders/1042", `fill_testid` → "Searched for: …").

### 3. Agent Loop (`backend/app/agent/loop.py`)
- Owns conversation history, the streaming Claude loop, tool dispatch, escalation parsing/persistence, and verifier invocation. See **Control Flow** above.
- History is **in-memory only** (process-local dict) — restarting the backend clears all conversations.

### 4. Browser Agent (`backend/app/browser/agent.py`, `actions.py`)
- Receives a natural-language task string from the main agent.
- Launches a fresh headless Chromium page at `SHOP_ADMIN_URL`.
- Runs its **own inner Claude loop** (`claude-sonnet-4-6`, ≤15 steps) with a JSON action protocol:
  `navigate` · `click_testid` · `click_text` · `fill_testid` · `done`.
- After each action it re-extracts page text (`get_page_text` pulls body text + a list of interactive elements with their `data-testid`s) and feeds it back to the model.
- Logs each step as an `agent_event` (`browser_action`, `browser_done`) tied to the conversation.
- Returns a plain-text result summary to the main loop; closes the browser when done or on step-limit.

### 5. RAG (`backend/app/rag/ingest.py`, `retrieve.py`)
- `ingest.py` (run once): chunks `knowledge/northshop_policies.md` (500-word chunks, 100-word overlap), embeds each chunk with `voyage-3-lite`, and writes them to a `documents` table (`vector(512)`). It creates the `vector` extension and rebuilds the table itself.
- `retrieve.py`: embeds the query and returns the top-3 chunks by L2 distance (`embedding <-> :query`).

### 6. Verifier (`backend/app/agent/verifier.py`)
- A separate `claude-sonnet-4-6` call made **after** the main agent produces a final text response.
- Given the system prompt, recent history, and the response, it flags exactly three violation classes:
  1. **Policy violation** (promised something the rules forbid),
  2. **Self-contradiction** (contradicts an earlier established fact),
  3. **Unverified factual claim** (specific order details never retrieved via a tool call).
- Returns `{"result":"ok"}` or `{"result":"correction","text":"…"}`. A correction replaces the user-visible message. Tuned to minimize false positives (hedged statements are not violations). Any error → treated as "ok" (fail-open).

### 7. Escalation & Handoff (`backend/app/agent/loop.py`, `models/escalation_handoff.py`)
- The agent escalates by emitting a fenced ` ```json ` handoff block immediately followed by the `[ESCALATE]` marker (format defined in the system prompt).
- The loop parses the JSON (`reason`, `customer`, `orders_reviewed`, `actions_attempted`, `sentiment`, `recommended_next_step`), persists it to `escalation_handoffs` (one row per conversation), and strips the raw block from the customer-facing text.
- The admin portal renders it as an `EscalationHandoffCard` on the relevant order page (looked up by `?conversation=<id>`).

### 8. Event Logging (`backend/app/agent/events.py`, `models/agent_event.py`)
- `log_event(conversation_id, event_type, payload)` appends an `agent_events` row.
- Event types: `tool_call`, `tool_result`, `browser_action`, `browser_done`, `agent_escalate`.
- Surfaced live in the chat (`action_log` SSE) and historically in the admin portal (`ActionLogTimeline`).

### 9. ShopAdmin Portal (`frontend/src/components/admin/*`)
- Internal-facing React app. Routes (in `App.tsx`, wrapped in `AdminLayout`):
  - `/admin` → `OrderTable` — searchable order list (search input `data-testid="customer-search"`; `@` ⇒ email filter, else name filter).
  - `/admin/orders/:id` → `OrderDetail` — customer info, items, status (`data-testid="order-status"`), and the refund flow (`issue-refund-btn` → `RefundModal` with `refund-reason-input` + `confirm-refund-btn`).
- Backed by FastAPI routes at `/admin/api/*` that read/write Postgres directly. No auth (simulates an already-logged-in session).
- The browser agent navigates this UI via the stable `data-testid` hooks; it has no knowledge of the underlying API.
- `OrderDetail` additionally renders the `EscalationHandoffCard` and `ActionLogTimeline` when a `?conversation=<id>` query param is present.
- `frontend/src/pages/ShopAdmin.tsx` is **dead code** — routing moved into `App.tsx`.

---

## Backend API Surface

| Method & path | Purpose |
|---|---|
| `POST /api/chat` | SSE chat stream (`{conversation_id, message}`) |
| `GET /admin/api/orders?name=&email=` | List/search orders |
| `GET /admin/api/orders/{id}` | Order detail (customer, items, refund) |
| `POST /admin/api/orders/{id}/refund` | Issue a refund (`{reason}`) |
| `GET /admin/api/conversations/{id}/events` | Ordered agent-event timeline |
| `GET /admin/api/conversations/{id}/handoff` | Escalation handoff (or `null`) |
| `GET /health` | Liveness probe |

CORS allows `http://localhost:5173`; Vite proxies `/api` and `/admin/api` to `http://localhost:8000`.

---

## Database Schema

```sql
customers          (id, name, email UNIQUE, created_at)
products           (id, name, price_cents, category)
orders             (id, customer_id→customers, status, total_cents, created_at)
order_items        (id, order_id→orders, product_id→products, quantity, price_cents)
refunds            (id, order_id→orders UNIQUE, amount_cents, reason, status, created_at)
documents          (id, content, embedding vector(512), metadata jsonb)   -- built by rag/ingest.py
agent_events       (id, conversation_id idx, timestamp, event_type, payload jsonb)
escalation_handoffs(id, conversation_id UNIQUE, reason, customer, orders_reviewed jsonb,
                    actions_attempted jsonb, sentiment, recommended_next_step, raw_summary, created_at)
```

Migrations: `001_initial_schema` (core commerce tables) and `002_agent_events_and_handoffs`. The `documents` table is created/managed by `rag/ingest.py`, not Alembic.

### Order statuses
`pending` → `processing` → `shipped` → `delivered` → `refunded` / `cancelled`

### Refund eligibility — policy vs. enforcement
- **Policy** (knowledge base, enforced by the agent's reasoning): status must be `delivered`, placed within 30 days, one refund per order, plus value-based escalation rules.
- **Backend enforcement** (`POST /admin/api/orders/{id}/refund`): only checks `status == "delivered"` and that no refund already exists. **It does not enforce the 30-day window** — that rule lives entirely in the policy layer and the agent. (The seed deliberately includes order #1002, delivered but 45 days old, to exercise this distinction.) On success it creates a `refunds` row and flips the order to `refunded`.

---

## Agent System Prompt (policy layer)

`backend/app/agent/prompts.py :: SYSTEM_PROMPT` — defines the agent's policies, declares the single `execute_browser_task` tool, gives explicit ShopAdmin navigation knowledge (base URL, the order-list search input, order-detail and refund `data-testid`s, and that there are no login/nav screens), and specifies the exact `[ESCALATE]` + JSON handoff format. RAG policy context is appended at runtime.

Key policies: refunds for delivered orders within 30 days; never promise what can't be executed; escalate on unresolvable issues or explicit human requests; always confirm the order number before acting; never discuss competitor pricing or internal metrics.

---

## Browser Agent Task Examples

| Customer says | Main agent calls |
|---|---|
| "Where is my order #1042?" | `execute_browser_task("Find order #1042 in ShopAdmin and return its current status and tracking info")` |
| "I want a refund on #1042" | `execute_browser_task("Check if order #1042 is eligible for a refund, then issue the refund if eligible")` |
| "Find Alice Chen's orders" | `execute_browser_task("Search the order list for customer Alice Chen and return her orders")` |

---

## Knowledge Base

File: `knowledge/northshop_policies.md`. Sections: Return & Refund Policy, Shipping & Delivery, Order Status Definitions, Damaged/Incorrect Items, Account & Order Changes, and Escalation triggers. Ingested into pgvector for RAG.

---

## Repo Structure

```
Support-Agent-Model/
├── spec.md
├── README.md
├── docker-compose.yml                 # Postgres + pgvector (pg16)
├── backend/
│   ├── pyproject.toml                 # uv-managed; deps incl. anthropic, voyageai, playwright
│   ├── uv.lock
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       └── 002_agent_events_and_handoffs.py
│   └── app/
│       ├── main.py                    # FastAPI app, CORS, router mounts, /health
│       ├── config.py                  # pydantic-settings (.env)
│       ├── database.py                # async engine, SessionLocal, Base, get_db
│       ├── models/
│       │   ├── customer.py
│       │   ├── order.py               # Product, Order, OrderItem
│       │   ├── refund.py
│       │   ├── agent_event.py
│       │   └── escalation_handoff.py
│       ├── routers/
│       │   ├── chat.py                # POST /api/chat (SSE)
│       │   └── admin.py               # /admin/api/* (orders, refund, events, handoff)
│       ├── agent/
│       │   ├── loop.py                # main streaming loop, tool dispatch, escalation
│       │   ├── prompts.py             # SYSTEM_PROMPT (policies + portal map + handoff format)
│       │   ├── tools.py               # execute_browser_task tool schema
│       │   ├── events.py              # log_event → agent_events
│       │   └── verifier.py            # second-pass response verification
│       ├── browser/
│       │   ├── agent.py               # browser sub-agent (inner Claude loop + Playwright)
│       │   └── actions.py            # DOM text extraction + click/fill helpers
│       └── rag/
│           ├── ingest.py              # policies.md → chunks → voyage embeddings → pgvector
│           └── retrieve.py            # top-k vector similarity search
├── frontend/
│   ├── package.json
│   ├── vite.config.ts                 # proxy /api and /admin/api → :8000
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                    # React Router: /, /admin, /admin/orders/:id
│       ├── pages/
│       │   ├── Chat.tsx               # mounts ChatWidget
│       │   └── ShopAdmin.tsx          # DEAD CODE (routing moved to App.tsx)
│       ├── components/
│       │   ├── chat/
│       │   │   ├── ChatWidget.tsx
│       │   │   ├── MessageBubble.tsx
│       │   │   ├── TypingIndicator.tsx
│       │   │   └── AgentActivityPanel.tsx   # live action log
│       │   └── admin/
│       │       ├── AdminLayout.tsx
│       │       ├── OrderTable.tsx
│       │       ├── OrderDetail.tsx
│       │       ├── RefundModal.tsx
│       │       ├── ActionLogTimeline.tsx        # historical event timeline
│       │       └── EscalationHandoffCard.tsx
│       ├── hooks/
│       │   └── useChat.ts             # SSE parsing + paced typewriter rendering
│       └── types/
│           └── index.ts
├── knowledge/
│   └── northshop_policies.md
└── scripts/
    └── seed.py                        # drop/create tables + seed demo data
```

---

## Demo Data (`scripts/seed.py`)

Seeds 3 customers, 5 products, 5 orders, and their items (drops/recreates all ORM tables first).

| Order | Customer | Status | Age | Refund? |
|---|---|---|---|---|
| #1001 | Alice Chen | delivered | 5d | eligible |
| #1002 | Alice Chen | delivered | 45d | policy-ineligible (backend would still allow) |
| #1003 | Bob Martinez | shipped | 3d | no (not delivered) |
| #1004 | Carol White | processing | 1d | no |
| **#1042** | **Bob Martinez** | **delivered** | **10d** | **hero demo — eligible** |

> Note: customer #1 (Alice Chen) is seeded with email `"x"`, and order totals are stored flat rather than summed from items — fine for the demo, not production-accurate.

---

## Environment Variables

```env
# backend/.env
ANTHROPIC_API_KEY=          # main loop, browser agent, verifier (claude-sonnet-4-6)
VOYAGE_API_KEY=             # voyage-3-lite embeddings for RAG
DATABASE_URL=postgresql+asyncpg://northshop:northshop@localhost:5432/northshop
SHOP_ADMIN_URL=http://localhost:5173/admin
```

---

## Running Locally

```bash
# 1. Database
docker compose up -d

# 2. Backend (from backend/)
uv sync
uv run playwright install chromium
uv run alembic upgrade head
uv run python ../scripts/seed.py        # demo data
uv run python -m app.rag.ingest         # build the RAG index
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend (from frontend/)
npm install
npm run dev                             # http://localhost:5173
```

Customer chat: `http://localhost:5173/` · Admin portal: `http://localhost:5173/admin`.

---

## Notable Implementation Constraints (current state)

- **Conversation memory is in-process** — a backend restart drops all history.
- **No auth** anywhere (chat or admin).
- **One refund check gap**: the 30-day window is policy-only, not enforced by the refund endpoint (see schema notes).
- **Verifier and browser agent are sequential** relative to the user-visible turn; the verifier adds one extra Claude round-trip before `done`.
- `frontend/src/pages/ShopAdmin.tsx` remains as a no-op stub.

---

## Post-MVP Considerations

- **Persistent conversation store** (move `_conversations` into Postgres/Redis)
- **Screenshots / vision**: replace DOM-text extraction with Claude computer-use as a visual audit log
- **Auth**: session-based auth for ShopAdmin and the chat widget
- **Analytics dashboard**: resolution vs. escalation rate over `agent_events` / `escalation_handoffs`
- **Voice**: STT → agent → TTS, WebRTC for realtime
- **Agent Canvas**: no-code UI to edit policies and conversation flows
- **Deployment**: Docker Compose → Railway/Render for demo hosting
```
