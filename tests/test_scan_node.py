import json
import os

from depscan.scan_node import iter_package_json_deps


def test_iter_package_json_skips_node_modules(tmp_path):
    root = tmp_path / "r"
    (root / "node_modules" / "nested").mkdir(parents=True)
    bad = root / "node_modules" / "nested" / "package.json"
    bad.write_text(json.dumps({"dependencies": {"bad": "1.0.0"}}), encoding="utf-8")
    good = root / "package.json"
    good.write_text(
        json.dumps({"dependencies": {"left-pad": "^1.0.0"}, "devDependencies": {}}),
        encoding="utf-8",
    )
    found = list(iter_package_json_deps(str(root)))
    assert len(found) == 1
    assert found[0][0] == "left-pad"


def test_skips_file_protocol():
    from depscan.scan_node import _should_skip_spec

    assert _should_skip_spec("file:../foo")
    assert _should_skip_spec("workspace:*")
    assert not _should_skip_spec("^1.0.0")
