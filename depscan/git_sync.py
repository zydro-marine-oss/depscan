import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)


def _authenticated_clone_url(clone_url, token):
    if not token:
        return clone_url
    if not clone_url.startswith("https://github.com/"):
        return clone_url
    return clone_url.replace(
        "https://github.com/", "https://x-access-token:{}@github.com/".format(token),
        1,
    )


def sync_repo(clone_url, dest, default_branch, token):
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    url = _authenticated_clone_url(clone_url, token)

    def run_fetch_and_reset():
        logger.debug(
            "git fetch: dest={} branch={} url={}".format(
                dest, default_branch, clone_url
            )
        )
        fetch = subprocess.run(
            [
                "git",
                "-C",
                dest,
                "fetch",
                "--depth",
                "1",
                "origin",
                default_branch,
            ],
            capture_output=True,
            text=True,
        )
        if fetch.returncode != 0:
            return False, fetch.stderr or fetch.stdout or "git fetch failed"
        reset = subprocess.run(
            ["git", "-C", dest, "reset", "--hard", "FETCH_HEAD"],
            capture_output=True,
            text=True,
        )
        if reset.returncode != 0:
            return False, reset.stderr or reset.stdout or "git reset failed"
        return True, ""

    def run_clone():
        logger.debug(
            "git clone: dest={} branch={} url={}".format(
                dest, default_branch, clone_url
            )
        )
        clone = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                default_branch,
                url,
                dest,
            ],
            capture_output=True,
            text=True,
        )
        if clone.returncode != 0:
            return False, clone.stderr or clone.stdout or "git clone failed"
        return True, ""

    if os.path.isdir(dest):
        git_dir = os.path.join(dest, ".git")
        if os.path.isdir(git_dir):
            ok, err = run_fetch_and_reset()
            if ok:
                logger.debug("git update ok: {}".format(dest))
                return True, ""
            logger.debug("git fetch/reset failed, replacing with fresh clone: {}".format(
                (err or "").strip()
            ))
        else:
            logger.debug(
                "path is not a git repo, replacing with fresh clone: {}".format(dest)
            )
        try:
            shutil.rmtree(dest)
        except OSError as exc:
            return False, "rmtree failed: {}".format(exc)

    ok, err = run_clone()
    if ok:
        logger.debug("git clone ok: {}".format(dest))
    else:
        logger.debug("git clone failed: {}".format((err or "").strip()))
    return ok, err


def sync_all_org_repos(org, repos, inputs_root, token, err_stream=None):
    err_stream = err_stream or sys.stderr
    ok = 0
    for repo in repos:
        name = repo.get("name") or ""
        clone_url = repo.get("clone_url") or ""
        default_branch = repo.get("default_branch") or "main"
        if not name or not clone_url:
            continue
        dest = os.path.join(inputs_root, org, name)
        logger.debug(
            "sync repo {}/{} -> {} (branch={})".format(
                org, name, dest, default_branch
            )
        )
        success, message = sync_repo(clone_url, dest, default_branch, token)
        if success:
            ok += 1
        else:
            err_stream.write(
                "[{}] {} clone/update failed: {}\n".format(org, name, message.strip())
            )
    return ok, len(repos)
