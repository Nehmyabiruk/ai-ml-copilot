# AI/ML Copilot Engine - Docker Deployment

This project can be deployed for free using Docker on platforms like **Render**, **Railway**, or **Fly.io**.

## Prerequisites

- Docker and Docker Compose installed locally
- A PostgreSQL database with pgvector extension (or use the included Docker Compose setup)
- API keys for LLM and embedding services

## Quick Start with Docker Compose

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd ai-ml-copilot
```

### 2. Configure environment variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
# Database
POSTGRES_USER=copilot
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=ai_ml_copilot

# LLM Configuration (choose one provider)
OPENROUTER_API_KEY=<your-openrouter-key>
OPENROUTER_MODEL=openrouter/free

# Or use OpenAI directly:
# LLM_API_KEY=<your-openai-key>
# LLM_MODEL=gpt-4o-mini
# EMBEDDING_MODEL=text-embedding-3-small

# Frontend URL (your domain)
FRONTEND_URL=https://your-app.onrender.com
```

### 3. Start the stack

```bash
docker compose up --build
```

This starts:
- **PostgreSQL + pgvector** on port 5432
- **Backend API** on port 8000
- **Frontend** on port 80

### 4. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 5. Access the app

- Frontend: http://localhost
- API docs: http://localhost:8000/docs

## Free Hosting Options

### Option 1: Render (Recommended for Free Tier)

1. Push your code to GitHub
2. Create a new **Web Service** on Render
3. Connect your repo and set:
   - **Build Command**: `docker compose build`
   - **Start Command**: `docker compose up`
4. Add environment variables from `.env.example`
5. Add a **PostgreSQL** database with pgvector extension
6. Deploy!

### Option 2: Railway

1. Push code to GitHub
2. Create new project on Railway
3. Use the `railway.json` or deploy via Docker Compose
4. Railway will auto-detect and deploy

### Option 3: Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app
fly launch

# Set secrets
fly secrets set OPENROUTER_API_KEY=<your-key>
fly secrets set DATABASE_URL=<your-db-url>
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string with pgvector |
| `OPENROUTER_API_KEY` | Yes* | OpenRouter API key |
| `OPENROUTER_MODEL` | No | Model name (default: `openrouter/free`) |
| `LLM_API_KEY` | Yes* | OpenAI API key (alternative to OpenRouter) |
| `LLM_MODEL` | No | OpenAI model name |
| `EMBEDDING_MODEL` | No | Embedding model name |
| `APP_ENV` | No | Set to `production` for deployment |
| `FRONTEND_URL` | No | Frontend URL for CORS |
| `GITHUB_APP_ID` | No | GitHub App ID (for PR creation) |
| `GITHUB_PRIVATE_KEY` | No | GitHub App private key |
| `GITHUB_CLIENT_ID` | No | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | No | GitHub OAuth client secret |

*At least one LLM provider must be configured.

## Production Notes

- The backend runs with **Gunicorn + Uvicorn workers** (4 workers by default)
- Database migrations run automatically via the entrypoint script
- Static assets are served by **nginx** with caching headers
- CORS is configured via `CORS_ORIGINS` environment variable

## Troubleshooting

### pgvector extension missing

If you get errors about `pgvector`, ensure your PostgreSQL image includes it:

```yaml
# In docker-compose.yml
postgres:
  image: pgvector/pgvector:pg16  # <-- Use this image
```

### Migration errors

If migrations fail on startup, run them manually:

```bash
docker compose exec backend alembic upgrade head
```

### Port conflicts

Change ports in `docker-compose.yml`:

```yaml
services:
  frontend:
    ports:
      - "8080:80"  # Change host port
  backend:
    ports:
      - "8001:8000"  # Change host port
```

## License

MIT
