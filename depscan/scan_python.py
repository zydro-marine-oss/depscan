import ast
import os
import re
import sys

from depscan.paths import safe_relpath

# PEP 508: name [extras] version; capture name and remainder (version markers)
_REQ_RE = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)(?:\[[^\]]+\])?(.*)$")

_SKIP_DIRS = frozenset(
    {
        "node_modules",
        ".git",
        "__pycache__",
        ".tox",
        "venv",
        ".venv",
    }
)


def _walk_repo(repo_root):
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        yield root, dirs, files


def _load_toml(path):
    with open(path, "rb") as f:
        if sys.version_info >= (3, 11):
            import tomllib

            return tomllib.load(f)
        import tomli

        return tomli.load(f)


def _yield_parsed_lines(lines, relpath):
    for line in lines:
        parsed = parse_requirements_line(line)
        if parsed:
            yield parsed[0], parsed[1], relpath


def _yield_pep508_strings(strings, relpath):
    if not isinstance(strings, list):
        return
    for item in strings:
        if isinstance(item, str) and item.strip():
            parsed = parse_requirements_line(item)
            if parsed:
                yield parsed[0], parsed[1], relpath


def _iter_poetry_dependency_table(table, relpath):
    if not isinstance(table, dict):
        return
    for name, spec in table.items():
        if not name or name == "python":
            continue
        version_spec = ""
        if isinstance(spec, str):
            version_spec = spec.strip()
        elif isinstance(spec, dict):
            if any(k in spec for k in ("path", "git", "url")):
                continue
            v = spec.get("version")
            if isinstance(v, str):
                version_spec = v.strip()
        else:
            continue
        if not version_spec:
            parsed = parse_requirements_line(name)
            if parsed:
                yield parsed[0], parsed[1], relpath
            continue
        line = "{} {}".format(name, version_spec).strip()
        parsed = parse_requirements_line(line)
        if parsed:
            yield parsed[0], parsed[1], relpath


def _iter_pyproject_toml_file(path, repo_root):
    try:
        data = _load_toml(path)
    except (OSError, ValueError, TypeError):
        return
    rel = safe_relpath(path, repo_root)
    project = data.get("project")
    if isinstance(project, dict):
        deps = project.get("dependencies")
        yield from _yield_pep508_strings(deps, rel)
        opt = project.get("optional-dependencies")
        if isinstance(opt, dict):
            for _group, plist in opt.items():
                yield from _yield_pep508_strings(plist, rel)

    tool = data.get("tool")
    if not isinstance(tool, dict):
        return
    poetry = tool.get("poetry")
    if isinstance(poetry, dict):
        yield from _iter_poetry_dependency_table(poetry.get("dependencies"), rel)
        legacy_dev = poetry.get("dev-dependencies")
        yield from _iter_poetry_dependency_table(legacy_dev, rel)
        group = poetry.get("group")
        if isinstance(group, dict):
            for _gname, gdata in group.items():
                if isinstance(gdata, dict):
                    yield from _iter_poetry_dependency_table(
                        gdata.get("dependencies"), rel
                    )

    flit = tool.get("flit")
    if isinstance(flit, dict):
        meta = flit.get("metadata")
        if isinstance(meta, dict):
            yield from _yield_pep508_strings(meta.get("requires"), rel)


def _ast_str_constant(elt):
    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
        return elt.value
    return None


def _ast_str_list(node):
    if isinstance(node, (ast.List, ast.Tuple)):
        out = []
        for elt in node.elts:
            s = _ast_str_constant(elt)
            if s is not None:
                out.append(s)
        return out
    return []


def _is_setup_call(node):
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Name) and f.id == "setup":
        return True
    if isinstance(f, ast.Attribute) and f.attr == "setup":
        return True
    return False


def _iter_setup_ast_keywords(tree, relpath):
    for n in ast.walk(tree):
        if not _is_setup_call(n):
            continue
        for kw in n.keywords:
            if kw.arg == "install_requires" and kw.value:
                for item in _ast_str_list(kw.value):
                    parsed = parse_requirements_line(item)
                    if parsed:
                        yield parsed[0], parsed[1], relpath
            if kw.arg == "extras_require" and isinstance(kw.value, ast.Dict):
                for val in kw.value.values:
                    if val is None:
                        continue
                    for item in _ast_str_list(val):
                        parsed = parse_requirements_line(item)
                        if parsed:
                            yield parsed[0], parsed[1], relpath


def iter_pyproject_toml_deps(repo_root):
    for root, dirs, files in _walk_repo(repo_root):
        if "pyproject.toml" not in files:
            continue
        path = os.path.join(root, "pyproject.toml")
        for triple in _iter_pyproject_toml_file(path, repo_root):
            yield triple


def iter_setup_py_deps(repo_root):
    for root, dirs, files in _walk_repo(repo_root):
        if "setup.py" not in files:
            continue
        path = os.path.join(root, "setup.py")
        rel = safe_relpath(path, repo_root)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except OSError:
            continue
        try:
            tree = ast.parse(src, filename=path)
        except SyntaxError:
            continue
        for triple in _iter_setup_ast_keywords(tree, rel):
            yield triple


def _strip_line_comment(line):
    idx = line.find("#")
    if idx >= 0:
        line = line[:idx]
    return line.strip()


def _is_vcs_or_url(line_lower):
    return (
        line_lower.startswith("-e ")
        or line_lower.startswith("--")
        or "://" in line_lower
        or line_lower.startswith("git+")
        or line_lower.startswith("hg+")
        or line_lower.startswith("svn+")
        or line_lower.startswith("bzr+")
    )


def parse_requirements_line(line):
    raw = line.strip()
    if not raw:
        return None
    stripped = _strip_line_comment(raw)
    if not stripped:
        return None
    low = stripped.lower()
    if low.startswith("-r ") or low.startswith("-c ") or low.startswith("-e "):
        return None
    if _is_vcs_or_url(low):
        return None
    if stripped.startswith("-") and not stripped.startswith("--"):
        return None
    part = stripped.split(";")[0].strip()
    part0 = part.split(",", 1)[0].strip()
    m = _REQ_RE.match(part0)
    if not m:
        return None
    name = m.group(1)
    if not name or name == ".":
        return None
    version_spec = (m.group(2) or "").strip()
    return name, version_spec


def iter_requirements_txt_deps(repo_root):
    for root, dirs, files in _walk_repo(repo_root):
        if "requirements.txt" not in files:
            continue
        path = os.path.join(root, "requirements.txt")
        rel = safe_relpath(path, repo_root)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue
        yield from _yield_parsed_lines(lines, rel)


def iter_all_pypi_manifest_deps(repo_root):
    yield from iter_requirements_txt_deps(repo_root)
    yield from iter_pyproject_toml_deps(repo_root)
    yield from iter_setup_py_deps(repo_root)
