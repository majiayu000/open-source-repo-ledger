from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from oss_ledger.github import GitHubApiError, GitHubClient, expect_int, license_spdx_id, optional_str
from oss_ledger.model import ReleaseInfo, WorkflowRunInfo


class FakeGitHubClient(GitHubClient):
    def __init__(self) -> None:
        super().__init__(token=None, api_root="https://example.invalid")

    def repo_has_readme(self, owner: str, repo: str) -> bool:
        return True

    def latest_release(self, owner: str, repo: str) -> ReleaseInfo | None:
        return ReleaseInfo(tag_name="v0.1.0", published_at="2026-06-25T00:00:00Z")

    def repo_has_workflows(self, owner: str, repo: str) -> bool:
        return True

    def recent_workflow_status(self, owner: str, repo: str) -> WorkflowRunInfo | None:
        return None


class GitHubMappingTests(unittest.TestCase):
    def test_entry_from_repo_maps_github_payload(self) -> None:
        entry = FakeGitHubClient().entry_from_repo(
            {
                "owner": {"login": "majiayu000"},
                "name": "open-source-repo-ledger",
                "full_name": "majiayu000/open-source-repo-ledger",
                "private": False,
                "visibility": "public",
                "archived": False,
                "fork": False,
                "default_branch": "main",
                "description": "A repository ledger.",
                "homepage": "",
                "topics": ["github", "ledger"],
                "license": {"spdx_id": "MIT"},
                "html_url": "https://github.com/majiayu000/open-source-repo-ledger",
            },
            checked_at="2026-06-25T00:00:00Z",
        )

        self.assertEqual(entry.owner, "majiayu000")
        self.assertEqual(entry.license_spdx, "MIT")
        self.assertEqual(entry.publish_readiness, "ready")
        self.assertEqual(entry.homepage, None)
        self.assertEqual(entry.topics, ("github", "ledger"))

    def test_optional_str_rejects_empty_strings(self) -> None:
        self.assertIsNone(optional_str(""))
        self.assertEqual(optional_str("value"), "value")

    def test_license_noassertion_is_unknown(self) -> None:
        self.assertIsNone(license_spdx_id({"spdx_id": "NOASSERTION"}))

    def test_default_api_root_reads_ambient_token(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "dummy-token"}):
            client = GitHubClient()

        self.assertEqual(client._headers()["Authorization"], "Bearer dummy-token")

    def test_custom_api_root_does_not_read_ambient_token(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "dummy-token"}):
            client = GitHubClient(api_root="https://example.invalid")

        self.assertNotIn("Authorization", client._headers())

    def test_expect_int_rejects_null_and_non_int(self) -> None:
        self.assertEqual(expect_int({}, "total_count", default=0), 0)
        self.assertEqual(expect_int({"total_count": 3}, "total_count", default=0), 3)
        with self.assertRaises(GitHubApiError):
            expect_int({"total_count": None}, "total_count", default=0)
        with self.assertRaises(GitHubApiError):
            expect_int({"total_count": "1"}, "total_count", default=0)

    def test_repo_has_workflows_null_total_count_raises_github_api_error(self) -> None:
        client = GitHubClient(token=None, api_root="https://example.invalid")
        with patch.object(client, "_request_json", return_value={"total_count": None}):
            with self.assertRaises(GitHubApiError) as ctx:
                client.repo_has_workflows("owner", "repo")
        self.assertIn("total_count", str(ctx.exception))
        self.assertNotIsInstance(ctx.exception, TypeError)

    def test_repo_has_workflows_missing_total_count_is_false(self) -> None:
        client = GitHubClient(token=None, api_root="https://example.invalid")
        with patch.object(client, "_request_json", return_value={}):
            self.assertFalse(client.repo_has_workflows("owner", "repo"))


if __name__ == "__main__":
    unittest.main()
