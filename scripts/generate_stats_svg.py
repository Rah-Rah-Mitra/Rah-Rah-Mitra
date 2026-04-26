#!/usr/bin/env python3
"""Generate an animated GitHub stats SVG with no external dependencies."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

API_BASE = "https://api.github.com"
CONTRIB_URL = "https://github.com/users/{username}/contributions"
COUNT_RE = re.compile(r'data-count="(\d+)"')


def _get_json(url: str, token: str | None = None) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "rah-rah-mitra-readme-generator",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_user(username: str, token: str | None = None) -> dict[str, Any]:
    return _get_json(f"{API_BASE}/users/{urllib.parse.quote(username)}", token)


def fetch_repos(username: str, token: str | None = None) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"{API_BASE}/users/{urllib.parse.quote(username)}/repos?type=owner&sort=updated&per_page=100&page={page}"
        batch = _get_json(url, token)
        if not batch:
            return repos
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def fetch_events(username: str, token: str | None = None) -> list[dict[str, Any]]:
    return _get_json(f"{API_BASE}/users/{urllib.parse.quote(username)}/events/public?per_page=100", token)


def fetch_contributions_total(username: str) -> int:
    req = urllib.request.Request(CONTRIB_URL.format(username=username), headers={"User-Agent": "stats-card"})
    with urllib.request.urlopen(req, timeout=30) as response:
        text = response.read().decode("utf-8")
    return sum(int(v) for v in COUNT_RE.findall(text))


def summarize(repos: list[dict[str, Any]], events: list[dict[str, Any]], contributions: int) -> dict[str, Any]:
    language_counter = Counter(repo.get("language") for repo in repos if repo.get("language"))
    top_languages = language_counter.most_common(3)
    recent_commits = 0
    for ev in events:
        if ev.get("type") == "PushEvent":
            recent_commits += len(ev.get("payload", {}).get("commits", []))

    return {
        "public_repos": len(repos),
        "total_stars": sum(repo.get("stargazers_count", 0) for repo in repos),
        "total_forks": sum(repo.get("forks_count", 0) for repo in repos),
        "total_issues": sum(repo.get("open_issues_count", 0) for repo in repos),
        "language_label": " · ".join(f"{lang} ({count})" for lang, count in top_languages) or "N/A",
        "contributions": contributions,
        "recent_commits": recent_commits,
    }


def build_svg(username: str, user: dict[str, Any], metrics: dict[str, Any], offline: bool) -> str:
    name = user.get("name") or username

    rows = [
        ("Followers", user.get("followers", 0)),
        ("Public Repos", metrics["public_repos"]),
        ("Total Stars", metrics["total_stars"]),
        ("Contributions (year)", metrics["contributions"]),
        ("Recent Commits", metrics["recent_commits"]),
        ("Open Issues", metrics["total_issues"]),
    ]

    row_svg = []
    for i, (k, v) in enumerate(rows):
        y = 146 + i * 34
        row_svg.append(f'<text x="64" y="{y}" fill="#5eead4" font-size="20" font-weight="600">{k}:</text>')
        row_svg.append(f'<text x="350" y="{y}" fill="#e2e8f0" font-size="20" font-weight="700">{v}</text>')

    note = "Offline preview" if offline else "Live profile snapshot"

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
  <rect x="40" y="40" width="560" height="330" rx="12" fill="#181c31" stroke="#e5e7eb"/>
  <rect x="615" y="72" width="325" height="196" rx="12" fill="#181c31" stroke="#e5e7eb"/>
  <rect x="186" y="286" width="620" height="130" rx="10" fill="#181c31" stroke="#e5e7eb"/>

  <text x="66" y="88" fill="#7fb0ff" font-size="40" font-weight="700">{name}'s GitHub Stats</text>
  {''.join(row_svg)}
  <text x="64" y="360" fill="#67e8f9" font-size="17">Top languages: {metrics['language_label']}</text>

  <text x="640" y="120" fill="#7fb0ff" font-size="40" font-weight="700">Signal</text>
  <circle cx="780" cy="182" r="63" fill="none" stroke="#2b3f75" stroke-width="10"/>
  <circle cx="780" cy="182" r="63" fill="none" stroke="#7fb0ff" stroke-width="10" stroke-linecap="round" stroke-dasharray="280 120">
    <animateTransform attributeName="transform" type="rotate" from="0 780 182" to="360 780 182" dur="7s" repeatCount="indefinite"/>
  </circle>

  <text x="214" y="340" fill="#7fb0ff" font-size="54" font-weight="700">{metrics['contributions']}</text>
  <text x="214" y="384" fill="#93c5fd" font-size="30">Total Contributions</text>
  <text x="560" y="340" fill="#7fb0ff" font-size="54" font-weight="700">{metrics['total_stars']}</text>
  <text x="560" y="384" fill="#93c5fd" font-size="30">Total Stars</text>

  <text x="40" y="432" fill="#64748b" font-size="14">{note}</text>
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate custom GitHub stats SVG")
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--token", default=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    if args.offline:
        user = {"name": args.username, "followers": 0}
        metrics = {
            "public_repos": 0,
            "total_stars": 0,
            "total_forks": 0,
            "total_issues": 0,
            "language_label": "N/A",
            "contributions": 0,
            "recent_commits": 0,
        }
    else:
        try:
            user = fetch_user(args.username, args.token)
            repos = fetch_repos(args.username, args.token)
            events = fetch_events(args.username, args.token)
            contribs = fetch_contributions_total(args.username)
            metrics = summarize(repos, events, contribs)
        except urllib.error.HTTPError as exc:
            print(f"GitHub API request failed: HTTP {exc.code}", file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"GitHub API request failed: {exc.reason}", file=sys.stderr)
            return 1

    svg = build_svg(args.username, user, metrics, args.offline)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
