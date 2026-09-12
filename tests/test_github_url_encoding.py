from __future__ import annotations

import unittest
from unittest.mock import patch

from oss_ledger.github import GitHubClient, encode_path_segment


class EncodePathSegmentTests(unittest.TestCase):
    def test_encodes_reserved_characters_as_single_segment(self) -> None:
        self.assertEqual(encode_path_segment("evil?x=1"), "evil%3Fx%3D1")
        self.assertEqual(encode_path_segment("a/b"), "a%2Fb")
        self.assertEqual(encode_path_segment("name#tag"), "name%23tag")
        self.assertEqual(encode_path_segment("my repo"), "my%20repo")


class GitHubUrlEncodingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = GitHubClient(token=None, api_root="https://api.example.test")
        self.captured_urls: list[str] = []

    def _capture_request(self, path: str, query=None, *, allow_not_found: bool = False):
        self.captured_urls.append(self.client._url(path, query))
        if allow_not_found:
            return None
        return []

    def test_iter_public_owner_repos_encodes_query_injection_owner(self) -> None:
        with patch.object(self.client, "_request_json", side_effect=self._capture_request):
            list(self.client.iter_public_owner_repos("evil?x=1"))

        self.assertEqual(len(self.captured_urls), 1)
        url = self.captured_urls[0]
        self.assertIn("/users/evil%3Fx%3D1/repos?", url)
        self.assertNotIn("/users/evil?x=1/repos", url)
        self.assertTrue(url.startswith("https://api.example.test/users/evil%3Fx%3D1/repos?"))
        self.assertIn("type=owner", url)

    def test_repo_methods_encode_slash_hash_and_space(self) -> None:
        owner = "org/with#hash"
        repo = "name with space"
        encoded_owner = "org%2Fwith%23hash"
        encoded_repo = "name%20with%20space"

        with patch.object(self.client, "_request_json", side_effect=self._capture_request):
            self.client.repo_has_readme(owner, repo)
            self.client.latest_release(owner, repo)
            self.client.repo_has_workflows(owner, repo)
            self.client.recent_workflow_status(owner, repo)

        self.assertEqual(len(self.captured_urls), 4)
        self.assertTrue(self.captured_urls[0].endswith(f"/repos/{encoded_owner}/{encoded_repo}/readme"))
        self.assertTrue(
            self.captured_urls[1].endswith(f"/repos/{encoded_owner}/{encoded_repo}/releases/latest")
        )
        self.assertIn(f"/repos/{encoded_owner}/{encoded_repo}/actions/workflows?", self.captured_urls[2])
        self.assertIn(f"/repos/{encoded_owner}/{encoded_repo}/actions/runs?", self.captured_urls[3])
        for url in self.captured_urls:
            self.assertNotIn("/org/with#hash/", url)
            self.assertNotIn("/name with space/", url)

    def test_path_builder_keeps_query_append_behavior(self) -> None:
        path = self.client._repo_path("owner?", "repo#1", "readme")
        url = self.client._url(path, {"per_page": 1})
        self.assertEqual(
            url,
            "https://api.example.test/repos/owner%3F/repo%231/readme?per_page=1",
        )
