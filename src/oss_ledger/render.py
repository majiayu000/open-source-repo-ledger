from __future__ import annotations

import json
from collections.abc import Sequence

from oss_ledger.model import RepoLedgerEntry


def render_json(entries: Sequence[RepoLedgerEntry]) -> str:
    payload = [entry.to_dict() for entry in entries]
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_markdown(entries: Sequence[RepoLedgerEntry]) -> str:
    rows = [
        "Publication signals only: `ready` means a description, README, GitHub SPDX license "
        "metadata, GitHub Actions workflow, and latest full GitHub release were observed; "
        "`needs_work` means one or more were not observed. Archived repositories and forks "
        "are `not_applicable`.",
        "",
        "GitHub Actions shows the latest observed run result/status independently of publication "
        "signals; a failed run can coexist with `ready`. `configured` means a workflow was "
        "observed without a run result/status; a blank Actions cell means no workflow was observed.",
        "",
        "Missing signals may be unobserved or unrecognized; verify before following suggested "
        "actions. This report does not determine license rights or assess code quality, security, "
        "test coverage, installability, release assets, support, maintenance, or adoption.",
        "",
        "| Repository | Publication signals | Signal gaps / exclusions | Suggested next action "
        "| Latest full release | GitHub Actions | License SPDX |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        release = entry.latest_release.tag_name if entry.latest_release else ""
        ci = _workflow_status(entry)
        license_spdx = entry.license_spdx or ""
        blockers = ", ".join(entry.blocking_reasons)
        rows.append(
            "| {repo} | {status} | {blockers} | {next_action} | {release} | {ci} | {license} |".format(
                repo=_escape_cell(entry.full_name),
                status=_escape_cell(entry.publish_readiness),
                blockers=_escape_cell(blockers),
                next_action=_escape_cell(entry.next_action),
                release=_escape_cell(release),
                ci=_escape_cell(ci),
                license=_escape_cell(license_spdx),
            )
        )
    return "\n".join(rows) + "\n"


def _workflow_status(entry: RepoLedgerEntry) -> str:
    if not entry.ci_present:
        return ""
    if entry.recent_workflow_status is None:
        return "configured"
    if entry.recent_workflow_status.conclusion:
        return entry.recent_workflow_status.conclusion
    return entry.recent_workflow_status.status or "configured"


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")

