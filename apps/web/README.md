# CrossAgent Web

Next.js 14 frontend for CrossAgent. Backend is Python FastAPI (`services/` + `api/`).

## Setup

```bash
cd apps/web
npm install
cp .env.local.example .env.local
```

## Dev

```bash
# terminal 1 — frontend
npm run dev

# terminal 2 — backend (after FastAPI is added)
# uvicorn api.main:app --reload --port 8000
```

Open http://localhost:3000

## Structure

```
src/
├── app/                 # Next.js App Router
├── components/chat/     # Chat UI
├── components/ui/       # shadcn/ui
├── hooks/useAgentChat.ts
├── lib/api.ts           # API base URL
├── lib/sse.ts           # fetch-event-source client
└── types/chat.ts        # SSE event types
```
