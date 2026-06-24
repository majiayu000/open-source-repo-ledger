from __future__ import annotations

from oss_ledger.model import PublishReadiness, ReleaseInfo


def classify_repo_facts(
    *,
    archived: bool,
    fork: bool,
    description: str | None,
    readme_present: bool,
    license_spdx: str | None,
    ci_present: bool,
    latest_release: ReleaseInfo | None,
) -> tuple[PublishReadiness, tuple[str, ...], str]:
    if archived:
        return (
            "not_applicable",
            ("archived repository",),
            "No publishing action needed for archived repositories.",
        )

    if fork:
        return (
            "not_applicable",
            ("forked repository",),
            "No publishing action needed for forks unless they become maintained projects.",
        )

    blockers: list[str] = []
    if not description or not description.strip():
        blockers.append("missing description")
    if not readme_present:
        blockers.append("missing README")
    if not license_spdx:
        blockers.append("missing license")
    if not ci_present:
        blockers.append("missing CI")
    if latest_release is None:
        blockers.append("no release")

    if not blockers:
        return ("ready", (), "Keep metadata, CI, and releases current.")

    return ("needs_work", tuple(blockers), _next_action(blockers[0]))


def _next_action(blocker: str) -> str:
    actions = {
        "missing description": "Add a concise GitHub repository description.",
        "missing README": "Add a README with purpose, install, usage, and validation.",
        "missing license": "Add an explicit open-source license.",
        "missing CI": "Add a minimal CI workflow for tests and packaging checks.",
        "no release": "Publish an initial tagged release when the project is usable.",
    }
    return actions.get(blocker, "Review the repository readiness blockers.")

