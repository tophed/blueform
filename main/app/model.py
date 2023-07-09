from dataclasses import dataclass
from typing import Any


class ValidationError(Exception):
    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__(error)


def from_json(cls, data: Any):
    try:
        return cls(**data)
    except TypeError as e:
        raise ValidationError(str(e))

@dataclass
class CreateRepoRequest:
    name: str


@dataclass
class GetRepoRequest:
    repo: str
    sha: str

@dataclass
class SetContentRequest:
    repo: str
    branch: str
    elements: list[dict[str, Any]]

