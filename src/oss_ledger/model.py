from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


PublishReadiness = Literal["ready", "needs_work", "not_applicable"]


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    published_at: str | None


@dataclass(frozen=True)
class WorkflowRunInfo:
    name: str | None
    status: str | None
    conclusion: str | None
    html_url: str | None
    updated_at: str | None


@dataclass(frozen=True)
class RepoLedgerEntry:
    owner: str
    name: str
    full_name: str
    visibility: str
    archived: bool
    fork: bool
    default_branch: str | None
    description: str | None
    homepage: str | None
    topics: tuple[str, ...]
    readme_present: bool
    license_spdx: str | None
    ci_present: bool
    latest_release: ReleaseInfo | None
    recent_workflow_status: WorkflowRunInfo | None
    publish_readiness: PublishReadiness
    blocking_reasons: tuple[str, ...]
    next_action: str
    checked_at: str
    source_url: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

