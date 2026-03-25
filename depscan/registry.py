import time
from urllib.parse import quote

import requests

NPM_REGISTRY = "https://registry.npmjs.org"
PYPI_JSON = "https://pypi.org/pypi"

_MAX_LICENSE_FIELD_CHARS = 200
_MAX_LICENSE_NEWLINES = 1
_MAX_LICENSE_WORDS = 48

_LICENSE_BODY_MARKERS = (
    "permission is hereby granted",
    "the software is provided",
    "terms and conditions for use, reproduction",
    "redistributions of source code",
    "hereby grants you a",
)


def sanitize_registry_license(raw):
    if raw is None or not isinstance(raw, str):
        return "unknown", ""
    s = raw.strip()
    if not s:
        return "unknown", ""
    if len(s) > _MAX_LICENSE_FIELD_CHARS:
        return "unknown", "full_license_text"
    if s.count("\n") > _MAX_LICENSE_NEWLINES:
        return "unknown", "full_license_text"
    if len(s.split()) > _MAX_LICENSE_WORDS:
        return "unknown", "full_license_text"
    low = s.lower()
    for marker in _LICENSE_BODY_MARKERS:
        if marker in low:
            return "unknown", "full_license_text"
    return s, ""


def npm_license_from_payload(data):
    if not isinstance(data, dict):
        return None, "invalid_json"
    lic = data.get("license")
    if isinstance(lic, str) and lic.strip():
        return lic.strip(), ""
    if isinstance(lic, dict):
        t = lic.get("type")
        if isinstance(t, str) and t.strip():
            return t.strip(), ""
    vers = data.get("versions")
    if isinstance(vers, dict) and vers:
        latest = data.get("dist-tags") or {}
        tag = latest.get("latest")
        if tag and tag in vers:
            vdata = vers[tag]
            if isinstance(vdata, dict):
                vlic = vdata.get("license")
                if isinstance(vlic, str) and vlic.strip():
                    return vlic.strip(), ""
                if isinstance(vlic, dict):
                    vt = vlic.get("type")
                    if isinstance(vt, str) and vt.strip():
                        return vt.strip(), ""
    return None, "no_license_field"


def pypi_license_from_payload(data):
    if not isinstance(data, dict):
        return None, "invalid_json"
    info = data.get("info")
    if not isinstance(info, dict):
        return None, "no_info"
    lic = info.get("license")
    if isinstance(lic, str) and lic.strip():
        return lic.strip(), ""
    classifiers = info.get("classifiers") or []
    licenses = []
    if isinstance(classifiers, list):
        for c in classifiers:
            if isinstance(c, str) and c.startswith("License :: "):
                parts = c.split(" :: ")
                if len(parts) >= 3:
                    licenses.append(parts[-1].strip())
    if licenses:
        return "; ".join(licenses), ""
    return None, "no_license_field"


def _request_with_retries(session, url, max_attempts=5):
    wait = 1.0
    last_err = ""
    for attempt in range(max_attempts):
        try:
            resp = session.get(url, timeout=60)
            if resp.status_code == 404:
                return resp, ""
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = "http_{}".format(resp.status_code)
                time.sleep(wait)
                wait = min(wait * 2, 30)
                continue
            return resp, ""
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(wait)
            wait = min(wait * 2, 30)
    return None, last_err


def fetch_npm_license(package_name, session=None):
    sess = session or requests.Session()
    enc = quote(package_name, safe="@/")
    url = "{}/{}".format(NPM_REGISTRY, enc)
    resp, err = _request_with_retries(sess, url)
    if resp is None:
        return "unknown", err or "request_failed"
    if resp.status_code == 404:
        return "unknown", "not_found"
    try:
        data = resp.json()
    except ValueError:
        return "unknown", "invalid_json"
    lic, e = npm_license_from_payload(data)
    if lic:
        clean, se = sanitize_registry_license(lic)
        if se:
            return clean, se
        return clean, ""
    return "unknown", e or "no_license"


def fetch_pypi_license(project_name, session=None):
    sess = session or requests.Session()
    enc = quote(project_name, safe="")
    url = "{}/{}/json".format(PYPI_JSON, enc)
    resp, err = _request_with_retries(sess, url)
    if resp is None:
        return "unknown", err or "request_failed"
    if resp.status_code == 404:
        return "unknown", "not_found"
    try:
        data = resp.json()
    except ValueError:
        return "unknown", "invalid_json"
    lic, e = pypi_license_from_payload(data)
    if lic:
        clean, se = sanitize_registry_license(lic)
        if se:
            return clean, se
        return clean, ""
    return "unknown", e or "no_license"


class LicenseCache:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent",
            "depscan/0.1 (dependency-license scanner)",
        )
        self._npm = {}
        self._pypi = {}

    def npm(self, package):
        if package in self._npm:
            return self._npm[package]
        lic, err = fetch_npm_license(package, self.session)
        self._npm[package] = (lic, err)
        return lic, err

    def pypi(self, package):
        key = package.lower()
        if key in self._pypi:
            return self._pypi[key]
        lic, err = fetch_pypi_license(package, self.session)
        self._pypi[key] = (lic, err)
        return lic, err
