from depscan.scan_python import parse_requirements_line


def test_parse_simple():
    assert parse_requirements_line("django==4.2") == ("django", "==4.2")


def test_parse_extras_stripped():
    assert parse_requirements_line("pandas[cuda]>=2") == ("pandas", ">=2")


def test_parse_comment():
    assert parse_requirements_line("numpy  # pin") == ("numpy", "")


def test_parse_env_marker():
    assert parse_requirements_line('backports.zoneinfo; python_version < "3.9"') == (
        "backports.zoneinfo",
        "",
    )


def test_skip_empty_and_includes():
    assert parse_requirements_line("") is None
    assert parse_requirements_line("   ") is None
    assert parse_requirements_line("-r other.txt") is None


def test_skip_vcs():
    assert parse_requirements_line("git+https://github.com/foo/bar.git") is None
