import textwrap

from depscan.scan_docker import iter_dockerfile_deps, normalize_git_url


def test_normalize_git_url_strips_git_suffix():
    assert (
        normalize_git_url("https://github.com/foo/bar.git")
        == "https://github.com/foo/bar"
    )


def test_apt_install_shell(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        textwrap.dedent(
            """
            FROM debian:bookworm
            RUN apt-get update && apt-get install -y curl git
            RUN apt-get install --no-install-recommends -y foo=1.2.3 bar
            """
        ).strip(),
        encoding="utf-8",
    )
    found = {(e, p, s) for e, p, s, _ in iter_dockerfile_deps(str(tmp_path))}
    assert ("apt", "curl", "") in found
    assert ("apt", "git", "") in found
    assert ("apt", "foo", "=1.2.3") in found
    assert ("apt", "bar", "") in found


def test_apt_continuation(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "RUN apt-get update && apt-get install -y \\\n    nano vim\n",
        encoding="utf-8",
    )
    found = {(e, p) for e, p, _, _ in iter_dockerfile_deps(str(tmp_path))}
    assert ("apt", "nano") in found
    assert ("apt", "vim") in found


def test_git_clone_shell(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        textwrap.dedent(
            """
            RUN git clone https://github.com/foo/bar.git /opt/bar
            RUN git clone -b v1.2 --depth 1 https://github.com/org/repo.git
            RUN git clone git@github.com:foo/bar.git
            """
        ).strip(),
        encoding="utf-8",
    )
    found = {(e, p, b) for e, p, b, _ in iter_dockerfile_deps(str(tmp_path))}
    assert (
        "git",
        "https://github.com/foo/bar",
        "",
    ) in found
    assert (
        "git",
        "https://github.com/org/repo",
        "v1.2",
    ) in found
    assert ("git", "git@github.com:foo/bar", "") in found


def test_apt_json_run(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        'RUN ["apt-get", "install", "-y", "curl"]\n',
        encoding="utf-8",
    )
    found = {(e, p) for e, p, _, _ in iter_dockerfile_deps(str(tmp_path))}
    assert ("apt", "curl") in found


def test_git_json_run(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        textwrap.dedent(
            """
            RUN ["git", "clone", "-b", "main", "https://github.com/a/b.git", "/src"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    found = list(iter_dockerfile_deps(str(tmp_path)))
    assert len(found) == 1
    assert found[0][0] == "git"
    assert found[0][1] == "https://github.com/a/b"
    assert found[0][2] == "main"


def test_no_false_positive_without_git_clone(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "RUN wget https://example.com/git-clone-tool.tar.gz\n",
        encoding="utf-8",
    )
    found = list(iter_dockerfile_deps(str(tmp_path)))
    assert not any(e == "git" for e, _, _, _ in found)
