import textwrap

from depscan.scan_python import (
    iter_pyproject_toml_deps,
    iter_setup_py_deps,
)


def test_pyproject_pep621_and_optional(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            dependencies = ["django==4.2", "httpx>=0.24"]
            [project.optional-dependencies]
            dev = ["pytest>=7"]
            """
        ).strip(),
        encoding="utf-8",
    )
    found = set()
    for name, ver, rel in iter_pyproject_toml_deps(str(tmp_path)):
        found.add((name, ver, rel))
    assert ("django", "==4.2", "pyproject.toml") in found
    assert ("pytest", ">=7", "pyproject.toml") in found
    assert ("httpx", ">=0.24", "pyproject.toml") in found


def test_setup_py_install_requires(tmp_path):
    (tmp_path / "setup.py").write_text(
        textwrap.dedent(
            """
            from setuptools import setup
            setup(
                name="demo",
                install_requires=["numpy>=1", "scipy"],
                extras_require={"test": ["pytest"]},
            )
            """
        ).strip(),
        encoding="utf-8",
    )
    found = set()
    for name, ver, rel in iter_setup_py_deps(str(tmp_path)):
        found.add((name, ver, rel))
    assert ("numpy", ">=1", "setup.py") in found
    assert ("scipy", "", "setup.py") in found
    assert ("pytest", "", "setup.py") in found


def test_skip_poetry_path_deps(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.poetry.dependencies]
            python = "^3.9"
            requests = "^2.0"
            local = { path = "../x" }
            """
        ).strip(),
        encoding="utf-8",
    )
    names = {n for n, _, _ in iter_pyproject_toml_deps(str(tmp_path))}
    assert "requests" in names
    assert "local" not in names
    assert "python" not in names
