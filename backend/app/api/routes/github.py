import os
import re
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_project_owner
from app.core.database import get_db

from app.github.service import GitHubServiceError, create_repair_pull_request,get_valid_access_token
from app.models.github import AppUser, GitHubInstallation, GitHubRepository
from app.models.project import Project

router = APIRouter(prefix="/github", tags=["GitHub OAuth"])


class RepositorySelection(BaseModel):
    repository_id: int


class RepoUrlRequest(BaseModel):
    repository_url: str


class PullRequestRequest(BaseModel):
    file_path: str
    original_code: str
    fixed_code: str
    explanation: str = "AI-generated repair"
    commit_message: str = "fix: apply AI Copilot repair"


# ---------- helpers ----------

def _get_oauth_credentials():
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(
            500,
            "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
        )
    return client_id, client_secret


def _installation_for_user(db: Session, user: AppUser) -> GitHubInstallation:
    installation = (
        db.query(GitHubInstallation)
        .filter(GitHubInstallation.user_id == user.id)
        .order_by(GitHubInstallation.id.desc())
        .first()
    )
    if not installation or not getattr(installation, "access_token", None):
        raise HTTPException(401, "GitHub is not connected. Connect GitHub first.")
    return installation


def _parse_github_repo(url_or_name: str) -> str:
    value = url_or_name.strip().rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", value, re.IGNORECASE)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        return value
    raise HTTPException(400, "Invalid GitHub repository URL or name.")


async def _exchange_code_for_token(code: str) -> dict:
    client_id, client_secret = _get_oauth_credentials()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-ML-Copilot",
            },
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
            },
        )

        data = resp.json()
        print("GitHub token response:", data)  # temporary debug

        if "error" in data:
            raise HTTPException(
                400,
                f"GitHub OAuth error: {data.get('error_description', data.get('error'))}",
            )

        if not data.get("access_token"):
            raise HTTPException(400, f"No access_token received from GitHub: {data}")

        return data


async def _get_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "AI-ML-Copilot",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        if resp.status_code != 200:
            print("GitHub /user error:", resp.status_code, resp.text)
            raise HTTPException(
                502,
                f"Failed to fetch GitHub user profile ({resp.status_code}): {resp.text}",
            )

        return resp.json()


async def _list_user_repositories(access_token: str) -> list[dict]:
    """Fetch repositories the authenticated user can access."""
    async with httpx.AsyncClient() as client:
        repos = []
        page = 1
        while True:
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "AI-ML-Copilot",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                params={
                    "per_page": 100,
                    "page": page,
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            if resp.status_code != 200:
                raise GitHubServiceError(f"Failed to list repositories: {resp.text}")

            batch = resp.json()
            if not batch:
                break

            repos.extend(batch)
            page += 1
            if len(batch) < 100:
                break

        return repos


# ---------- routes ----------

@router.get("/connect")
def connect_github(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    client_id, _ = _get_oauth_credentials()

    state = secrets.token_urlsafe(32)
    user.github_oauth_state = state
    db.commit()

    params = {
        "client_id": client_id,
        "redirect_uri": f"{os.getenv('BACKEND_URL', 'http://localhost:8000').rstrip('/')}/github/callback",
        "scope": "repo read:user",
        "state": state,
    }
    authorization_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return {"authorization_url": authorization_url}


@router.get("/callback")
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(400, f"GitHub authorization error: {error}")

    if not code or not state:
        raise HTTPException(400, "Missing code or state from GitHub")

    user = db.query(AppUser).filter(AppUser.github_oauth_state == state).first()
    if not user:
        raise HTTPException(400, "Invalid or expired state. Please try connecting again.")

    # Exchange code → access token
    token_data = await _exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(400, "Failed to obtain access token from GitHub")

    # Get GitHub user profile
   
    # Get GitHub user profile
    gh_user = await _get_github_user(access_token)

    # Clear state + save identity
    user.github_oauth_state = None
    user.github_login = gh_user.get("login")
    user.github_account_id = gh_user.get("id")

    # Store the OAuth token
    refresh_token = token_data.get("refresh_token")

    installation = (
        db.query(GitHubInstallation)
        .filter(GitHubInstallation.user_id == user.id)
        .first()
    )

    if not installation:
        installation = GitHubInstallation(
            user_id=user.id,
            account_login=gh_user.get("login", "github"),
            access_token=access_token,
            refresh_token=refresh_token,
            installation_id=0,
        )
        db.add(installation)
    else:
        installation.access_token = access_token
        installation.refresh_token = refresh_token
        installation.account_login = gh_user.get("login", "github")

    db.commit()

    frontend = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return RedirectResponse(f"{frontend}/?github=connected")


@router.get("/status")
def github_status(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = (
        db.query(GitHubInstallation)
        .filter(GitHubInstallation.user_id == user.id)
        .first()
    )
    connected = bool(installation and getattr(installation, "access_token", None))
    return {
        "connected": connected,
        "github_login": user.github_login,
        "installation_id": None,
    }



@router.get("/repositories")
async def github_repositories(
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    installation = _installation_for_user(db, user)

    try:
        access_token = get_valid_access_token(installation, db)
        repositories = await _list_user_repositories(access_token)
    except GitHubServiceError as exc:
        raise HTTPException(502, str(exc)) from exc

    result = []

    for item in repositories:
        record = (
            db.query(GitHubRepository)
            .filter(
                GitHubRepository.installation_id == installation.id,
                GitHubRepository.github_repository_id == item["id"],
            )
            .first()
        )

        if not record:
            record = GitHubRepository(
                installation_id=installation.id,
                github_repository_id=item["id"],
                full_name=item["full_name"],
                default_branch=item.get("default_branch") or "main",
            )
            db.add(record)
        else:
            record.full_name = item["full_name"]
            record.default_branch = item.get("default_branch") or "main"

        result.append(
            {
                "id": item["id"],
                "full_name": item["full_name"],
                "default_branch": item.get("default_branch") or "main",
            }
        )

    db.commit()

    return {"repositories": result}



@router.post("/projects/{project_id}/repository")
def select_project_repository(
    project_id: int,
    request: RepositorySelection,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = require_project_owner(project_id, user, db)
    installation = _installation_for_user(db, user)

    repository = (
        db.query(GitHubRepository)
        .filter(
            GitHubRepository.installation_id == installation.id,
            GitHubRepository.github_repository_id == request.repository_id,
        )
        .first()
    )
    if not repository:
        raise HTTPException(403, "This repository is not authorized.")

    project.github_repository_id = repository.id
    project.repository_url = f"https://github.com/{repository.full_name}.git"
    db.commit()

    return {
        "repository": {
            "id": repository.github_repository_id,
            "full_name": repository.full_name,
        }
    }


@router.post("/projects/{project_id}/repository-by-url")
async def select_project_repository_by_url(
    project_id: int,
    body: RepoUrlRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = require_project_owner(project_id, user, db)
    installation = _installation_for_user(db, user)

    full_name = _parse_github_repo(body.repository_url)

    try:
        repositories = await _list_user_repositories(installation.access_token)
    except GitHubServiceError as exc:
        raise HTTPException(502, str(exc)) from exc

    match = next(
        (r for r in repositories if r["full_name"].lower() == full_name.lower()),
        None,
    )
    if not match:
        raise HTTPException(
            403,
            f"Repository '{full_name}' is not accessible with the connected GitHub account.",
        )

    record = (
        db.query(GitHubRepository)
        .filter(
            GitHubRepository.installation_id == installation.id,
            GitHubRepository.github_repository_id == match["id"],
        )
        .first()
    )
    if not record:
        record = GitHubRepository(
            installation_id=installation.id,
            github_repository_id=match["id"],
            full_name=match["full_name"],
            default_branch=match.get("default_branch") or "main",
        )
        db.add(record)
    else:
        record.full_name = match["full_name"]
        record.default_branch = match.get("default_branch") or "main"

    db.flush()
    project.github_repository_id = record.id
    project.repository_url = f"https://github.com/{record.full_name}.git"
    db.commit()

    return {
        "repository": {
            "id": record.github_repository_id,
            "full_name": record.full_name,
        }
    }


@router.post("/projects/{project_id}/pull-request")
def create_pull_request(
    project_id: int,
    request: PullRequestRequest,
    user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = require_project_owner(project_id, user, db)
    if not project.github_repository:
        raise HTTPException(400, "Connect GitHub to create a Pull Request.")

    repository = project.github_repository
    installation = repository.installation
    if installation.user_id != user.id:
        raise HTTPException(403, "Repository access is not authorized for this user.")
    if not installation.access_token:
        raise HTTPException(400, "Connect GitHub to create a Pull Request.")

    try:
        return create_repair_pull_request(
            access_token=installation.access_token,
            repo={
                "full_name": repository.full_name,
                "default_branch": repository.default_branch,
            },
            file_path=request.file_path,
            original_code=request.original_code,
            fixed_code=request.fixed_code,
            commit_message=request.commit_message,
            explanation=request.explanation,
        )
    except GitHubServiceError as exc:
        raise HTTPException(400, str(exc)) from exc