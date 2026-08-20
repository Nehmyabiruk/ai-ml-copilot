# AI/ML Copilot Engine

> **Ingest. Audit. Repair. Chat.** — An AI-powered copilot that understands your codebase end-to-end and Fixes your Error.

AI/ML Copilot Engine lets you **paste any public GitHub repository URL**, automatically ingests it into a RAG pipeline, and gives you an intelligent assistant for **error repair**, **code auditing**, and **repository-scoped chat** — no GitHub login required.

---

## What It Does

| Feature | Description |
|---------|-------------|
| **Public Repo Ingestion** | Paste a GitHub URL → instant ingestion. No OAuth, no app installation. |
| **Auto Error Scan** | Scans the repository for syntax errors, logic bugs, security issues, and framework misuses. |
| **AI Repair** | Generates a concrete before/after fix for the selected issue. |
| **RAG Chat** | Ask questions about your repository; answers are grounded only in ingested files. |

---

## How It Works

```
User pastes GitHub URL
        │
        ▼
Backend validates URL & downloads public repo
        │
        ▼
Ingestion pipeline: clone → parse → chunk → embed → store
        │
        ▼
Repository is now the active project context
        │
        ├──▶ Fix an error (repair / audit)
        ├──▶ Ask anything (RAG chat)
        
```

---

## Tech Stack

### Backend
- **FastAPI** — async API layer
- **SQLAlchemy** — ORM with `pgvector` for vector embeddings
- **Alembic** — database migrations
- **LangChain / LangGraph** — LLM orchestration
- **OpenAI / OpenRouter** — LLM and embedding models
- **Sentence Transformers** — local embedding fallback
- **GitPython** — repository cloning and inspection
- **PostgreSQL + pgvector** — persistent vector storage

### Frontend
- **React 19** — UI
- **Vite** — build tooling
- **Tailwind CSS** — styling
- **Docker + Nginx** — production serving

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- An OpenAI or OpenRouter API key

### 1. Clone
```bash
git clone <your-repo-url>
cd ai-ml-copilot
```

### 2. Configure
```bash
cp .env.example .env
```

Edit `.env` and set at least one LLM provider:
```env
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=openrouter/free

# Or OpenAI directly:
# LLM_API_KEY=your-openai-key
# LLM_MODEL=gpt-4o-mini
# EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Start Everything
```bash
docker compose up --build
```

### 4. Run Migrations
```bash
docker compose exec backend alembic upgrade head
```

### 5. Use the App
- **Frontend:** http://localhost
- **API Docs:** http://localhost:8000/docs

---

## Usage

### Ingest a Repository
1. Paste a public GitHub URL, e.g. `https://github.com/user/repo`
2. Click **Ingest Repository**
3. Wait for ingestion to complete

### Fix an Error
1. It Automatically Scans or manually  Paste an error trace into **Fix an error in this repository**
2. Click **Generate repair**
3. Review the before/after diff


### Chat with Your Codebase
1. Type a question in the **RAG chat** box
2. Answers are retrieved only from the active repository



---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes* | OpenRouter API key |
| `LLM_API_KEY` | Yes* | OpenAI API key (alternative) |
| `OPENROUTER_MODEL` | No | Model name (default: `openrouter/free`) |
| `LLM_MODEL` | No | OpenAI model name |
| `EMBEDDING_MODEL` | No | Embedding model name |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `POSTGRES_DB` | No | Database name (default: `ml_copilot`) |

*At least one LLM provider must be configured.*

---

## Docker Deployment

The project ships with a production-ready Docker Compose stack:

```bash
docker compose up --build
docker compose exec backend alembic upgrade head
```

Services:
- **PostgreSQL + pgvector** on port `5432`
- **FastAPI backend** on port `8000`
- **Nginx frontend** on port `80`

For detailed deployment guides, see [DEPLOY.md](./DEPLOY.md).

---

## Architecture

```
frontend/
  └── React + Vite + Tailwind
      └── src/App.jsx

backend/
  ├── app/
  │   ├── main.py               # FastAPI app + CORS
  │   ├── core/
  │   │   ├── database.py        # SQLAlchemy engine + session
  │   │   └── config.py          # Settings from env vars
  │   ├── models/                # SQLAlchemy ORM models
  │   ├── schemas/               # Pydantic schemas
  │   ├── services/              # Business logic
  │   │   ├── project_service.py
  │   │   ├── code_audit.py
  │   │   └── code_repair.py
  │   ├── api/routes/            # REST endpoints
  │   │   ├── projects.py
  │   │   ├── chat.py
  │   │   ├── ingestion.py
  │   │   └── github.py
  │   ├── rag/                   # Embeddings + retrieval
  │   ├── ingestion/             # File parsing + chunking
  │   └── github/                # GitHub API + archive download
  ├── alembic/                   # Database migrations
  ├── requirements.txt
  ├── Dockerfile
  └── entrypoint.sh
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Public URL ingestion without OAuth** | Lower friction for users ingesting open-source repos |
| **Separate PR auth** | Keep ingestion fast and optional for contribution workflows |
| **pgvector in PostgreSQL** | Single database for metadata + vectors; no separate vector DB |
| **Project-scoped retrieval** | RAG chat only retrieves chunks from the active project |
| **Archive safety checks** | Prevents path traversal and unsafe extraction on repo downloads |
| **Docker multi-stage build** | Small production image; dependencies cached separately |

---

## Security

- Repository URLs are validated to be `github.com` only
- Downloaded archives are scanned for path traversal before extraction
- Patches are validated for secrets, syntax errors, and no-op changes
- GitHub tokens are stored server-side only; never exposed to the frontend

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `vector type does not exist` | Ensure `POSTGRES_DB=ml_copilot` in `.env`, then `docker compose down -v && docker compose up --build` |
| `relation "documents" does not exist` | Run `docker compose exec backend alembic upgrade head` or start fresh with `docker compose down -v` |
| `ModuleNotFoundError: sentence_transformers` | Rebuild with `docker compose build --no-cache` |
| `ERR_EMPTY_RESPONSE` on frontend | Backend is still starting; wait for `Listening at: http://0.0.0.0:8000` in logs |

---

## License

MIT
