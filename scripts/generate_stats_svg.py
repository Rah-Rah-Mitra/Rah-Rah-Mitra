#!/usr/bin/env python3
"""Generate an animated GitHub stats SVG with no external dependencies."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

API_BASE = "https://api.github.com"


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
        url = (
            f"{API_BASE}/users/{urllib.parse.quote(username)}/repos"
            f"?type=owner&sort=updated&per_page=100&page={page}"
        )
        batch = _get_json(url, token)
        if not batch:
            return repos
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def summarize(repos: list[dict[str, Any]]) -> dict[str, Any]:
    public_repos = len(repos)
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    total_forks = sum(repo.get("forks_count", 0) for repo in repos)

    language_counter = Counter(repo.get("language") for repo in repos if repo.get("language"))
    top_languages = language_counter.most_common(3)
    language_label = " · ".join(f"{lang} ({count})" for lang, count in top_languages) or "N/A"

    top_repo = max(repos, key=lambda r: r.get("stargazers_count", 0), default=None)
    top_repo_label = "N/A"
    if top_repo:
        top_repo_label = f"{top_repo['name']} ★{top_repo.get('stargazers_count', 0)}"

    return {
        "public_repos": public_repos,
        "total_stars": total_stars,
        "total_forks": total_forks,
        "language_label": language_label,
        "top_repo_label": top_repo_label,
    }


def build_svg(username: str, user: dict[str, Any], metrics: dict[str, Any], offline: bool) -> str:
    name = user.get("name") or username
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    cards = [
        ("Followers", str(followers), "80", "190"),
        ("Following", str(following), "300", "190"),
        ("Public Repos", str(metrics["public_repos"]), "520", "190"),
        ("Total Stars", str(metrics["total_stars"]), "80", "300"),
        ("Total Forks", str(metrics["total_forks"]), "300", "300"),
    ]

    card_svg = []
    for i, (title, value, x, y) in enumerate(cards):
        delay = i * 0.15
        card_svg.append(
            f'''<g transform="translate({x},{y})" opacity="0">\
<animate attributeName="opacity" from="0" to="1" begin="{delay}s" dur="0.6s" fill="freeze"/>\
<rect width="190" height="90" rx="14" fill="#111827" stroke="#334155"/>\
<text x="18" y="32" fill="#93c5fd" font-size="14">{title}</text>\
<text x="18" y="66" fill="#e2e8f0" font-size="30" font-weight="700">{value}</text>\
</g>'''
        )

    note = "Offline preview values" if offline else "Live values from GitHub API"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="430" viewBox="0 0 800 430" role="img" aria-labelledby="title desc">
  <title id="title">{name}'s Custom GitHub Stats</title>
  <desc id="desc">Animated geometric GitHub summary card generated from GitHub API data.</desc>
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="line" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#a78bfa"/>
    </linearGradient>
  </defs>

  <rect width="800" height="430" rx="22" fill="url(#bg)"/>

  <g opacity="0.4">
    <polygon points="0,70 110,0 250,0 100,95" fill="#0b1222">
      <animate attributeName="points" dur="8s" repeatCount="indefinite"
        values="0,70 110,0 250,0 100,95;0,50 125,0 250,0 120,105;0,70 110,0 250,0 100,95"/>
    </polygon>
    <polygon points="800,360 675,430 560,430 700,335" fill="#101a33">
      <animate attributeName="points" dur="10s" repeatCount="indefinite"
        values="800,360 675,430 560,430 700,335;800,340 660,430 540,430 685,320;800,360 675,430 560,430 700,335"/>
    </polygon>
  </g>

  <polyline points="40,120 760,120" stroke="url(#line)" stroke-width="2" stroke-dasharray="6 6" fill="none">
    <animate attributeName="stroke-dashoffset" from="0" to="-24" dur="2s" repeatCount="indefinite"/>
  </polyline>

  <text x="40" y="62" fill="#38bdf8" font-size="16" letter-spacing="1.5">RAH-RAH-MITRA • LIVE PROFILE SNAPSHOT</text>
  <text x="40" y="98" fill="#f8fafc" font-size="34" font-weight="700">{name}</text>
  <text x="40" y="145" fill="#cbd5e1" font-size="16">Top languages: {metrics['language_label']}</text>
  <text x="40" y="170" fill="#cbd5e1" font-size="16">Top starred repo: {metrics['top_repo_label']}</text>
  <text x="560" y="400" fill="#64748b" font-size="12">{note}</text>

  {''.join(card_svg)}
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate custom GitHub stats SVG")
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument("--output", required=True, help="Output SVG path")
    parser.add_argument(
        "--token",
        default=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"),
        help="GitHub token (optional, improves API rate limit)",
    )
    parser.add_argument("--offline", action="store_true", help="Generate placeholder card without API calls")
    args = parser.parse_args()

    offline = args.offline
    if offline:
        user = {"name": args.username, "followers": 0, "following": 0}
        metrics = {
            "public_repos": 0,
            "total_stars": 0,
            "total_forks": 0,
            "language_label": "N/A",
            "top_repo_label": "N/A",
        }
    else:
        try:
            user = fetch_user(args.username, args.token)
            repos = fetch_repos(args.username, args.token)
            metrics = summarize(repos)
        except urllib.error.HTTPError as exc:
            print(f"GitHub API request failed: HTTP {exc.code}", file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"GitHub API request failed: {exc.reason}", file=sys.stderr)
            return 1

    svg = build_svg(args.username, user, metrics, offline)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
