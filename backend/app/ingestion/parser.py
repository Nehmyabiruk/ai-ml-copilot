import json
from pathlib import Path


def parse_file(
    file_path: Path,
) -> str:

    if file_path.suffix.lower() == ".ipynb":
        return parse_notebook(file_path)

    return file_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def parse_notebook(
    file_path: Path,
) -> str:

    notebook = json.loads(
        file_path.read_text(
            encoding="utf-8"
        )
    )

    parts = []

    for cell in notebook.get(
        "cells",
        []
    ):

        source = "".join(
            cell.get(
                "source",
                []
            )
        )

        if not source.strip():
            continue

        cell_type = cell.get(
            "cell_type",
            "unknown",
        )

        parts.append(
            f"# {cell_type}\n{source}"
        )

    return "\n\n".join(parts)
