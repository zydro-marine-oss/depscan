from depscan.paths import safe_relpath


def test_safe_relpath_under_root(tmp_path):
    root = str(tmp_path)
    f = tmp_path / "a" / "b.txt"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    rel = safe_relpath(str(f), root)
    assert rel == "a/b.txt"
    assert "\\" not in rel


def test_safe_relpath_dockerfile(tmp_path):
    root = str(tmp_path)
    sub = tmp_path / "pkg" / "Dockerfile"
    sub.parent.mkdir(parents=True)
    sub.write_text("FROM x", encoding="utf-8")
    assert safe_relpath(str(sub), root) == "pkg/Dockerfile"
