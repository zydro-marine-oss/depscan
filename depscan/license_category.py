import re

_UNKNOWN = "Unknown"
_OTHER = "Other"


def _norm(s):
    if not s or not isinstance(s, str):
        return ""
    return s.strip()


def _classify_fragment(low):
    if not low or low == "unknown":
        return _UNKNOWN

    if re.search(r"\bagpl\b", low) or re.search(r"affero\s+general\s+public", low):
        return "AGPL"
    if re.search(r"\blgpl\b", low) or re.search(r"lesser\s+general\s+public", low):
        return "LGPL"
    if re.search(r"\bgpl\b", low) or re.search(r"gnu\s+general\s+public", low):
        if any(
            x in low
            for x in ("lesser", "affero", "lgpl", "agpl", "gnu lesser", "gnu affero")
        ):
            pass
        else:
            return "GPL"

    if "apache" in low:
        m = re.search(r"apache[/-]([\d.]+)", low)
        if m:
            return "Apache-{}".format(m.group(1).rstrip("."))
        mv = re.search(r"version\s+([\d.]+)", low)
        if mv:
            return "Apache-{}".format(mv.group(1).rstrip("."))
        return "Apache"

    if re.search(r"\bmit\b", low) or low == "mit license" or "expat" in low:
        return "MIT"

    if "bsd" in low or "berkeley" in low:
        if "3-clause" in low or "new bsd" in low or "modified" in low:
            return "BSD-3-Clause"
        if "2-clause" in low or "simplified" in low or "freebsd" in low:
            return "BSD-2-Clause"
        return "BSD"

    if re.search(r"\bisc\b", low):
        return "ISC"

    if "mozilla" in low or re.search(r"\bmpl\b", low):
        return "MPL"

    if "unlicense" in low or "public domain" in low:
        return "Unlicense"

    if "cc0" in low:
        return "CC0"

    if "artistic" in low:
        return "Artistic"

    if re.search(r"\bepl\b", low) or "eclipse public" in low:
        return "EPL"

    if "cddl" in low:
        return "CDDL"

    if "boost" in low or "bsl" in low:
        return "BSL"

    if "zlib" in low:
        return "Zlib"

    if "wtfpl" in low:
        return "WTFPL"

    if "postgresql" in low:
        return "PostgreSQL"

    if "python software foundation" in low or re.search(r"\bpsfl\b", low):
        return "PSF"

    if "eupl" in low:
        return "EUPL"

    if "proprietary" in low or "commercial" in low or "all rights reserved" in low:
        return "Proprietary"

    if "osi approved" in low and "mit license" in low:
        return "MIT"

    return _OTHER


def _split_license_parts(text):
    parts = re.split(
        r"\s+(?:or|and)\s+|\s*/\s*",
        text,
        flags=re.IGNORECASE,
    )
    return [p.strip() for p in parts if p.strip()]


def summarize_license(raw):
    t = _norm(raw)
    if not t or t.lower() == "unknown":
        return _UNKNOWN

    fragments = _split_license_parts(t)
    if len(fragments) <= 1:
        return _classify_fragment(t.lower())

    labels = []
    seen = set()
    for frag in fragments:
        lab = _classify_fragment(frag.lower())
        if lab == _UNKNOWN and not frag:
            continue
        if lab not in seen:
            seen.add(lab)
            labels.append(lab)

    if not labels:
        return _UNKNOWN
    if len(labels) == 1:
        return labels[0]
    filtered = [x for x in labels if x != _OTHER]
    if len(filtered) == 1:
        return filtered[0]
    if filtered:
        return "/".join(sorted(filtered))
    return _OTHER
