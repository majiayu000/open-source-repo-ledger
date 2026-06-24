from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from oss_ledger import cli
from oss_ledger.model import ReleaseInfo, RepoLedgerEntry, WorkflowRunInfo
from oss_ledger.render import render_json, render_markdown


class RenderTests(unittest.TestCase):
    def test_render_json_is_valid_and_stable(self) -> None:
        payload = json.loads(render_json([sample_entry()]))

        self.assertEqual(payload[0]["full_name"], "majiayu000/open-source-repo-ledger")
        self.assertEqual(payload[0]["latest_release"]["tag_name"], "v0.1.0")

    def test_render_markdown_includes_core_columns(self) -> None:
        output = render_markdown([sample_entry()])

        self.assertIn("| Repository | Status | Blockers | Next action | Release | CI | License |", output)
        self.assertIn("| majiayu000/open-source-repo-ledger | ready |  | Keep current. | v0.1.0 | success | MIT |", output)


class CliRenderTests(unittest.TestCase):
    def test_json_flag_uses_json_renderer(self) -> None:
        stdout = io.StringIO()
        with patch("oss_ledger.cli.GitHubClient") as client_class:
            client_class.return_value.ledger_for_owner.return_value = [sample_entry()]
            with redirect_stdout(stdout):
                exit_code = cli.main(["--owner", "majiayu000", "--limit", "5", "--json"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())[0]["name"], "open-source-repo-ledger")
        client_class.return_value.ledger_for_owner.assert_called_once_with("majiayu000", limit=5)

    def test_markdown_flag_uses_markdown_renderer(self) -> None:
        stdout = io.StringIO()
        with patch("oss_ledger.cli.GitHubClient") as client_class:
            client_class.return_value.ledger_for_owner.return_value = [sample_entry()]
            with redirect_stdout(stdout):
                exit_code = cli.main(["--owner", "majiayu000", "--limit", "5", "--markdown"])

        self.assertEqual(exit_code, 0)
        self.assertIn("| majiayu000/open-source-repo-ledger | ready |", stdout.getvalue())
        client_class.return_value.ledger_for_owner.assert_called_once_with("majiayu000", limit=5)


def sample_entry() -> RepoLedgerEntry:
    return RepoLedgerEntry(
        owner="majiayu000",
        name="open-source-repo-ledger",
        full_name="majiayu000/open-source-repo-ledger",
        visibility="public",
        archived=False,
        fork=False,
        default_branch="main",
        description="A repository ledger.",
        homepage=None,
        topics=("github", "open-source"),
        readme_present=True,
        license_spdx="MIT",
        ci_present=True,
        latest_release=ReleaseInfo(tag_name="v0.1.0", published_at="2026-06-25T00:00:00Z"),
        recent_workflow_status=WorkflowRunInfo(
            name="check",
            status="completed",
            conclusion="success",
            html_url="https://example.com/run",
            updated_at="2026-06-25T00:00:00Z",
        ),
        publish_readiness="ready",
        blocking_reasons=(),
        next_action="Keep current.",
        checked_at="2026-06-25T00:00:00Z",
        source_url="https://github.com/majiayu000/open-source-repo-ledger",
    )


if __name__ == "__main__":
    unittest.main()
