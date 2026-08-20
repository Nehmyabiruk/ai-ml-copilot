import hashlib

from pathlib import Path


def calculate_file_hash(
    file_path: Path,
) -> str:

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:

        while True:

            data = file.read(1024 * 1024)

            if not data:
                break

            sha256.update(data)

    return sha256.hexdigest()