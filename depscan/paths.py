import os


def cache_root():
    return os.path.join(os.path.expanduser("~"), ".zydro", "depscan")


def safe_relpath(path, start):
    path_abs = os.path.normpath(os.path.abspath(path))
    start_abs = os.path.normpath(os.path.abspath(start))
    try:
        rel = os.path.relpath(path_abs, start_abs)
    except ValueError:
        rel = None
    if rel is not None:
        return rel.replace("\\", "/")
    base = start_abs.rstrip(os.sep)
    prefix = base + os.sep
    if len(path_abs) >= len(prefix) and path_abs[: len(prefix)].lower() == prefix.lower():
        out = path_abs[len(prefix) :]
    else:
        out = path_abs
    return out.replace("\\", "/")
