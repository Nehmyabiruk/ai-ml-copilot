# AI/ML Copilot

## GitHub App setup

Create a GitHub App (not an OAuth App) and configure:

- Repository permissions: **Contents: Read and write** and **Metadata: Read-only**.
- Install on selected repositories only.
- Setup URL: `http://localhost:8000/github/callback` for local development.
- Generate a private key and keep it on the backend only.

Copy `backend/.env.example` to `backend/.env` and set `GITHUB_APP_ID`, `GITHUB_APP_NAME`, and `GITHUB_PRIVATE_KEY`. Never add those values to the frontend or commit them.

## Run

```powershell
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

## Manual GitHub App test

1. Open the frontend and click **Connect GitHub**.
2. Install the App on a disposable test repository, then return to the frontend.
3. Select the repository listed by the App and ingest it.
4. Run Auto Error Scan, generate a repair, and review the before/after code.
5. Click **Approve repair**, then **Create branch & pull request**.
6. Confirm the PR targets the default branch and the change is on an `ai-copilot/fix/...` branch.

The backend validates the file path, source SHA/content, Python syntax, and common secret patterns before creating the pull request.
