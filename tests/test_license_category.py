from depscan.license_category import summarize_license


def test_mit():
    assert summarize_license("MIT") == "MIT"
    assert summarize_license("MIT License") == "MIT"


def test_apache():
    assert summarize_license("Apache-2.0") == "Apache-2.0"
    assert summarize_license("Apache License, Version 2.0") == "Apache-2.0"


def test_gpl_family():
    assert summarize_license("GPL-3.0") == "GPL"
    assert summarize_license("LGPL-3.0") == "LGPL"
    assert summarize_license("AGPL-3.0") == "AGPL"


def test_dual():
    s = summarize_license("MIT OR Apache-2.0")
    assert "MIT" in s and "Apache" in s and "/" in s


def test_unknown():
    assert summarize_license("") == "Unknown"
    assert summarize_license("unknown") == "Unknown"
