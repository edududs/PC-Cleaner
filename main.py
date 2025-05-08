import ctypes
import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

try:
    import pywintypes
    import win32api
    import win32con
    import win32security

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def is_admin():
    """Check if running as admin (Windows)."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def has_read_access(path):
    """Check if path is readable."""
    if os.access(str(path), os.R_OK):
        return True
    # Optional: advanced check for Windows
    if HAS_WIN32:
        try:
            sd = win32security.GetFileSecurity(
                str(path),
                win32security.OWNER_SECURITY_INFORMATION
                | win32security.DACL_SECURITY_INFORMATION,
            )
            dacl = sd.GetSecurityDescriptorDacl()
            if dacl is None:
                return True
        except Exception:
            return False
    return False


def safe_iter_files(path: Path):
    """Yield files recursively, skipping those without permission."""
    try:
        if not has_read_access(path):
            logger.warning("Sem permissão para acessar: %s", path)
            return
        for entry in path.iterdir():
            try:
                if entry.is_dir():
                    yield from safe_iter_files(entry)
                elif entry.is_file() and has_read_access(entry):
                    yield entry
            except (PermissionError, OSError) as e:
                logger.warning("Erro ao acessar %s: %s", entry, e)
    except (PermissionError, OSError) as e:
        logger.warning("Erro ao acessar %s: %s", path, e)


def list_highest_files(path: Path, limit: int = 10):
    """List the N largest files in the given path."""
    files = safe_iter_files(path)
    # Lazy: heapq.nlargest evita carregar tudo em memória
    import heapq

    return heapq.nlargest(limit, files, key=lambda x: x.stat().st_size)


def format_size(size):
    """Format size to human readable."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def calc_dir_size(path: Path):
    """Calculate total size of files in directory."""
    return sum(f.stat().st_size for f in safe_iter_files(path))


def args_handler():
    parser = ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def main():
    if os.name == "nt" and not is_admin():
        logger.warning("Not running as administrator. Some files may be inaccessible.")
    args = args_handler()
    if not args.path.exists():
        logger.error("O caminho especificado não existe: %s", args.path)
        sys.exit(1)
    logger.info("Analisando diretório: %s", args.path)
    files = list_highest_files(args.path, args.limit)
    if not files:
        logger.info("Nenhum arquivo encontrado ou permissões insuficientes.")
    else:
        logger.info("Os %d maiores arquivos:", len(files))
        for i, file in enumerate(files, 1):
            try:
                logger.info("%d. %s - %s", i, file, format_size(file.stat().st_size))
            except Exception as e:
                logger.warning("%d. %s - Erro ao obter tamanho: %s", i, file, e)
    try:
        total_size = calc_dir_size(args.path)
        logger.info("Tamanho total: %s", format_size(total_size))
    except Exception as e:
        logger.error("Erro ao calcular tamanho total: %s", e)


if __name__ == "__main__":
    main()
