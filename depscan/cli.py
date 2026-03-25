import argparse
import logging
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
    log = logging.getLogger("depscan")
    total_d = len(discoveries)
    log.info(
        "Resolving licenses for {} dependency row(s); registry calls may take several minutes.".format(
            total_d
        )
    )
    progress_every = max(100, total_d // 20) if total_d > 200 else 50
    for idx, (org, repo, eco, pkg, spec, rel) in enumerate(discoveries, start=1):
        if eco == "npm":
            lic, err = cache.npm(pkg)
        elif eco == "pypi":
            lic, err = cache.pypi(pkg)
        elif eco == "apt":
            lic, err = "unknown", ""
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
        if total_d and (idx % progress_every == 0 or idx == total_d):
            log.info(
                "License progress: {}/{} ({:.0f}%)".format(
                    idx, total_d, 100.0 * idx / total_d
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
        help="DEBUG on stderr (git, caches); default is INFO progress",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only warnings and errors on stderr (no progress INFO)",
    )
    args = p.parse_args(argv)

    if args.verbose and args.quiet:
        sys.stderr.write("Ignoring --quiet because --verbose was set.\n")
        args.quiet = False
    init_logging(verbose=args.verbose, quiet=args.quiet)

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

    _log = logging.getLogger("depscan")
    _log.info("Clone/sync finished; scanning cloned trees under {}.".format(inputs_root))
    discoveries = collect_discoveries(args.orgs, inputs_root)
    _log.info("Collected {} raw dependency discovery row(s).".format(len(discoveries)))
    cache = registry.LicenseCache()
    rows = build_report_rows(discoveries, cache)
    _log.info(
        "Deduplicated to {} row(s); writing {} report.".format(
            len(rows), args.format
        )
    )

    if args.format == "stdio":
        report.write_stdio(rows)
    elif args.format == "csv":
        out = args.output or "license-report.csv"
        report.write_csv(rows, out)
    else:
        out = args.output or "license-report.xlsx"
        report.write_excel(rows, out)

    _log.info("Report written; emitting lookup warnings if any.")
    report.emit_lookup_warnings(rows)
    _log.info("Done.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
