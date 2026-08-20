import json

from pathlib import Path


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

        cell_type = cell.get(
            "cell_type"
        )

        source = "".join(
            cell.get(
                "source",
                []
            )
        )

        if not source.strip():
            continue

        parts.append(
            f"# {cell_type}\n{source}"
        )

    return "\n\n".join(parts)