from pathlib import Path
from tempfile import TemporaryDirectory

from git import Repo


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
}


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ipynb",
}


def is_data_file(path: Path, repository_path: Path) -> bool:
    """Data assets are indexed by name only, never read or embedded."""
    return "data" in {part.lower() for part in path.relative_to(repository_path).parts[:-1]}


def clone_repository(
    repository_url: str,
) -> TemporaryDirectory:

    temporary_directory = TemporaryDirectory()

    Repo.clone_from(
        repository_url,
        temporary_directory.name,
        depth=1,
    )

    return temporary_directory


def discover_files(
    repository_path: Path,
) -> list[Path]:

    files = []

    for path in repository_path.rglob("*"):

        if not path.is_file():
            continue

        relative_parts = path.relative_to(
            repository_path
        ).parts

        if any(
            directory in IGNORED_DIRECTORIES
            for directory in relative_parts
        ):
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS and not is_data_file(path, repository_path):
            continue

        files.append(path)

    return files
