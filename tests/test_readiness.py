from __future__ import annotations

import unittest

from oss_ledger.model import ReleaseInfo
from oss_ledger.readiness import classify_repo_facts


class ReadinessTests(unittest.TestCase):
    def test_ready_when_required_publication_signals_exist(self) -> None:
        status, blockers, next_action = classify_repo_facts(
            archived=False,
            fork=False,
            description="Tooling for repositories.",
            readme_present=True,
            license_spdx="MIT",
            ci_present=True,
            latest_release=ReleaseInfo(tag_name="v0.1.0", published_at="2026-06-25T00:00:00Z"),
        )

        self.assertEqual(status, "ready")
        self.assertEqual(blockers, ())
        self.assertEqual(next_action, "Keep metadata, CI, and releases current.")

    def test_needs_work_lists_blockers_in_action_order(self) -> None:
        status, blockers, next_action = classify_repo_facts(
            archived=False,
            fork=False,
            description=None,
            readme_present=False,
            license_spdx=None,
            ci_present=False,
            latest_release=None,
        )

        self.assertEqual(status, "needs_work")
        self.assertEqual(
            blockers,
            ("missing description", "missing README", "missing license", "missing CI", "no release"),
        )
        self.assertEqual(next_action, "Add a concise GitHub repository description.")

    def test_archived_repositories_are_not_applicable(self) -> None:
        status, blockers, next_action = classify_repo_facts(
            archived=True,
            fork=False,
            description=None,
            readme_present=False,
            license_spdx=None,
            ci_present=False,
            latest_release=None,
        )

        self.assertEqual(status, "not_applicable")
        self.assertEqual(blockers, ("archived repository",))
        self.assertIn("archived", next_action)


if __name__ == "__main__":
    unittest.main()

