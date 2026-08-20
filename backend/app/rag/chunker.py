import ast
from dataclasses import dataclass


@dataclass
class CodeChunk:
    content: str
    start_line: int
    end_line: int
    symbol: str | None
    chunk_type: str


def chunk_python_code(source: str) -> list[CodeChunk]:

    tree = ast.parse(source)

    lines = source.splitlines()

    chunks: list[CodeChunk] = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            start_line = node.lineno
            end_line = node.end_lineno

            content = "\n".join(
                lines[start_line - 1:end_line]
            )

            if isinstance(node, ast.ClassDef):
                chunk_type = "class"

            elif isinstance(node, ast.AsyncFunctionDef):
                chunk_type = "async_function"

            else:
                chunk_type = "function"

            chunks.append(
                CodeChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    symbol=node.name,
                    chunk_type=chunk_type,
                )
            )

    return chunks