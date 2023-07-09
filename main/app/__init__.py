import os
import json
from asyncio import TaskGroup
from io import BytesIO
from zipfile import ZipFile
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, request
from httpx import HTTPStatusError

from . import model
from .model import from_json
from .github import GitHubClient
from .env import STATE_BUCKET

app = Flask(__name__)


@app.route("/create_repo", methods=["POST"])
async def create_repo():
    req = from_json(model.CreateRepoRequest, request.json)
    gh = GitHubClient()
    await gh.create_repo(req.name)
    await gh.set_content(
        repo=req.name,
        branch="main",
        path="terraform.backend.gcs.tf.json",
        content=json.dumps(
            {
                "terraform": {
                    "backend": {
                        "gcs": {"bucket": STATE_BUCKET, "prefix": req.name}
                    }
                }
            },
            indent=2,
            sort_keys=True,
        ),
    )
    return jsonify(message=f"Created repo '{req.name}'"), 201


@app.route("/get_content", methods=["POST"])
async def get_content():
    req = from_json(model.GetRepoRequest, request.json)
    gh = GitHubClient()
    r = await gh.get_repo_zip(req.repo, req.sha)
    with ZipFile(BytesIO(r.content)) as zf:
        elements = [
            _element(member.filename, zf.read(member))
            for member in zf.infolist()
            if not member.is_dir()
        ]
    return jsonify(elements), 200


@app.route("/set_content", methods=["POST"])
async def set_content():
    req = from_json(model.SetContentRequest, request.json)
    gh = GitHubClient()
    branch = await gh.get_branch(repo=req.repo, name=req.branch)
    sha = branch.json()["object"]["sha"]
    async with TaskGroup() as tg:
        for element in req.elements:
            address = element["address"]
            path = address + ".tf.json"
            body = element.get("body")
            if body is not None:
                content = _file_content(address, body)
                tg.create_task(
                    _set_content_safe(
                        gh,
                        repo=req.repo, 
                        base=req.branch, 
                        sha=sha,
                        path=path, 
                        content=content
                    )
                )
            else:
                tg.create_task(
                    _delete_content_safe(
                        gh,
                        repo=req.repo, 
                        base=req.branch, 
                        sha=sha,
                        path=path
                    )
                )
    return jsonify(message="Successfully set content"), 200


@app.errorhandler(HTTPStatusError)
def handle_http_error(e: HTTPStatusError):
    return (
        jsonify(
            message="HTTP Error",
            response=e.response.content.decode(),
            status=e.response.status_code,
        ),
        500,
    )


async def _set_content_safe(
        gh: GitHubClient, repo: str, base: str, sha: str, path: str, content: str
):
    ephemeral = uuid4().hex
    await gh.create_branch(repo=repo, name=ephemeral, sha=sha)
    await gh.set_content(repo=repo, path=path, branch=ephemeral, content=content)
    await gh.merge_branch(repo=repo, head=ephemeral, base=base)
    await gh.delete_branch(repo=repo, name=ephemeral)

async def _delete_content_safe(
        gh: GitHubClient, repo: str, base: str, sha: str, path: str
):
    ephemeral = uuid4().hex
    await gh.create_branch(repo=repo, name=ephemeral, sha=sha)
    await gh.delete_content(repo=repo, path=path, branch=ephemeral)
    await gh.merge_branch(repo=repo, head=ephemeral, base=base)
    await gh.delete_branch(repo=repo, name=ephemeral)


def _element(filename: str, content: bytes):
    address = os.path.basename(filename).replace(".tf.json", "")
    keys = _address_keys(address)
    body = json.loads(content)
    for key in keys:
        body = body[key]
    return {"address": address, "body": body}


def _file_content(address: str, body: Any):
    content = {}
    child = content
    keys = _address_keys(address)
    last = len(keys) - 1
    for i, key in enumerate(keys):
        if i == last:
            child[key] = body
        else:
            child[key] = {}
            child = child[key]
    return json.dumps(content, indent=2, sort_keys=True)


def _address_keys(address: str):
    return address.split(".")
