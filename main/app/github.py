from time import time
from typing import Any
from base64 import b64encode

import jwt
import requests
import httpx
import json

from .env import (
    GITHUB_ORG,
    GITHUB_APP_ID,
    GITHUB_APP_PRIVATE_KEY,
    GITHUB_APP_INSTALLATION_ID,
)


class GitHubClient:
    def __init__(self) -> None:
        self.base_url = "https://api.github.com"
        self.token = self._get_access_token()

    async def create_repo(self, name: str):
        return await self._request(
            method="POST",
            url=f"{self.base_url}/orgs/{GITHUB_ORG}/repos",
            body={
                "name": name,
                "private": True,
                "has_issues": False,
                "has_wiki": False,
                "has_projects": False,
            },
        )

    async def get_repo_zip(self, repo: str, sha: str):
        return await self._request(
            method="GET",
            url=f"{self._repo_url(repo)}/zipball/{sha}",
        )

    async def set_content(self, repo: str, path: str, branch: str, content: str):
        body = {
            "branch": branch,
            "message": f"set {path}",
            "content": b64encode(content.encode()).decode(),
        }
        r = await self._request(
            method="GET",
            url=f"{self._repo_url(repo)}/contents/{path}",
            params={"ref": branch},
            raise_for_status=False,
        )
        if r.status_code == 200:
            body["sha"] = r.json()["sha"]
        elif r.status_code != 404:
            r.raise_for_status()
        r = await self._request(
            method="PUT",
            url=f"{self._repo_url(repo)}/contents/{path}",
            body=body,
            raise_for_status=False,
        )
        print("GITHUB", json.dumps(r.json(), indent=2, sort_keys=True))
        return r

    async def delete_content(self, repo: str, path: str, branch: str):
        r = await self._request(
            method="GET",
            url=f"{self._repo_url(repo)}/contents/{path}",
            params={"ref": branch},
        )
        if r.status_code == 404:
            return
        await self._request(
            method="DELETE",
            url=f"{self._repo_url(repo)}/contents/{path}",
            body={
                "branch": branch,
                "message": f"delete {path}",
                "sha": r.json()["sha"],
            },
        )

    async def get_branch(self, repo: str, name: str):
        return await self._request(
            method="GET",
            url=f"{self._repo_url(repo)}/git/ref/heads/{name}",
        )

    async def create_branch(self, repo: str, name: str, sha: str):
        return await self._request(
            method="POST",
            url=f"{self._repo_url(repo)}/git/refs",
            body={"ref": f"refs/heads/{name}", "sha": sha},
        )

    async def delete_branch(self, repo: str, name: str):
        return await self._request(
            method="DELETE",
            url=f"{self._repo_url(repo)}/git/refs/heads/{name}",
        )

    async def merge_branch(self, repo: str, base: str, head: str):
        return await self._request(
            method="POST",
            url=f"{self._repo_url(repo)}/merges",
            body={
                "base": base,
                "head": head
            }
        )

    def _repo_url(self, repo: str):
        return f"{self.base_url}/repos/{GITHUB_ORG}/{repo}"

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        raise_for_status=True,
    ):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.request(
                method=method, url=url, headers=headers, params=params, json=body
            )
        if raise_for_status:
            r.raise_for_status()
        return r

    def _get_access_token(self) -> str:
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
            f"{self.base_url}/app/installations/{GITHUB_APP_INSTALLATION_ID}/access_tokens",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {app_jwt}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        return r.json()["token"]
