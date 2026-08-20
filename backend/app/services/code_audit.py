import ast
import builtins
from typing import Any

from sqlalchemy.orm import Session

from app.models.document import Document
from app.llm.client import generate_answer


SUPPORTED_CODE_FILES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}


def get_project_code_files(
    db: Session,
    project_id: int,
) -> list[Document]:
    documents = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .all()
    )

    return [
        document
        for document in documents
        if document.file_type.lower() in SUPPORTED_CODE_FILES
    ]


def scan_python_file(
    content: str,
    file_path: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    try:
        tree = ast.parse(content)

    except SyntaxError as error:
        issues.append(
            {
                "file_path": file_path,
                "line": error.lineno or 1,
                "column": error.offset or 1,
                "severity": "error",
                "type": "syntax",
                "message": error.msg,
            }
        )

        return issues

    # A line containing only an unknown identifier parses successfully but fails
    # immediately at runtime (for example, a pasted word in a Python file).
    defined_names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined_names.add(node.name)
        elif isinstance(node, ast.Import):
            defined_names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            defined_names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)

    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name) and node.value.id not in defined_names:
            issues.append({
                "file_path": file_path,
                "line": node.lineno,
                "column": node.col_offset + 1,
                "severity": "error",
                "type": "undefined-name",
                "message": f"'{node.value.id}' is an undefined standalone expression and will raise NameError.",
            })

    return issues


def scan_project(
    db: Session,
    project_id: int,
) -> list[dict[str, Any]]:
    documents = get_project_code_files(
        db,
        project_id,
    )

    issues: list[dict[str, Any]] = []

    for document in documents:
        if document.file_type.lower() == ".py":
            issues.extend(
                scan_python_file(
                    document.content,
                    document.file_path,
                )
            )

    return issues


def analyze_project_with_llm(
    db: Session,
    project_id: int,
) -> list[dict[str, Any]]:
    documents = get_project_code_files(
        db,
        project_id,
    )

    results: list[dict[str, Any]] = []

    for document in documents:
        if not document.content.strip():
            continue

        prompt = f"""
You are an expert senior software engineer performing a
real code audit.

Analyze this file for:

1. Syntax errors
2. Runtime errors
3. Incorrect API usage
4. Incorrect imports
5. SQLAlchemy problems
6. FastAPI problems
7. Logic bugs
8. Security problems
9. Incorrect type usage
10. Obvious bugs that will break execution

Do NOT invent problems.

Only report a problem if you can identify a concrete reason.

File:

PATH:
{document.file_path}

CONTENT:
{document.content}
"""

        answer = generate_answer(
            system_prompt=prompt,
            user_prompt="Please perform the audit now.",
        )

        results.append(
            {
                "file_path": document.file_path,
                "audit": answer,
            }
        )

    return results
