import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException


def parse_github_url(repository_url: str):
    parsed = urlparse(repository_url)

    if parsed.hostname not in {
        "github.com",
        "www.github.com",
    }:
        raise ValueError(
            "Only GitHub repositories are supported."
        )

    parts = parsed.path.strip("/").split("/")

    if len(parts) < 2:
        raise ValueError(
            "Invalid GitHub repository URL."
        )

    owner = parts[0]
    repository = parts[1]

    if repository.endswith(".git"):
        repository = repository[:-4]

    return owner, repository


def push_changes_to_github(
    repository_url: str,
    commit_message: str,
    changes: list[dict],
):
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not configured."
        )

    if not changes:
        raise ValueError(
            "There are no changes to commit."
        )

    temp_directory = tempfile.mkdtemp(
        prefix="ai_ml_copilot_"
    )

    try:
        askpass = Path(temp_directory) / "askpass.bat"

        askpass.write_text(
            "@echo off\n"
            "echo %GITHUB_TOKEN%\n",
            encoding="utf-8",
        )

        clone_environment = os.environ.copy()

        clone_environment[
            "GITHUB_TOKEN"
        ] = token

        clone_environment[
            "GIT_ASKPASS"
        ] = str(askpass)

        clone_environment[
            "GIT_TERMINAL_PROMPT"
        ] = "0"

        subprocess.run(
            [
                "git",
                "clone",
                repository_url,
                temp_directory,
            ],
            env=clone_environment,
            check=True,
            capture_output=True,
            text=True,
        )

        for change in changes:
            file_path = change["file_path"]
            fixed_code = change["fixed_code"]

            destination = (
                Path(temp_directory)
                / file_path
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination.write_text(
                fixed_code,
                encoding="utf-8",
            )

        subprocess.run(
            [
                "git",
                "-C",
                temp_directory,
                "config",
                "user.name",
                "AI ML Copilot",
            ],
            check=True,
        )

        subprocess.run(
            [
                "git",
                "-C",
                temp_directory,
                "config",
                "user.email",
                "ai-ml-copilot@users.noreply.github.com",
            ],
            check=True,
        )

        subprocess.run(
            [
                "git",
                "-C",
                temp_directory,
                "add",
                ".",
            ],
            check=True,
        )

        status = subprocess.run(
            [
                "git",
                "-C",
                temp_directory,
                "status",
                "--porcelain",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        if not status.stdout.strip():
            return {
                "success": False,
                "message": "No changes detected.",
            }

        subprocess.run(
            [
                "git",
                "-C",
                temp_directory,
                "commit",
                "-m",
                commit_message,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                temp_directory,
                "push",
            ],
            env=clone_environment,
            check=True,
            capture_output=True,
            text=True,
        )

        return {
            "success": True,
            "message": "Changes committed and pushed to GitHub.",
        }

    finally:
        shutil.rmtree(
            temp_directory,
            ignore_errors=True,
        )