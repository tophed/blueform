from time import time

import requests 
import jwt

from .env import (
    GITHUB_ORG,
    GITHUB_APP_ID,
    GITHUB_APP_PRIVATE_KEY,
    GITHUB_APP_INSTALLATION_ID,
)

BASE_URL = "https://api.github.com"

def get_repo_zip(repo: str, ref: str):
    token = _get_access_token()
    r = requests.get(
        f"{BASE_URL}/repos/{GITHUB_ORG}/{repo}/zipball/{ref}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    r.raise_for_status()
    return r


def _get_access_token() -> str:
    now = int(time())
    app_jwt = jwt.encode(
        {
            "iat": now - 60,
            "exp": now + 60,
            "iss": GITHUB_APP_ID,
        },
        GITHUB_APP_PRIVATE_KEY,
        algorithm="RS256",
    )
    r = requests.post(
        f"{BASE_URL}/app/installations/{GITHUB_APP_INSTALLATION_ID}/access_tokens",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {app_jwt}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    return r.json()["token"]
