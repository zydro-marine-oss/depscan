# depscan

Scans all projects in a GitHub org for dependencies &amp; generates a license report.

**!!! This is AI slop. Use at your own risk. !!!**

Scans one or more GitHub organizations’ repositories for **`package.json`**, **`requirements.txt`**, **`pyproject.toml`** (PEP 621 `project` / Poetry / Flit metadata), and **`setup.py`** (`install_requires` / `extras_require` via AST), resolves **registry-declared** licenses from npm and PyPI, and writes **CSV on stdout** (summarized license families) or full-detail CSV/Excel files.

This reports direct dependencies listed in those manifest files, not full transitive closure from lockfiles. Python manifests skip `node_modules`, `__pycache__`, `.git`, typical venv dirs, and Poetry/path/git URL deps that are not PyPI names.

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

`organization`, `repository`, `ecosystem` (`npm` or `pypi`), `package`, `version_spec`, `license`, `source_file` (relative path to the manifest), `lookup_error` (e.g. `not_found` or empty if resolved).

Rows are deduplicated on `(organization, repository, ecosystem, package)`; the first seen `source_file` is kept.

## Stdio format

RFC 4180-style CSV to stdout with columns:

`organization`, `project` (repository name), `source_file`, `dependency`, `license`

The `license` column is a short category (for example `MIT`, `Apache-2.0`, `GPL`, `LGPL`, `AGPL`, `BSD`, `ISC`, `MPL`, `Unknown`) derived from the registry license string, not the full legal text. Dual licenses use `/`, for example `Apache-2.0/MIT`.
