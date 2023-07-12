import os
from io import BytesIO
from contextlib import contextmanager
from shutil import rmtree, make_archive
from uuid import uuid4
from zipfile import ZipFile

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from google.cloud import storage

from app.terraform import Terraform, TerraformError
from app.env import TMP_DIR, PLAN_BUCKET
from app.model import (
    ApplyRequest,
    AutoApplyRequest,
    PlanRequest,
    ValidationError,
    from_json,
)
from app.github import get_repo_zip


app = Flask(__name__)
gcs = storage.Client()


@app.route("/plan", methods=["POST"])
def plan():
    with transient_directory(TMP_DIR) as td:
        req = from_json(PlanRequest, request.json)
        tfdir = os.path.join(td, "tf")
        write_configuration(tfdir, req.repo, req.ref)
        tf = Terraform(
            tfdir,
            repo=req.repo,
            sha=req.ref,
            workspace=req.workspace,
            plan_id=req.plan_id,
            **req.meta,
        )
        # TODO: decrypt vars
        tf.init(req.workspace)
        tf.plan(vars=req.vars, refresh_only=req.refresh_only, destroy=req.destroy)
        rmtree(os.path.join(tfdir, ".terraform/providers"), ignore_errors=True)
        archive = make_archive(tfdir, "zip", tfdir)
        blob = gcs.bucket(PLAN_BUCKET).blob(req.plan_id)
        blob.upload_from_filename(archive)
    return jsonify(
        message="Successfully created plan",
        plan_id=req.plan_id,
        repo=req.repo,
        ref=req.ref,
    )


@app.route("/apply", methods=["POST"])
def apply():
    req = from_json(ApplyRequest, request.json)
    blob = gcs.bucket(PLAN_BUCKET).get_blob(req.plan_id)
    if not blob:
        return jsonify(message="Plan not found", plan_id=req.plan_id), 404
    with transient_directory(TMP_DIR) as td:
        tfdir = os.path.join(td, "tf")
        archive = f"{tfdir}.zip"
        blob.download_to_filename(archive)
        with ZipFile(archive) as zf:
            zf.extractall(tfdir)
        tf = Terraform(tfdir, plan_id=req.plan_id, **req.meta)
        tf.init()
        tf.apply()
    return jsonify(message="Successfully applied plan", plan_id=req.plan_id)


@app.route("/auto-apply", methods=["POST"])
def auto_apply():
    req = from_json(AutoApplyRequest, request.json)
    with transient_directory(TMP_DIR) as td:
        tfdir = os.path.join(td, "tf")
        write_configuration(tfdir, req.repo, req.ref)
        tf = Terraform(
            tfdir,
            repo=req.repo,
            sha=req.ref,
            workspace=req.workspace,
            **req.meta,
        )
        tf.init(req.workspace)
        tf.auto_apply(vars=req.vars, refresh_only=req.refresh_only, destroy=req.destroy)
    return jsonify(message="Successfully applied")


@app.errorhandler(TerraformError)
def handle_terraform_error(e: TerraformError):
    return jsonify(message="Terraform error"), 400


@app.errorhandler(ValidationError)
def handle_validation_error(e: ValidationError):
    return jsonify(error=e.error), 400


@app.errorhandler(HTTPException)
def handle_http_error(e: HTTPException):
    return jsonify(message=str(e)), e.response.status_code if e.response else 500


@contextmanager
def transient_directory(root_dir):
    d = os.path.join(root_dir, uuid4().hex)
    os.makedirs(d)
    try:
        yield d
    finally:
        rmtree(d)


def write_configuration(path: str, repo: str, ref: str):
    os.makedirs(path)
    r = get_repo_zip(repo, ref)
    with ZipFile(BytesIO(r.content)) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            member.filename = os.path.basename(member.filename)
            zf.extract(member, path=path)
