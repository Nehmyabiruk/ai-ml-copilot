import json

from pathlib import Path


def read_notebook(path: Path) -> list[dict]:

    notebook = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    chunks = []

    for index, cell in enumerate(
        notebook.get("cells", [])
    ):

        source = "".join(
            cell.get("source", [])
        ).strip()

        if not source:
            continue

        cell_type = cell.get(
            "cell_type",
            "unknown",
        )

        chunks.append(
            {
                "content": source,
                "cell_index": index,
                "cell_type": cell_type,
            }
        )

    return chunks