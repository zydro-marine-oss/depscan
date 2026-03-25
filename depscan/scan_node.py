import json
import os


_SKIP_SPEC_PREFIXES = (
    "file:",
    "link:",
    "workspace:",
    "portal:",
    "npm:",
)


def _should_skip_spec(spec):
    if not spec or not isinstance(spec, str):
        return True
    s = spec.strip()
    low = s.lower()
    for p in _SKIP_SPEC_PREFIXES:
        if low.startswith(p):
            return True
    if low.startswith("git+") or "github.com" in low and (".git" in low or "git+" in low):
        return True
    if low.startswith("git:"):
        return True
    if low.startswith("http://") or low.startswith("https://"):
        return True
    return False


def _merge_dep_map(target, source):
    if not isinstance(source, dict):
        return
    for name, spec in source.items():
        if not name or not isinstance(name, str):
            continue
        spec_str = spec if isinstance(spec, str) else ""
        if _should_skip_spec(spec_str):
            continue
        if name not in target:
            target[name] = spec_str


def iter_package_json_deps(repo_root):
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        if ".git" in dirs:
            dirs.remove(".git")
        if "package.json" not in files:
            continue
        path = os.path.join(root, "package.json")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        merged = {}
        _merge_dep_map(merged, data.get("dependencies"))
        _merge_dep_map(merged, data.get("devDependencies"))
        for pkg, spec in merged.items():
            rel = os.path.relpath(path, repo_root)
            yield pkg, spec or "", rel
