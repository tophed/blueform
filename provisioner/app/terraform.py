import json
from os import path
from subprocess import Popen, PIPE, run
from typing import Any, List
from datetime import datetime
from zoneinfo import ZoneInfo

from google.cloud import firestore

from .env import TF_EXE


class Terraform:
    def __init__(self, cwd: str, **meta: Any) -> None:
        self.cwd = cwd
        self.planfile = path.join(self.cwd, "tfplan")
        self.meta = meta
        self.db = firestore.Client()

    def init(self, workspace: str | None = None):
        run([TF_EXE, "init"], cwd=self.cwd)
        if workspace:
            try:
                run([TF_EXE, "workspace", "select", workspace], cwd=self.cwd)
            except TerraformError:
                run([TF_EXE, "workspace", "new", workspace], cwd=self.cwd)

    def plan(
        self, vars: dict[str, Any] | None = None, refresh_only=False, destroy=False
    ):
        args = _get_args(vars, refresh_only, destroy)
        self.run("plan", "-json", *args, f"-out={self.planfile}")

    def apply(self):
        self.run("apply", "-json", self.planfile)

    def auto_apply(
        self, vars: dict[str, Any] | None = None, refresh_only=False, destroy=False
    ):
        args = _get_args(vars, refresh_only, destroy)
        self.run("apply", "-json", "-auto-approve", *args)

    def run(self, *args: str):
        cmd = [TF_EXE, *args]
        ref = self.db.collection('runs').document()
        ref.set({
            "timestamp": datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")),
            "args": args,
            "meta": self.meta
        })
        with Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=self.cwd) as process:
            if process.stdout:
                for line in process.stdout:
                    if "-json" in args:
                        parsed = self._write_output(ref, line)
                        print(parsed['@message'])
                    else:
                        print(line.decode())
            if process.stderr:
                for line in process.stderr:
                    if "-json" in args:
                        parsed = self._write_output(ref, line)
                        print(parsed['@message'])
                    else:
                        print(line.decode())
        if process.returncode != 0:
            raise TerraformError(cmd=cmd)

    def _write_output(self, ref: firestore.DocumentReference, output: bytes):
        parsed = json.loads(output)
        ref.collection('output').document().set(parsed)
        return parsed



class TerraformError(Exception):
    def __init__(self, cmd: List[str]) -> None:
        super().__init__(
            f"Error occured when executing Terraform command: {' '.join(cmd)}"
        )


def _get_args(
    vars: dict[str, Any] | None = None,
    refresh_only: bool = False,
    destroy: bool = False,
):
    args = []
    if refresh_only:
        args.append("-refresh-only")
    if destroy:
        args.append("-destroy")
    if vars:
        args.extend([f"-var={k}={v}" for k, v in vars.items()])
    return args
