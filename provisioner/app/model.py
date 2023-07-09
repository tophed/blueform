from dataclasses import dataclass, field
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
class PlanRequest:
    plan_id: str
    workspace: str
    repo: str
    ref: str
    vars: Any = field(default_factory=dict)
    refresh_only: bool = False
    destroy: bool = False
    meta: dict[str, str] = field(default_factory=dict)


@dataclass
class AutoApplyRequest:
    workspace: str
    repo: str
    ref: str
    vars: dict[str, Any] = field(default_factory=dict)
    refresh_only: bool = False
    destroy: bool = False
    meta: dict[str, str] = field(default_factory=dict)


@dataclass
class ApplyRequest:
    plan_id: str
    meta: dict[str, str] = field(default_factory=dict)
