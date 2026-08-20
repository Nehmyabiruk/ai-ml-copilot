# Frontend — AI/ML Copilot Engine

React + Vite + Tailwind CSS frontend for the AI/ML Copilot Engine.

## Scripts

```bash
npm install
npm run dev      # Start dev server
npm run build    # Production build
npm run preview  # Preview production build
```

## Environment

- `VITE_API_URL` — Backend API base URL (defaults to `http://localhost:8000`)

## Docker

The frontend is built as a multi-stage Docker image:
1. **Builder:** Node 20 Alpine → `npm run build`
2. **Runtime:** Nginx Alpine serving static files with SPA fallback

Build arg:
```bash
docker build --build-arg VITE_API_URL=http://localhost:8000 -t ai-ml-copilot-frontend ./frontend
```
