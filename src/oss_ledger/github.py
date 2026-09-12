from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from oss_ledger.model import ReleaseInfo, RepoLedgerEntry, WorkflowRunInfo
from oss_ledger.readiness import classify_repo_facts


API_ROOT = "https://api.github.com"


class GitHubApiError(RuntimeError):
    pass


def encode_path_segment(value: str) -> str:
    """Percent-encode a single URL path segment so reserved characters cannot rewrite the path."""
    return urllib.parse.quote(value, safe="")


class GitHubClient:
    def __init__(self, token: str | None = None, api_root: str = API_ROOT) -> None:
        self.api_root = api_root.rstrip("/")
        self.token = token if token is not None else self._env_token_for_api_root()

    def ledger_for_owner(self, owner: str, limit: int | None = None) -> list[RepoLedgerEntry]:
        checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        entries: list[RepoLedgerEntry] = []
        for repo in self.iter_public_owner_repos(owner):
            if limit is not None and len(entries) >= limit:
                break
            entries.append(self.entry_from_repo(repo, checked_at=checked_at))
        entries.sort(key=lambda entry: entry.full_name.lower())
        return entries

    def iter_public_owner_repos(self, owner: str) -> Iterator[dict[str, Any]]:
        page = 1
        encoded_owner = encode_path_segment(owner)
        while True:
            data = self._request_json(
                f"/users/{encoded_owner}/repos",
                {
                    "type": "owner",
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": 100,
                    "page": page,
                },
            )
            if not isinstance(data, list):
                raise GitHubApiError(f"Expected a repository list for owner {owner}.")
            if not data:
                return
            for repo in data:
                if not repo.get("private", False):
                    yield repo
            page += 1

    def entry_from_repo(self, repo: dict[str, Any], *, checked_at: str) -> RepoLedgerEntry:
        owner = repo_owner(repo)
        name = expect_str(repo, "name")
        full_name = expect_str(repo, "full_name")
        readme_present = self.repo_has_readme(owner, name)
        latest_release = self.latest_release(owner, name)
        ci_present = self.repo_has_workflows(owner, name)
        recent_workflow_status = self.recent_workflow_status(owner, name) if ci_present else None
        license_spdx = license_spdx_id(repo.get("license"))
        publish_readiness, blocking_reasons, next_action = classify_repo_facts(
            archived=bool(repo.get("archived", False)),
            fork=bool(repo.get("fork", False)),
            description=optional_str(repo.get("description")),
            readme_present=readme_present,
            license_spdx=license_spdx,
            ci_present=ci_present,
            latest_release=latest_release,
        )

        return RepoLedgerEntry(
            owner=owner,
            name=name,
            full_name=full_name,
            visibility=optional_str(repo.get("visibility")) or "public",
            archived=bool(repo.get("archived", False)),
            fork=bool(repo.get("fork", False)),
            default_branch=optional_str(repo.get("default_branch")),
            description=optional_str(repo.get("description")),
            homepage=optional_str(repo.get("homepage")),
            topics=tuple(str(topic) for topic in repo.get("topics") or ()),
            readme_present=readme_present,
            license_spdx=license_spdx,
            ci_present=ci_present,
            latest_release=latest_release,
            recent_workflow_status=recent_workflow_status,
            publish_readiness=publish_readiness,
            blocking_reasons=blocking_reasons,
            next_action=next_action,
            checked_at=checked_at,
            source_url=expect_str(repo, "html_url"),
        )

    def repo_has_readme(self, owner: str, repo: str) -> bool:
        return self._request_json(self._repo_path(owner, repo, "readme"), allow_not_found=True) is not None

    def latest_release(self, owner: str, repo: str) -> ReleaseInfo | None:
        data = self._request_json(self._repo_path(owner, repo, "releases/latest"), allow_not_found=True)
        if data is None:
            return None
        return ReleaseInfo(
            tag_name=expect_str(data, "tag_name"),
            published_at=optional_str(data.get("published_at")),
        )

    def repo_has_workflows(self, owner: str, repo: str) -> bool:
        data = self._request_json(
            self._repo_path(owner, repo, "actions/workflows"),
            {"per_page": 1},
            allow_not_found=True,
        )
        if data is None:
            return False
        return int(data.get("total_count", 0)) > 0

    def recent_workflow_status(self, owner: str, repo: str) -> WorkflowRunInfo | None:
        data = self._request_json(
            self._repo_path(owner, repo, "actions/runs"),
            {"per_page": 1},
            allow_not_found=True,
        )
        if data is None:
            return None
        runs = data.get("workflow_runs") or []
        if not runs:
            return None
        run = runs[0]
        return WorkflowRunInfo(
            name=optional_str(run.get("name")),
            status=optional_str(run.get("status")),
            conclusion=optional_str(run.get("conclusion")),
            html_url=optional_str(run.get("html_url")),
            updated_at=optional_str(run.get("updated_at")),
        )

    def _request_json(
        self,
        path: str,
        query: dict[str, str | int] | None = None,
        *,
        allow_not_found: bool = False,
    ) -> Any:
        url = self._url(path, query)
        request = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and allow_not_found:
                return None
            message = exc.read().decode("utf-8", errors="replace")
            if exc.code in {403, 429}:
                raise GitHubApiError(f"GitHub API rate limit or permission error for {url}: {message}") from exc
            raise GitHubApiError(f"GitHub API error {exc.code} for {url}: {message}") from exc
        except urllib.error.URLError as exc:
            raise GitHubApiError(f"Network error calling GitHub API {url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise GitHubApiError(f"GitHub API returned invalid JSON for {url}: {exc}") from exc

    def _url(self, path: str, query: dict[str, str | int] | None) -> str:
        encoded_query = urllib.parse.urlencode(query or {})
        url = f"{self.api_root}{path}"
        if encoded_query:
            url = f"{url}?{encoded_query}"
        return url

    def _repo_path(self, owner: str, repo: str, suffix: str) -> str:
        return f"/repos/{encode_path_segment(owner)}/{encode_path_segment(repo)}/{suffix}"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "open-source-repo-ledger",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _env_token_for_api_root(self) -> str | None:
        if self.api_root == API_ROOT:
            return os.environ.get("GITHUB_TOKEN")
        return None


def repo_owner(repo: dict[str, Any]) -> str:
    owner = repo.get("owner")
    if not isinstance(owner, dict):
        raise GitHubApiError("Repository payload is missing owner.")
    return expect_str(owner, "login")


def expect_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise GitHubApiError(f"GitHub payload is missing string field: {key}")
    return value


def optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def license_spdx_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    spdx_id = value.get("spdx_id")
    if isinstance(spdx_id, str) and spdx_id and spdx_id != "NOASSERTION":
        return spdx_id
    return None
