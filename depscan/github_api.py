import os
import requests


GITHUB_API = "https://api.github.com"


def resolve_token():
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def list_org_repos(org, token, session=None):
    sess = session or requests.Session()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer {}".format(token)
    repos = []
    page = 1
    per_page = 100
    while True:
        url = "{}/orgs/{}/repos".format(GITHUB_API, org)
        resp = sess.get(
            url,
            headers=headers,
            params={"per_page": per_page, "page": page, "type": "all"},
            timeout=60,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return repos
