#!/usr/bin/env python3
"""Generate an animated GitHub stats SVG with no external dependencies."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

from github_profile_data import (
    ContributionFetchError,
    fetch_contribution_snapshot,
    fetch_events,
    fetch_repos,
    fetch_user,
    owned_work_repos,
)


def summarize(
    username: str,
    repos: list[dict[str, Any]],
    events: list[dict[str, Any]],
    contributions: int,
) -> dict[str, Any]:
    work_repos = owned_work_repos(username, repos)
    language_counter = Counter(repo.get("language") for repo in work_repos if repo.get("language"))
    top_languages = language_counter.most_common(3)
    recent_pushes = 0
    for event in events:
        if event.get("type") == "PushEvent":
            recent_pushes += 1

    return {
        "owned_repos": len(work_repos),
        "total_stars": sum(repo.get("stargazers_count", 0) for repo in work_repos),
        "total_forks": sum(repo.get("forks_count", 0) for repo in work_repos),
        "total_issues": sum(repo.get("open_issues_count", 0) for repo in work_repos),
        "language_label": " / ".join(f"{lang} ({count})" for lang, count in top_languages) or "N/A",
        "contributions": contributions,
        "recent_pushes": recent_pushes,
    }


def build_svg(username: str, user: dict[str, Any], metrics: dict[str, Any], offline: bool) -> str:
    name = escape(user.get("name") or username)

    rows = [
        ("Followers", user.get("followers", 0)),
        ("Owned Repos", metrics["owned_repos"]),
        ("Total Stars", metrics["total_stars"]),
        ("Contributions (year)", metrics["contributions"]),
        ("Recent Pushes", metrics["recent_pushes"]),
        ("Open Issues", metrics["total_issues"]),
    ]

    row_svg = []
    for i, (key, value) in enumerate(rows):
        y = 126 + i * 28
        row_svg.append(f'<text x="78" y="{y}" fill="#5eead4" font-size="19" font-weight="600">{key}:</text>')
        row_svg.append(f'<text x="360" y="{y}" fill="#e2e8f0" font-size="19" font-weight="700">{value}</text>')

    note = "Offline preview" if offline else "Live profile snapshot"
    languages = escape(metrics["language_label"])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="980" height="450" viewBox="0 0 980 450" role="img" aria-labelledby="title desc">
  <title id="title">{name} GitHub stats</title>
  <desc id="desc">Custom GitHub statistics card.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#070b1a"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
  </defs>
  <rect width="980" height="450" rx="20" fill="url(#bg)"/>

  <rect x="38" y="42" width="570" height="256" rx="12" fill="#181c31" stroke="#e5e7eb"/>
  <rect x="624" y="42" width="318" height="256" rx="12" fill="#181c31" stroke="#e5e7eb"/>
  <rect x="166" y="316" width="648" height="102" rx="10" fill="#181c31" stroke="#e5e7eb"/>
  <line x1="490" y1="326" x2="490" y2="408" stroke="#334155" stroke-width="2"/>

  <text x="76" y="88" fill="#7fb0ff" font-size="30" font-weight="700">{name}'s GitHub Stats</text>
  {''.join(row_svg)}
  <text x="78" y="286" fill="#67e8f9" font-size="16">Top owned-work languages: {languages}</text>

  <text x="650" y="95" fill="#7fb0ff" font-size="28" font-weight="700">Signal</text>
  <circle cx="783" cy="172" r="66" fill="none" stroke="#2b3f75" stroke-width="10"/>
  <circle cx="783" cy="172" r="66" fill="none" stroke="#7fb0ff" stroke-width="10" stroke-linecap="round" stroke-dasharray="280 134">
    <animateTransform attributeName="transform" type="rotate" from="0 783 172" to="360 783 172" dur="7s" repeatCount="indefinite"/>
  </circle>

  <text x="196" y="360" fill="#7fb0ff" font-size="44" font-weight="700">{metrics['contributions']}</text>
  <text x="196" y="396" fill="#93c5fd" font-size="22">Total Contributions</text>
  <text x="536" y="360" fill="#7fb0ff" font-size="44" font-weight="700">{metrics['total_stars']}</text>
  <text x="536" y="396" fill="#93c5fd" font-size="22">Owned Repo Stars</text>

  <text x="40" y="435" fill="#64748b" font-size="14">{note}</text>
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate custom GitHub stats SVG")
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--token", default=os.getenv("GH_STATS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    if args.offline:
        user = {"name": args.username, "followers": 0}
        metrics = {
            "owned_repos": 0,
            "total_stars": 0,
            "total_forks": 0,
            "total_issues": 0,
            "language_label": "N/A",
            "contributions": 0,
            "recent_pushes": 0,
        }
    else:
        try:
            user = fetch_user(args.username, args.token)
            repos = fetch_repos(args.username, args.token)
            events = fetch_events(args.username, args.token)
            snapshot = fetch_contribution_snapshot(args.username, args.token)
            metrics = summarize(args.username, repos, events, snapshot.total)
        except ContributionFetchError as exc:
            print(f"GitHub contribution request failed: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"GitHub request failed: {exc}", file=sys.stderr)
            return 1

    svg = build_svg(args.username, user, metrics, args.offline)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
