# Research Agent Frontend Design

React (Vite) + Tailwind frontend for the Research Agent backend. Dark, minimal aesthetic with live SSE progress and markdown report rendering.

---

## 1. Component Structure

```
src/
├── App.tsx                 # Root layout, orchestrates TopicInput + ProgressFeed + ReportView
├── main.tsx
├── index.css               # Tailwind imports + base styles
├── components/
│   ├── TopicInput.tsx      # Centered input + search button
│   ├── ProgressFeed.tsx    # Live SSE event list (status, search, synthesis)
│   ├── ReportView.tsx      # Rendered markdown with clickable citation links
│   └── EventItem.tsx       # Single event row (icon + message)
├── hooks/
│   └── useResearchStream.ts  # SSE wiring, state, reconnection
├── api/
│   └── research.ts         # POST /research, fetch job_id
└── types/
    └── events.ts           # SSE event type definitions
```

### Component Responsibilities

| Component | Role |
|-----------|------|
| **App** | Holds `jobId`, `events`, `report`, `status`. Renders TopicInput (always), ProgressFeed (when job active), ReportView (when report available). |
| **TopicInput** | Controlled input, submit triggers `POST /research` → opens SSE. Disabled while job running. |
| **ProgressFeed** | Scrollable list of `EventItem`s. Auto-scroll to bottom. Shows phase transitions, search queries, results. |
| **ReportView** | Renders markdown via `react-markdown`. Parses `[1]`, `[2]` citations and maps to URLs from events. |
| **EventItem** | Renders one event: icon by type, timestamp, human-readable message. |

---

## 2. State Model

### Job Lifecycle

```
idle → submitting → streaming → done | error
```

| State | Meaning |
|-------|---------|
| `idle` | No job. TopicInput enabled. |
| `submitting` | POST in flight. TopicInput disabled. |
| `streaming` | SSE connected. Events arriving. ProgressFeed visible. |
| `done` | `done` event received. Report shown. TopicInput enabled for new search. |
| `error` | `error` event or connection failure. Error message shown. TopicInput enabled. |

### State Shape

```ts
interface ResearchState {
  status: 'idle' | 'submitting' | 'streaming' | 'done' | 'error';
  jobId: string | null;
  topic: string;
  events: StreamEvent[];
  report: string | null;
  error: string | null;
  citations: Map<number, string>;  // citation_id → url
}
```

### Event List

Each SSE event is parsed and stored as:

```ts
type StreamEvent =
  | { event: 'status'; timestamp: string; phase: string; message: string }
  | { event: 'search_started'; timestamp: string; query: string }
  | { event: 'search_result'; timestamp: string; citation_id: number; title: string; url: string; snippet: string; score?: number }
  | { event: 'synthesis_started'; timestamp: string }
  | { event: 'final_report'; timestamp: string; report: string }
  | { event: 'error'; timestamp: string; message: string }
  | { event: 'done'; timestamp: string };
```

`search_result` events populate `citations` for ReportView link mapping.

---

## 3. SSE Wiring

### EventSource Usage

```ts
const url = `${API_BASE}/api/v1/research/${jobId}/stream`;
const es = new EventSource(url);
```

### Event Listeners

| Event Type | Handler |
|------------|---------|
| `status` | Append to events, update phase display |
| `search_started` | Append "Searching: {query}" |
| `search_result` | Append result, add to `citations` map |
| `synthesis_started` | Append "Synthesizing report..." |
| `final_report` | Store `report`, append event |
| `error` | Set `error` state, close EventSource |
| `done` | Close EventSource, set status `done` |

### Message Parsing

SSE `data` is JSON. Parse and dispatch by `event` field:

```ts
es.addEventListener('status', (e) => { const d = JSON.parse(e.data); appendEvent(d); });
es.addEventListener('search_started', ...);
// ... etc for each event type
```

**Generic fallback**: Use `es.onmessage` for events without a named listener, or register all known event names explicitly.

### Reconnection Behavior

- **Default**: `EventSource` auto-reconnects when connection drops. Use `Last-Event-ID` if backend supports it (FastAPI streaming typically does not persist; reconnection may restart stream).
- **Recommendation**: Do **not** auto-reconnect on `done` or `error`—close and clean up. On unexpected disconnect (network error), show "Connection lost" and allow user to retry (new search).
- **Cleanup**: `es.close()` in `done`/`error` handlers and on component unmount.

### Error Handling

- `es.onerror`: Connection failed. Set `error`, close, set status `error`.
- `error` event from server: Set `error` from `data.message`, close, set status `error`.
- 404 on stream URL: Job not found. Set error, stop.

---

## 4. Styling Approach

### Tailwind Setup

- `tailwindcss` v4 or v3 with `content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"]`
- Dark theme: `dark` class on `html` or `bg-zinc-950` base

### Typography Plugin

```bash
npm i @tailwindcss/typography
```

```js
// tailwind.config.js
plugins: [require('@tailwindcss/typography')],
```

Use `prose prose-invert prose-zinc` for markdown content in ReportView. Tune with `prose-headings:font-semibold`, `prose-a:text-sky-400 hover:text-sky-300`.

### Key Classes

| Element | Classes |
|---------|---------|
| Page background | `bg-zinc-950 min-h-screen` |
| Container | `max-w-3xl mx-auto px-6 py-12` |
| Topic input | `bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500` |
| Search button | `bg-amber-600 hover:bg-amber-500 text-zinc-950 font-medium px-6 py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed` |
| Progress feed | `bg-zinc-900/50 rounded-lg border border-zinc-800 max-h-80 overflow-y-auto` |
| Event item | `flex gap-3 py-2 px-3 border-b border-zinc-800/50 last:border-0 text-sm` |
| Report container | `prose prose-invert prose-zinc max-w-none mt-8` |
| Citation link | `text-amber-400 hover:text-amber-300 no-underline` |

### Dark Minimal Palette

- Background: `zinc-950`, `zinc-900`
- Text: `zinc-100`, `zinc-400`
- Accent: `amber-500`, `amber-600`
- Borders: `zinc-800`, `zinc-700`

---

## 5. Markdown Rendering

### Recommended Library: `react-markdown`

```bash
npm i react-markdown
```

- Renders markdown to React elements
- Supports `remark-gfm` for GitHub Flavored Markdown (tables, strikethrough, autolinks)
- Custom `components` prop for citation links

### Citation Link Handling

Report uses `[1]`, `[2]` inline. Two approaches:

1. **Preprocess**: Replace `\[(\d+)\]` with `<a href="{url}">[$1]</a>` before passing to react-markdown (use `dangerouslySetInnerHTML` or a custom remark plugin).
2. **Custom component**: Use `remark`/`rehype` plugin to transform citation nodes into links.

**Simpler approach**: Use `remark-gfm` and a custom `components` for `text` to detect `[N]` and render as links when `citations.get(N)` exists. Or use `rehype` plugin:

```ts
// rehype plugin: replace [1], [2] with links
function rehypeCitations(citations: Map<number, string>) {
  return (tree) => {
    visit(tree, 'text', (node) => {
      const match = node.value.match(/\[(\d+)\]/g);
      if (match) {
        // Split and create link nodes
      }
    });
  };
}
```

**Alternative**: Use `react-markdown` with `remarkPlugins` and `rehypePlugins` for custom parsing. Or preprocess the report string: replace `[1]` with `[1](url)` and let react-markdown handle links natively.

### Dependencies

```json
{
  "react-markdown": "^9.x",
  "remark-gfm": "^4.x"
}
```

---

## 6. Vite Dev Proxy

Proxy `/api` to the FastAPI backend during development:

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // FastAPI default
        changeOrigin: true,
      },
    },
  },
});
```

- Frontend: `fetch('/api/v1/research', ...)` and `EventSource('/api/v1/research/123/stream')` work without CORS.
- Production: Use same origin or configure API base URL via env.

---

## 7. API Base URL

```ts
const API_BASE = import.meta.env.VITE_API_BASE || '';
```

- Dev: `''` (relative, proxy handles `/api`)
- Prod: `''` if same origin, or `https://api.example.com` if deployed separately
