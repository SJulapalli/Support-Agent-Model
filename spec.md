# NorthShop Support Agent — Project Spec

## Overview

A replica of Giga's (GigaML) enterprise AI support agent, built for portfolio demonstration. The agent resolves customer support tickets autonomously by controlling a browser — no direct API calls to the backend from the agent. The hero demo: a customer requests a refund, the agent navigates the internal ShopAdmin portal, looks up the order, and processes the refund end-to-end without human intervention.

---

## Goals

- Demonstrate a full-stack, production-shaped AI agent
- Showcase browser-based task execution (Giga's core differentiator)
- Complete and demoable within 2 weeks for job applications

---

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| LLM | Claude (Anthropic) | Prompt engineering only, no fine-tuning |
| Agent model | `claude-opus-4-8` | Main agent loop |
| Cheap routing | `claude-haiku-4-5-20251001` | Classification, intent detection |
| Backend | Python + FastAPI | Async, SSE streaming |
| Database | PostgreSQL + pgvector | Orders, customers, refunds, embeddings |
| Migrations | Alembic | |
| Browser automation | Playwright | DOM text extraction (not screenshots) |
| Frontend | React + TypeScript + Vite | |
| Monorepo | Single repo, two top-level packages | `backend/` and `frontend/` |

---

## Architecture

```
Customer
  │
  ▼
[Chat Widget]  ──SSE──▶  [Agent API /api/chat]
                               │
                        [Claude loop]
                         │        │
                    [RAG]        [execute_browser_task()]
                         │                │
                   [pgvector]       [Browser Agent]
                                         │
                                   [Playwright]
                                         │
                                  [ShopAdmin Portal]
                                         │
                                    [Postgres]
```

### Key design principle
Claude has exactly **one tool**: `execute_browser_task(task: str) → str`. It never queries the database directly. All reads and writes happen through the browser agent navigating the ShopAdmin portal. This replicates Giga's "no APIs required" value proposition.

---

## Components

### 1. Chat Widget (frontend/src/pages/Chat.tsx)
- Customer-facing chat UI
- Streams Claude responses via SSE
- Shows "Agent is working..." indicator while browser task runs
- Shows escalation state when confidence is low

### 2. Agent Loop (backend/app/agent/loop.py)
- Maintains conversation history
- Calls Claude with system prompt + RAG context + conversation history
- Handles tool use: when Claude calls `execute_browser_task`, dispatches to browser agent
- Streams text tokens back to client, buffers tool calls

### 3. RAG (backend/app/rag/)
- Ingests `knowledge/northshop_policies.md` into pgvector
- On each turn: retrieves top-k relevant policy chunks
- Injects retrieved context into Claude's system prompt

### 4. Browser Agent (backend/app/browser/)
- Receives natural-language task string from Claude
- Opens Playwright Chromium session
- Navigates ShopAdmin portal
- Extracts DOM text at each step, feeds to a Claude mini-loop to decide next action
- Returns structured result (what it found / what it did) as a string
- Closes browser session after task

### 5. ShopAdmin Portal (frontend/src/pages/ShopAdmin.tsx)
- Internal-facing React app at `/admin`
- Pages: order list, order detail, refund modal
- Backed by FastAPI routes at `/admin/api/*` which read/write Postgres directly
- No auth for MVP (simulates an already-logged-in session)
- The browser agent navigates this UI — it has no knowledge of the underlying API

### 6. Escalation
- If Claude's response contains low confidence or explicit request for human
- Chat widget shows "Transferred to human support" banner
- Full conversation transcript displayed for handoff context

---

## Database Schema

```sql
customers (id, name, email, created_at)
products  (id, name, price_cents, category)
orders    (id, customer_id, status, total_cents, created_at)
order_items (id, order_id, product_id, quantity, price_cents)
refunds   (id, order_id, amount_cents, reason, status, created_at)
documents (id, content, embedding vector(1536), metadata jsonb)
```

### Order statuses
`pending` → `processing` → `shipped` → `delivered` → `refunded` / `cancelled`

### Refund eligibility rule (policy)
Orders in `delivered` status, placed within 30 days. Only one refund per order.

---

## Agent System Prompt (policy layer)

```
You are NorthShop's AI support agent. You help customers with order issues,
refunds, shipping questions, and account inquiries.

Policies:
- Refunds are available for delivered orders placed within 30 days.
- Never promise outcomes you cannot execute.
- If you cannot resolve an issue, escalate to a human agent.
- Always confirm the customer's order number before taking any action.
- Do not discuss competitor pricing or internal business metrics.

You have one tool: execute_browser_task. Use it to look up information and
take actions in the support portal. Always use it before making claims about
a specific order or customer account.
```

---

## Browser Agent Task Examples

| Customer says | Claude calls |
|---|---|
| "Where is my order #1042?" | `execute_browser_task("Find order #1042 in ShopAdmin and return its current status and tracking info")` |
| "I want a refund on #1042" | `execute_browser_task("Check if order #1042 is eligible for a refund, then issue the refund if eligible")` |
| "Change my email to x@y.com" | `execute_browser_task("Update customer email to x@y.com for the account associated with order #1042")` |

---

## Knowledge Base

File: `knowledge/northshop_policies.md`

Contents:
- Return & refund policy (30-day window, delivered orders only)
- Shipping timelines by region
- How to track an order
- What to do if an item arrives damaged
- Contact escalation paths

---

## Repo Structure

```
Support-Agent-Model/
├── spec.md
├── README.md
├── .gitignore
├── docker-compose.yml              # Postgres + pgvector
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       │   ├── customer.py
│       │   ├── order.py
│       │   └── refund.py
│       ├── routers/
│       │   ├── chat.py             # POST /api/chat (SSE)
│       │   └── admin.py            # /admin/api/* (ShopAdmin backend)
│       ├── agent/
│       │   ├── loop.py             # Claude conversation loop
│       │   ├── prompts.py          # System prompt, policies
│       │   └── tools.py            # execute_browser_task definition
│       ├── browser/
│       │   ├── agent.py            # Browser agent orchestrator
│       │   └── actions.py          # Playwright DOM helpers
│       └── rag/
│           ├── ingest.py           # Doc → chunks → embeddings → pgvector
│           └── retrieve.py         # Vector similarity search
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       │   ├── Chat.tsx            # Customer-facing chat widget
│       │   └── ShopAdmin.tsx       # Internal admin portal
│       ├── components/
│       │   ├── chat/
│       │   │   ├── ChatWidget.tsx
│       │   │   ├── MessageBubble.tsx
│       │   │   └── TypingIndicator.tsx
│       │   └── admin/
│       │       ├── OrderTable.tsx
│       │       ├── OrderDetail.tsx
│       │       └── RefundModal.tsx
│       ├── hooks/
│       │   └── useChat.ts
│       └── types/
│           └── index.ts
├── knowledge/
│   └── northshop_policies.md
└── scripts/
    └── seed.py                     # Seed Postgres with mock data
```

---

## Build Phases

### Phase 1 — Conversational core + RAG (Days 1–3)
- FastAPI app, Postgres connection, pgvector setup
- Knowledge base ingestion and retrieval
- Claude agent loop (no tools yet)
- Streaming chat endpoint (SSE)
- Basic React chat widget

### Phase 2 — ShopAdmin portal + mock data (Days 4–6)
- Postgres schema + Alembic migration
- Seed script (customers, orders, products, refunds)
- ShopAdmin React UI (order list, order detail, refund modal)
- Admin API routes backing the portal

### Phase 3 — Browser agent (Days 7–11)
- `execute_browser_task` tool definition wired into Claude loop
- Playwright browser agent: navigate ShopAdmin, extract DOM text, act
- Mini Claude loop inside the browser agent for step-by-step reasoning
- End-to-end demo: customer requests refund → agent processes it via browser

### Post-MVP
- Screenshots as visual audit log
- Agent Canvas builder UI
- Analytics dashboard (transcript logging, resolution rate)
- Voice (STT → agent → TTS)

---

## Environment Variables

```env
# backend/.env
ANTHROPIC_API_KEY=
DATABASE_URL=postgresql://northshop:northshop@localhost:5432/northshop
SHOP_ADMIN_URL=http://localhost:5173/admin
EMBEDDING_MODEL=text-embedding-3-small
```

---

## Post-MVP Considerations

- **Screenshots**: Replace DOM text with vision-based browser agent using Claude's computer use
- **Auth**: Add session-based auth to ShopAdmin (currently open for demo)
- **Voice**: Deepgram STT + ElevenLabs/Cartesia TTS, WebRTC for realtime
- **Agent Canvas**: No-code UI to edit policies and conversation flows
- **Analytics**: Transcript storage, resolution/escalation rate dashboard
- **Deployment**: Docker Compose → Railway/Render for demo hosting
