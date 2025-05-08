import logging
from argparse import ArgumentParser
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def args_handler():
    parser = ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def list_highest_files(path: Path, limit: int = 10):
    """List the limit highest files in the given path."""
    files = list(safe_iter_files(path))
    files.sort(key=lambda x: x.stat().st_size, reverse=True)
    return files[:limit]


def format_size(size):
    """Format the size to a human readable format."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024:.2f} MB"
    return f"{size / 1024 / 1024 / 1024:.2f} GB"


def calc_dir_size(path: Path):
    """Calculate the size of the given directory."""
    return sum(f.stat().st_size for f in safe_iter_files(path))


def safe_iter_files(path: Path):
    """Itera recursivamente por arquivos, ignorando problemas de permissão."""
    try:
        for entry in path.iterdir():
            try:
                if entry.is_dir():
                    yield from safe_iter_files(entry)
                elif entry.is_file():
                    yield entry
            except PermissionError:
                logger.warning("Sem permissão para acessar: %s", entry)
    except PermissionError:
        logger.warning("Sem permissão para acessar: %s", path)


def main():
    args = args_handler()
    files = list_highest_files(args.path, args.limit)
    for file in files:
        print(f"{file.name} - {format_size(file.stat().st_size)}")
    print(f"Total size: {format_size(calc_dir_size(args.path))}")


if __name__ == "__main__":
    main()
