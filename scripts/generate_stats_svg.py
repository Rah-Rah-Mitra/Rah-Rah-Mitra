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

TECH_STACK_GROUPS = (
    ("Systems", ("Rust", "Tokio", "Axum", "SQLx", "Rusqlite", "Clap")),
    ("Python/API", ("Python", "FastAPI", "Pydantic", "aiohttp", "uv")),
    ("AI/OCR/CV", ("OpenCV", "Pillow", "pypdfium2", "ONNX", "Ultralytics", "Hailo")),
    ("Frontend", ("TypeScript", "React", "Vite", "Tailwind", "PostCSS")),
    ("Data", ("Jupyter", "GeoPandas", "NetworkX", "Matplotlib", "NumPy")),
    ("Tooling", ("Docker/Compose", "Shell", "PowerShell", "PlatformIO", "Arduino/C++")),
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
    safe_username = escape(username)

    metric_tiles = [
        ("Followers", user.get("followers", 0), "#5eead4"),
        ("Following", user.get("following", 0), "#67e8f9"),
        ("Public Repos", user.get("public_repos", metrics["owned_repos"]), "#93c5fd"),
        ("Owned Work", metrics["owned_repos"], "#a78bfa"),
        ("Year Contributions", metrics["contributions"], "#5eead4"),
        ("Recent Pushes", metrics["recent_pushes"], "#67e8f9"),
        ("Stars", metrics["total_stars"], "#93c5fd"),
        ("Forks", metrics["total_forks"], "#a78bfa"),
        ("Open Issues", metrics["total_issues"], "#5eead4"),
    ]

    tile_svg = []
    for i, (label, value, accent) in enumerate(metric_tiles):
        col = i % 3
        row = i // 3
        x = 58 + col * 138
        y = 166 + row * 68
        tile_svg.append(
            f'<g transform="translate({x} {y})">'
            '<rect width="126" height="60" rx="10" fill="#0f172a" stroke="#334155" stroke-opacity="0.84"/>'
            f'<text x="63" y="30" text-anchor="middle" fill="{accent}" font-size="27" font-weight="800">{_format_metric(value)}</text>'
            f'<text x="63" y="50" text-anchor="middle" fill="#cbd5e1" font-size="12" font-weight="600">{escape(label)}</text>'
            "</g>"
        )

    live_label = "PREVIEW" if offline else "LIVE"
    languages = escape(metrics["language_label"])
    stack_svg = _build_stack_rows()

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460" role="img" aria-labelledby="title desc" font-family="Segoe UI, Arial, sans-serif">
  <title id="title">{name} GitHub stats</title>
  <desc id="desc">Custom GitHub snapshot and known technology stack.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#a78bfa"/>
    </linearGradient>
  </defs>
  <rect width="1100" height="460" rx="24" fill="url(#bg)"/>

  <g stroke="#1e293b" stroke-width="1" opacity="0.56">
    <path d="M70 64H1030M70 126H1030M70 188H1030M70 250H1030M70 312H1030M70 374H1030"/>
    <path d="M110 42V408M230 42V408M350 42V408M470 42V408M590 42V408M710 42V408M830 42V408M950 42V408"/>
  </g>

  <text x="34" y="52" fill="#e2e8f0" font-size="32" font-weight="700">Profile Snapshot</text>
  <text x="34" y="84" fill="#93c5fd" font-size="18">{name} / @{safe_username}</text>

  <g transform="translate(34 96)">
    <rect width="448" height="292" rx="16" fill="#0f172a" stroke="url(#neon)" stroke-opacity="0.58">
      <animate attributeName="stroke-opacity" values="0.38;0.78;0.38" dur="4.8s" repeatCount="indefinite"/>
    </rect>
  </g>
  <text x="58" y="126" fill="#e2e8f0" font-size="24" font-weight="700">GitHub Snapshot</text>
  <text x="58" y="151" fill="#64748b" font-size="14">public activity, generated from GitHub</text>
  {''.join(tile_svg)}

  <g transform="translate(500 96)">
    <rect width="566" height="292" rx="16" fill="#0f172a" stroke="url(#neon)" stroke-opacity="0.48">
      <animate attributeName="stroke-opacity" values="0.32;0.7;0.32" dur="5.4s" repeatCount="indefinite"/>
    </rect>
  </g>
  <text x="526" y="126" fill="#e2e8f0" font-size="24" font-weight="700">Known Tech Stack</text>
  <text x="526" y="151" fill="#64748b" font-size="14">curated from public repositories</text>
  {stack_svg}

  <g transform="translate(34 406)">
    <rect width="88" height="26" rx="13" fill="#052e2b" stroke="#22d3ee" opacity="0.92">
      <animate attributeName="opacity" values="0.62;1;0.62" dur="2.2s" repeatCount="indefinite"/>
    </rect>
    <circle cx="15" cy="13" r="4" fill="#5eead4">
      <animate attributeName="opacity" values="0.35;1;0.35" dur="1.4s" repeatCount="indefinite"/>
    </circle>
    <text x="28" y="17" fill="#d1fae5" font-size="12" font-weight="700">{escape(live_label)}</text>
  </g>
  <text x="150" y="424" fill="#64748b" font-size="14">Top repo languages: {languages}</text>
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
        user = {"name": args.username, "followers": 0, "following": 0, "public_repos": 0}
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


def _build_stack_rows() -> str:
    rows = []
    for row_index, (group, labels) in enumerate(TECH_STACK_GROUPS):
        y = 166 + row_index * 36
        rows.append(
            f'<g transform="translate(526 {y})">'
            f'<text x="0" y="16" fill="#5eead4" font-size="14" font-weight="700">{escape(group)}</text>'
        )
        x = 92
        for label in labels:
            width = _chip_width(label)
            safe_label = escape(label)
            rows.append(
                f'<g transform="translate({x} 0)">'
                f'<rect width="{width}" height="24" rx="12" fill="#111827" stroke="#334155" stroke-opacity="0.88">'
                '<animate attributeName="stroke-opacity" values="0.42;0.95;0.42" dur="6s" repeatCount="indefinite"/>'
                '</rect>'
                f'<text x="{width / 2:.1f}" y="16.5" text-anchor="middle" fill="#cbd5e1" font-size="12.5" font-weight="600">{safe_label}</text>'
                "</g>"
            )
            x += width + 8
        rows.append("</g>")
    return "".join(rows)


def _chip_width(label: str) -> int:
    return max(50, int(len(label) * 6.1) + 21)


def _format_metric(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    return escape(str(value))


if __name__ == "__main__":
    raise SystemExit(main())
