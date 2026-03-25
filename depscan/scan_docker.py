import json
import os
import re
import shlex
from depscan.scan_python import _walk_repo

_RUN_PREFIX = re.compile(r"^RUN\s+", re.IGNORECASE)


def _strip_docker_comment(line):
    in_single = False
    in_double = False
    escape = False
    for i, ch in enumerate(line):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def _dockerfile_instruction_lines(content):
    accumulated = []
    for raw in content.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        ls = line.lstrip()
        if ls.startswith("#"):
            continue
        line = _strip_docker_comment(line)
        if not line.strip():
            continue
        if line.rstrip().endswith("\\"):
            frag = line.rstrip()[:-1].rstrip()
            if not accumulated:
                m0 = _RUN_PREFIX.match(frag)
                if m0:
                    frag = frag[m0.end() :].strip()
            accumulated.append(frag)
            continue
        tail = line.strip()
        if accumulated:
            m1 = _RUN_PREFIX.match(tail)
            if m1:
                tail = tail[m1.end() :].strip()
            shell = " ".join(accumulated + [tail])
            accumulated = []
            full = "RUN {}".format(shell)
        else:
            full = tail
        if full:
            yield full
    if accumulated:
        yield "RUN {}".format(" ".join(accumulated))


def _split_shell_chunks(body):
    parts = re.split(r"\s*(?:&&|\|\||;)\s*", body)
    return [p.strip() for p in parts if p.strip()]


def _apt_packages_from_tokens(tokens):
    pkgs = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("-o", "--option") and i + 1 < len(tokens):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        pkgs.append(t)
        i += 1
    return pkgs


def _parse_apt_from_chunk(chunk):
    low = chunk.lower()
    m = None
    if "apt-get" in low:
        m = re.search(r"apt-get\s+install\s+", chunk, re.IGNORECASE)
    if m is None and re.search(r"\bapt\s+install\b", chunk, re.IGNORECASE):
        m = re.search(r"\bapt\s+install\s+", chunk, re.IGNORECASE)
    if not m:
        return []
    rest = chunk[m.end() :]
    sub = _split_shell_chunks(rest)[0] if rest else ""
    if not sub.strip():
        return []
    try:
        tokens = shlex.split(sub, posix=True)
    except ValueError:
        return []
    names = _apt_packages_from_tokens(tokens)
    out = []
    for n in names:
        if "=" in n and not n.startswith("-"):
            name, _, ver = n.partition("=")
            if name:
                out.append((name, "={}".format(ver) if ver else ""))
        elif n:
            out.append((n, ""))
    return out


def normalize_git_url(url):
    u = url.strip().strip('"').strip("'")
    if u.endswith(".git"):
        u = u[:-4]
    return u


def _parse_git_clone_from_tokens(tokens):
    if not tokens:
        return None
    i = 0
    branch = ""
    while i < len(tokens):
        a = tokens[i]
        if a in ("-b", "--branch") and i + 1 < len(tokens):
            branch = tokens[i + 1]
            i += 2
            continue
        if a in ("--depth", "--shallow-since", "--shallow-exclude") and i + 1 < len(tokens):
            i += 2
            continue
        if a in (
            "--single-branch",
            "--no-single-branch",
            "--recurse-submodules",
            "--progress",
            "-v",
            "--verbose",
        ):
            i += 1
            continue
        if a.startswith("-") and a != "--":
            i += 1
            continue
        break
    if i >= len(tokens):
        return None
    url = tokens[i]
    return normalize_git_url(url), branch


def _parse_git_from_chunk(chunk):
    m = re.search(r"\bgit\s+clone\b", chunk, re.IGNORECASE)
    if not m:
        return []
    rest = chunk[m.end() :].strip()
    if not rest:
        return []
    sub = _split_shell_chunks(rest)[0] if rest else ""
    if not sub:
        return []
    try:
        tokens = shlex.split(sub, posix=True)
    except ValueError:
        return []
    parsed = _parse_git_clone_from_tokens(tokens)
    if not parsed:
        return []
    url, branch = parsed
    if not url or url.startswith("${") or "${" in url:
        return []
    return [(url, branch)]


def _parse_run_shell(line):
    m = _RUN_PREFIX.match(line)
    if not m:
        return None
    return line[m.end() :].strip()


def _try_parse_run_json_array(line):
    m = _RUN_PREFIX.match(line)
    if not m:
        return None
    rest = line[m.end() :].strip()
    if not rest.startswith("["):
        return None
    try:
        arr = json.loads(rest)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(arr, list):
        return None
    if not all(isinstance(x, str) for x in arr):
        return None
    return arr


def _apt_from_json_array(arr):
    try:
        idx = arr.index("install")
    except ValueError:
        return []
    if idx == 0:
        return []
    cmd = arr[0].lower()
    if cmd not in ("apt-get", "apt"):
        return []
    toks = arr[idx + 1 :]
    names = _apt_packages_from_tokens(toks)
    out = []
    for n in names:
        if "=" in n:
            name, _, ver = n.partition("=")
            if name:
                out.append((name, "={}".format(ver) if ver else ""))
        elif n:
            out.append((n, ""))
    return out


def _git_from_json_array(arr):
    if len(arr) < 2:
        return []
    if arr[0].lower() != "git" or arr[1].lower() != "clone":
        return []
    parsed = _parse_git_clone_from_tokens(arr[2:])
    if not parsed:
        return []
    url, branch = parsed
    if not url or url.startswith("${") or "${" in url:
        return []
    return [(url, branch)]


def _iter_from_dockerfile(path, repo_root):
    rel = os.path.relpath(path, repo_root)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return

    for logical in _dockerfile_instruction_lines(content):
        arr = _try_parse_run_json_array(logical)
        if arr is not None:
            for name, spec in _apt_from_json_array(arr):
                yield "apt", name, spec, rel
            for url, branch in _git_from_json_array(arr):
                yield "git", url, branch, rel
            continue

        body = _parse_run_shell(logical)
        if not body:
            continue
        for chunk in _split_shell_chunks(body):
            for name, spec in _parse_apt_from_chunk(chunk):
                yield "apt", name, spec, rel
            for url, branch in _parse_git_from_chunk(chunk):
                yield "git", url, branch, rel


def iter_dockerfile_deps(repo_root):
    for root, dirs, files in _walk_repo(repo_root):
        if "Dockerfile" not in files:
            continue
        path = os.path.join(root, "Dockerfile")
        for eco, pkg, spec, rel in _iter_from_dockerfile(path, repo_root):
            yield eco, pkg, spec, rel
