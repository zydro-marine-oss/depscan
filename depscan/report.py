import csv
import sys
from dataclasses import dataclass

from depscan.license_category import summarize_license

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None


@dataclass
class ReportRow:
    organization: str
    repository: str
    ecosystem: str
    package: str
    version_spec: str
    license: str
    source_file: str
    lookup_error: str

    def as_tuple(self):
        return (
            self.organization,
            self.repository,
            self.ecosystem,
            self.package,
            self.version_spec,
            self.license,
            self.source_file,
            self.lookup_error,
        )


HEADERS = (
    "organization",
    "repository",
    "ecosystem",
    "package",
    "version_spec",
    "license",
    "source_file",
    "lookup_error",
)


def dedupe_rows(rows):
    seen = set()
    out = []
    for r in rows:
        key = (r.organization, r.repository, r.ecosystem, r.package)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


STDIO_HEADERS = (
    "organization",
    "project",
    "source_file",
    "dependency",
    "license",
)


def write_stdio(rows, stream=None):
    stream = stream or sys.stdout
    w = csv.writer(stream, lineterminator="\n")
    w.writerow(STDIO_HEADERS)
    for r in rows:
        w.writerow(
            (
                r.organization,
                r.repository,
                r.source_file,
                r.package,
                summarize_license(r.license),
            )
        )


def write_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADERS)
        for r in rows:
            w.writerow(r.as_tuple())


def write_excel(rows, path):
    if Workbook is None:
        raise RuntimeError("openpyxl is required for excel output")
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for r in rows:
        ws.append(list(r.as_tuple()))
    wb.save(path)
