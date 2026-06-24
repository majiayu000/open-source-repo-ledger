# open-source-repo-ledger

Open-source repository status ledger for GitHub owners: license, CI, releases,
metadata, readiness, and next actions.

`oss-ledger` scans public repositories for a GitHub user or organization and
prints a small ledger you can use before publishing, pinning, or cleaning up a
portfolio of open-source projects.

## Install

```bash
python -m pip install git+https://github.com/majiayu000/open-source-repo-ledger.git
```

For local development:

```bash
python -m pip install -e .
```

## Usage

```bash
oss-ledger --owner majiayu000 --limit 5 --markdown
oss-ledger --owner majiayu000 --limit 5 --json
```

By default, the CLI reads public GitHub metadata without authentication. Set a
`GITHUB_TOKEN` environment variable to raise GitHub API limits. The token should
only need read access to public metadata; this tool does not write to GitHub and
does not scan private repositories. The environment token is only used for the
default `https://api.github.com` API root.

## Output Fields

- `owner`, `name`, `full_name`, `source_url`
- `visibility`, `archived`, `fork`, `default_branch`
- `description`, `homepage`, `topics`
- `readme_present`, `license_spdx`, `ci_present`
- `latest_release`, `recent_workflow_status`
- `publish_readiness`, `blocking_reasons`, `next_action`
- `checked_at`

## Readiness Rules

Repositories are `ready` when they have a description, README, explicit license,
CI workflow, and latest release. Repositories are `needs_work` when one or more
of those signals are missing. Archived repositories and forks are
`not_applicable` by default.

This is intentionally a ledger, not a quality score. It does not judge code
quality, security posture, test coverage, or project popularity.

## Development

```bash
python -m compileall src tests
PYTHONPATH=src python -m unittest discover -s tests
python -m pip install .
oss-ledger --help
```
