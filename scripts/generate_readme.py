#!/usr/bin/env python3
"""Render the GitHub profile README from live profile and owned repository data."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from github_profile_data import fetch_repos, fetch_user, owned_work_repos

DEFAULT_BIO = (
    "Fellow coder partaking in NUS B.Eng. (Hons) in Industrial & Systems Engineering, "
    "2nd Major in CS and a Minor in Math"
)
DEFAULT_PORTFOLIO = "https://rahul-mitra.vercel.app/"
LINKEDIN = "https://www.linkedin.com/in/rahulmitra-dev/"


def build_readme(username: str, user: dict[str, Any], repos: list[dict[str, Any]]) -> str:
    name = _clean_text(user.get("name") or username)
    bio = _clean_text(user.get("bio") or DEFAULT_BIO)
    portfolio = _clean_url(user.get("blog")) or DEFAULT_PORTFOLIO
    work_repos = owned_work_repos(username, repos)

    repo_lines = [_repo_line(repo) for repo in work_repos]
    if not repo_lines:
        repo_lines = ["- Owned public repositories will appear here after the next profile refresh."]

    return f'''<div align="center">
  <img src="assets/hero-geometry.svg" width="100%" alt="Custom geometric animated profile banner" />
</div>

# {name}

{bio}

[GitHub](https://github.com/{username}) | [Portfolio]({portfolio}) | [LinkedIn]({LINKEDIN})

## Work

{chr(10).join(repo_lines)}

## Contributions

<p align="center">
  <img src="assets/contribution-3d.svg" width="100%" alt="3D contribution graph" />
</p>

## Profile Snapshot

<p align="center">
  <img src="assets/github-stats.svg" width="100%" alt="Custom GitHub profile insights with geometric animation" />
</p>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the GitHub profile README")
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--token", default=os.getenv("GH_STATS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    if args.offline:
        user = {"name": "Rahul Mitra", "bio": DEFAULT_BIO, "blog": DEFAULT_PORTFOLIO}
        repos: list[dict[str, Any]] = []
    else:
        try:
            user = fetch_user(args.username, args.token)
            repos = fetch_repos(args.username, args.token)
        except OSError as exc:
            print(f"GitHub request failed: {exc}", file=sys.stderr)
            return 1

    readme = build_readme(args.username, user, repos)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(readme, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def _repo_line(repo: dict[str, Any]) -> str:
    name = _clean_text(repo.get("name") or "Repository")
    url = _clean_url(repo.get("html_url"))
    language = _clean_text(repo.get("language") or "")
    description = _clean_text(repo.get("description") or "")

    detail_parts = []
    if description:
        detail_parts.append(description)
    if language:
        detail_parts.append(language)
    detail = " - ".join(detail_parts) if detail_parts else "Owned repository"

    return f"- [{name}]({url}) - {detail}"


def _clean_text(value: str) -> str:
    return " ".join(str(value).replace("|", "/").split())


def _clean_url(value: str | None) -> str:
    value = (value or "").strip()
    return value if value.startswith(("http://", "https://")) else ""


if __name__ == "__main__":
    raise SystemExit(main())
