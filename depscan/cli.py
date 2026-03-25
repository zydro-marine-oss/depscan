import argparse
import os
import sys

from depscan import git_sync
from depscan import github_api
from depscan.custom_formatter import init_logging
from depscan import paths
from depscan import registry
from depscan import report
from depscan.scan_docker import iter_dockerfile_deps
from depscan.scan_node import iter_package_json_deps
from depscan.scan_python import iter_all_pypi_manifest_deps


def collect_discoveries(orgs, inputs_root):
    discoveries = []
    for org in orgs:
        org_path = os.path.join(inputs_root, org)
        if not os.path.isdir(org_path):
            continue
        for name in sorted(os.listdir(org_path)):
            repo_path = os.path.join(org_path, name)
            if not os.path.isdir(repo_path):
                continue
            for pkg, spec, rel in iter_package_json_deps(repo_path):
                discoveries.append((org, name, "npm", pkg, spec, rel))
            for pkg, spec, rel in iter_all_pypi_manifest_deps(repo_path):
                discoveries.append((org, name, "pypi", pkg, spec, rel))
            for eco, pkg, spec, rel in iter_dockerfile_deps(repo_path):
                discoveries.append((org, name, eco, pkg, spec, rel))
    return discoveries


def build_report_rows(discoveries, cache):
    rows = []
    for org, repo, eco, pkg, spec, rel in discoveries:
        if eco == "npm":
            lic, err = cache.npm(pkg)
        elif eco == "pypi":
            lic, err = cache.pypi(pkg)
        elif eco == "apt":
            lic, err = "unknown", "apt_not_resolved"
        elif eco == "git":
            lic, err = "unknown", "git_not_resolved"
        else:
            lic, err = "unknown", "unknown_ecosystem"
        rows.append(
            report.ReportRow(
                organization=org,
                repository=repo,
                ecosystem=eco,
                package=pkg,
                version_spec=spec,
                license=lic,
                source_file=rel,
                lookup_error=err or "",
            )
        )
    return report.dedupe_rows(rows)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(
        description="Scan GitHub org repos for dependencies and registry licenses.",
    )
    p.add_argument(
        "orgs",
        nargs="+",
        metavar="ORG",
        help="One or more GitHub organization names (each org is listed and cloned)",
    )
    p.add_argument(
        "--format",
        choices=("stdio", "csv", "excel"),
        default="stdio",
        help="Output format (default: stdio)",
    )
    p.add_argument(
        "--output",
        default="",
        help="Output file path for csv or excel (defaults: license-report.csv / .xlsx)",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug log git clone/fetch to stderr",
    )
    args = p.parse_args(argv)

    init_logging(verbose=args.verbose)

    token = github_api.resolve_token()
    inputs_root = paths.cache_root()

    if not token:
        sys.stderr.write(
            "Warning: no GITHUB_TOKEN/GH_TOKEN set; GitHub API rate limits are low.\n"
        )
    for org in args.orgs:
        try:
            repos = github_api.list_org_repos(org, token)
        except Exception as e:
            sys.stderr.write("Failed to list repos for org {}: {}\n".format(org, e))
            continue
        git_sync.sync_all_org_repos(org, repos, inputs_root, token)

    discoveries = collect_discoveries(args.orgs, inputs_root)
    cache = registry.LicenseCache()
    rows = build_report_rows(discoveries, cache)

    if args.format == "stdio":
        report.write_stdio(rows)
    elif args.format == "csv":
        out = args.output or "license-report.csv"
        report.write_csv(rows, out)
    else:
        out = args.output or "license-report.xlsx"
        report.write_excel(rows, out)

    report.emit_lookup_warnings(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
