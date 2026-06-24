from __future__ import annotations

import argparse
import sys

from oss_ledger import __version__
from oss_ledger.github import GitHubApiError, GitHubClient
from oss_ledger.render import render_json, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oss-ledger",
        description="Generate a readiness ledger for public GitHub repositories.",
    )
    parser.add_argument("--owner", required=True, help="GitHub user or organization login.")
    parser.add_argument("--limit", type=positive_int, help="Maximum number of repositories to scan.")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Write JSON to stdout.")
    output.add_argument("--markdown", action="store_true", help="Write a Markdown table to stdout.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        entries = GitHubClient().ledger_for_owner(args.owner, limit=args.limit)
    except GitHubApiError as exc:
        print(f"oss-ledger: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(render_json(entries), end="")
    else:
        print(render_markdown(entries), end="")
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed

