import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.document import Document
from app.llm.client import generate_answer


def generate_repair(
    db: Session,
    project_id: int,
    file_path: str,
    issue: dict[str, Any],
) -> dict[str, Any]:

    document = (
        db.query(Document)
        .filter(
            Document.project_id == project_id,
            Document.file_path == file_path,
        )
        .first()
    )

    if document is None:
        raise ValueError(
            f"File not found: {file_path}"
        )

    prompt = f"""
You are a senior software engineer.

Repair the following REAL source file.

FILE:
{file_path}

REPORTED PROBLEM:
{json.dumps(issue, indent=2)}

CURRENT SOURCE CODE:
```text
{document.content}

Return ONLY a JSON object with these string fields:
"summary", "fixed_code". "fixed_code" must contain the complete repaired file.
"""

    answer = generate_answer(
        system_prompt="You return precise, safe source code repairs as valid JSON only.",
        user_prompt=prompt,
    )
    try:
        cleaned = answer.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", cleaned)
        result = json.loads(cleaned)
        fixed_code = result.get("fixed_code")
        if not isinstance(fixed_code, str) or not fixed_code.strip():
            raise ValueError("The model did not return repaired code")
        summary = result.get("summary", "Generated a repair based on the reported error.")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError(f"The repair model returned an invalid response: {exc}") from exc

    return {
        "file_path": document.file_path,
        "original_code": document.content,
        "fixed_code": fixed_code,
        "summary": summary,
    }
