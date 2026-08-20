def chunk_code(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:

    if not text.strip():
        return []

    lines = text.splitlines()

    chunks = []

    current_lines = []
    current_length = 0

    for line in lines:

        line_length = len(line) + 1

        if (
            current_length + line_length
            > chunk_size
            and current_lines
        ):

            chunks.append(
                "\n".join(current_lines)
            )

            overlap_lines = []

            overlap_length = 0

            for previous_line in reversed(
                current_lines
            ):

                if (
                    overlap_length
                    + len(previous_line)
                    + 1
                    > overlap
                ):
                    break

                overlap_lines.insert(
                    0,
                    previous_line,
                )

                overlap_length += (
                    len(previous_line) + 1
                )

            current_lines = overlap_lines

            current_length = overlap_length

        current_lines.append(line)

        current_length += line_length

    if current_lines:
        chunks.append(
            "\n".join(current_lines)
        )

    return chunks