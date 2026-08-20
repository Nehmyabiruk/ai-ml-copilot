import ast
import base64
import os
import re
import time
import uuid
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

API_URL = "https://api.github.com"


class GitHubServiceError(RuntimeError):
    pass


def validate_github_url(url: str) -> str:
    value = url.strip().rstrip("/")
    if not value:
        raise GitHubServiceError("GitHub repository URL is required.")
    parsed = value if value.startswith("http") else f"https://{value}"
    try:
        host = httpx.URL(parsed).host
    except Exception:
        host = None
    if not host or host.lower() not in {"github.com", "www.github.com"}:
        raise GitHubServiceError("Invalid GitHub repository URL. Only github.com URLs are supported.")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", value, re.IGNORECASE)
    if not match:
        raise GitHubServiceError("Invalid GitHub repository URL. Expected format: https://github.com/user/repository")
    return f"{match.group(1)}/{match.group(2)}"


def _oauth_headers(access_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "AI-ML-Copilot",
    }


def _request(
    method: str,
    path: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = httpx.request(
        method,
        f"{API_URL}{path}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        try:
            message = response.json().get("message", response.text)
        except Exception:
            message = response.text
        raise GitHubServiceError(f"GitHub API error {response.status_code}: {message}")
    return response.json() if response.content else {}


# ---------- Token refresh ----------

def refresh_access_token(refresh_token: str) -> dict[str, str]:
    """Use the refresh_token to get a new access_token."""
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        raise GitHubServiceError("GitHub OAuth credentials are not configured.")

    response = httpx.post(
        "https://github.com/login/oauth/access_token",
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-ML-Copilot",
        },
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=20,
    )

    data = response.json()
    if "error" in data:
        raise GitHubServiceError(
            f"Failed to refresh token: {data.get('error_description', data.get('error'))}"
        )

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),  # GitHub may rotate it
    }


def get_valid_access_token(installation, db: Session) -> str:
    """
    Returns a valid access_token.
    If the current one is expired, it silently refreshes it.
    """
    if not installation.access_token:
        raise GitHubServiceError("GitHub is not connected.")

    # Try a cheap call to see if the token is still valid
    try:
        _request("GET", "/user", headers=_oauth_headers(installation.access_token))
        return installation.access_token
    except GitHubServiceError as exc:
        if "401" not in str(exc) and "Bad credentials" not in str(exc):
            raise  # some other error

    # Token is expired → try to refresh
    if not installation.refresh_token:
        raise GitHubServiceError(
            "GitHub access token expired and no refresh token is available. Please reconnect GitHub."
        )

    new_tokens = refresh_access_token(installation.refresh_token)

    installation.access_token = new_tokens["access_token"]
    installation.refresh_token = new_tokens["refresh_token"]
    db.commit()

    return installation.access_token


# ---------- Public API ----------

def list_repositories(access_token: str) -> list[dict[str, Any]]:
    headers = _oauth_headers(access_token)
    repos: list[dict[str, Any]] = []
    page = 1

    while True:
        result = _request(
            "GET",
            f"/user/repos?per_page=100&page={page}&affiliation=owner,collaborator,organization_member",
            headers=headers,
        )
        if not result:
            break
        repos.extend(result)
        if len(result) < 100:
            break
        page += 1

    return repos


def download_repository_archive(
    full_name: str,
    branch: str,
    access_token: str | None = None,
) -> tempfile.TemporaryDirectory:
    headers = (
        _oauth_headers(access_token)
        if access_token
        else {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AI-ML-Copilot",
        }
    )

    response = httpx.get(
        f"{API_URL}/repos/{full_name}/tarball/{branch}",
        headers=headers,
        timeout=90,
        follow_redirects=True,
    )

    if response.status_code >= 400:
        raise GitHubServiceError(
            f"GitHub archive download failed: {response.status_code} - {response.text}"
        )

    temp = tempfile.TemporaryDirectory(prefix="copilot_github_")
    archive_path = Path(temp.name) / "repository.tar.gz"
    archive_path.write_bytes(response.content)

    with tarfile.open(archive_path, "r:gz") as archive:
        root = Path(temp.name).resolve()
        members = archive.getmembers()

        for member in members:
            member_path = (root / member.name).resolve()
            if not member_path.is_relative_to(root):
                temp.cleanup()
                raise GitHubServiceError("GitHub archive contains an unsafe path.")

        archive.extractall(root, members=members, filter="data")

    directories = [path for path in Path(temp.name).iterdir() if path.is_dir()]
    if len(directories) != 1:
        temp.cleanup()
        raise GitHubServiceError("GitHub archive has an unexpected layout.")

    return temp


def get_public_repository_info(full_name: str) -> dict[str, Any]:
    response = httpx.get(
        f"{API_URL}/repos/{full_name}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AI-ML-Copilot",
        },
        timeout=30,
    )
    if response.status_code == 404:
        raise GitHubServiceError("GitHub repository not found. Make sure the repository is public and the URL is correct.")
    if response.status_code == 403:
        raise GitHubServiceError("This repository appears to be private. Connect GitHub to access private repositories.")
    if response.status_code >= 400:
        raise GitHubServiceError(f"GitHub API error {response.status_code}: {response.text}")
    data = response.json()
    return {
        "github_repository_id": data["id"],
        "full_name": data["full_name"],
        "default_branch": data.get("default_branch") or "main",
    }


def validate_patch(file_path: str, original_code: str, fixed_code: str) -> None:
    if not file_path or file_path.startswith(("/", "\\")) or ".." in file_path.replace("\\", "/").split("/"):
        raise GitHubServiceError("Invalid repository file path.")

    if not fixed_code.strip() or len(fixed_code) > 2_000_000:
        raise GitHubServiceError("Fixed code is empty or too large.")

    if re.search(
        r"(?:BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|gh[pous]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})",
        fixed_code,
    ):
        raise GitHubServiceError("The proposed patch appears to contain a secret and cannot be pushed.")

    if file_path.lower().endswith(".py"):
        try:
            ast.parse(fixed_code)
        except SyntaxError as exc:
            raise GitHubServiceError(
                f"Python patch validation failed at line {exc.lineno}: {exc.msg}"
            ) from exc

    if fixed_code == original_code:
        raise GitHubServiceError("The proposed patch does not change the file.")


def create_repair_pull_request(
    access_token: str,
    repository: dict[str, Any],
    file_path: str,
    original_code: str,
    fixed_code: str,
    commit_message: str,
    explanation: str,
) -> dict[str, Any]:
    validate_patch(file_path, original_code, fixed_code)

    owner_repo = repository["full_name"]
    headers = _oauth_headers(access_token)
    base = repository.get("default_branch") or "main"

    base_ref = _request("GET", f"/repos/{owner_repo}/git/ref/heads/{base}", headers=headers)
    base_sha = base_ref["object"]["sha"]

    branch = f"ai-copilot/fix/{uuid.uuid4().hex[:8]}"
    _request(
        "POST",
        f"/repos/{owner_repo}/git/refs",
        headers=headers,
        payload={"ref": f"refs/heads/{branch}", "sha": base_sha},
    )

    current = _request(
        "GET",
        f"/repos/{owner_repo}/contents/{file_path}?ref={base}",
        headers=headers,
    )
    current_text = base64.b64decode(current["content"].replace("\n", "")).decode("utf-8")

    if current_text != original_code:
        raise GitHubServiceError(
            "The file changed on GitHub since this repair was generated. Re-ingest and generate a new repair."
        )

    safe_message = re.sub(r"[\r\n]+", " ", commit_message).strip()[:200] or f"fix: repair {file_path}"

    commit = _request(
        "PUT",
        f"/repos/{owner_repo}/contents/{file_path}",
        headers=headers,
        payload={
            "message": safe_message,
            "content": base64.b64encode(fixed_code.encode()).decode(),
            "sha": current["sha"],
            "branch": branch,
        },
    )

    pr = _request(
        "POST",
        f"/repos/{owner_repo}/pulls",
        headers=headers,
        payload={
            "title": f"AI Copilot: {safe_message}",
            "head": branch,
            "base": base,
            "body": (
                f"## AI Copilot Repair\n\n{explanation}\n\n"
                "### Validation\n"
                "- Patch validation: passed\n"
                "- Default branch preserved: yes"
            ),
        },
    )

    return {
        "branch_name": branch,
        "commit_sha": commit["commit"]["sha"],
        "pull_request_url": pr["html_url"],
        "pull_request_number": pr["number"],
    }