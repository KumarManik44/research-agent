# Research Agent Frontend

React (Vite) + Tailwind frontend for the Research Agent backend.

## Setup

```bash
npm install
```

## Development

Start the backend (FastAPI) on port 8000, then:

```bash
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Build

```bash
npm run build
```

## Environment

- `VITE_API_BASE` — API base URL (default: `''` for same-origin/proxy)
