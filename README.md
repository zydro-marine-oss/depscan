# depscan

Scans all projects in a GitHub org for dependencies &amp; generates a license report.

**!!! This is AI slop. Use at your own risk. !!!**

Scans one or more GitHub organizations’ repositories for **`package.json`**, **`requirements.txt`**, **`pyproject.toml`** (PEP 621 `project` / Poetry / Flit metadata), **`setup.py`** (`install_requires` / `extras_require` via AST), and each **`Dockerfile`** ( **`apt`** / **`apt-get install`** and **`git clone`** in `RUN`, shell or JSON form). It resolves **registry-declared** licenses from npm and PyPI only, and writes **CSV on stdout** (summarized license families) or full-detail CSV/Excel files.

This reports direct dependencies listed in those manifest files, not full transitive closure from lockfiles. Python manifests skip `node_modules`, `__pycache__`, `.git`, typical venv dirs, and Poetry/path/git URL deps that are not PyPI names.

**Dockerfile / apt / git:** Ecosystem **`apt`** lists Debian package names; **`git`** lists clone URLs (normalized by dropping a trailing `.git`). Version pins and clone branches are still parsed from Dockerfiles but are not written to CSV/Excel. License fields are **`unknown`** with lookup tags **`apt_not_resolved`** / **`git_not_resolved`** (surfaced as stderr warnings with `source_file`). Parsing is heuristic: shell in `RUN` is not fully evaluated (variables, heredocs, and chained `git checkout` after clone may be missed).

## Setup

```bash
pip install -e .
```

For development tests:

```bash
pip install -e ".[dev]"
pytest
```

## Authentication

Set a GitHub personal access token so listing repositories and cloning stay within rate limits (and so private repos work if the token allows):

```bash
export GITHUB_TOKEN=ghp_...
```

`GH_TOKEN` is also accepted.

## Usage

```bash
depscan my-org another-org
depscan my-org --format csv --output licenses.csv
depscan my-org --format excel --output licenses.xlsx
depscan my-org --format stdio
depscan my-org --verbose   # -v: debug git clone/fetch on stderr
```

- Repositories are stored under `~/.zydro/depscan/{org}/{repo}`. If a directory is already a git checkout, the tool runs a shallow `fetch` and `reset --hard` to match the default branch; if that fails or the path is not a repo, it removes the directory and clones again.

## Output columns

CSV and Excel: `repository` (as `org-name/repo-name`), `ecosystem` (`npm`, `pypi`, `apt`, or `git`), `package`, `license` (raw registry value for npm/pypi; **`unknown`** for apt/git).

Rows are deduplicated on `(organization, repository, ecosystem, package)` internally; the first seen manifest path is used only for warnings.

After the report is written, any row with a non-empty registry `lookup_error` is logged once on stderr (with `CustomFormatter` when configured): `source_file`, `lookup_error`, plus combined repository path, ecosystem, and package. Those fields are not written to stdout or export files.

## Stdio format

RFC 4180-style CSV to stdout with columns:

`repository` (as `org/repo`), `dependency`, `license`

The `license` column is a short category (for example `MIT`, `Apache-2.0`, `GPL`, `LGPL`, `AGPL`, `BSD`, `ISC`, `MPL`, `Unknown`) derived from the registry license string, not the full legal text. Dual licenses use `/`, for example `Apache-2.0/MIT`.
