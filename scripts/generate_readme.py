#!/usr/bin/env python3
"""Render the GitHub profile README from live profile data."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Any

from github_profile_data import fetch_user

DEFAULT_BIO = (
    "Fellow coder partaking in NUS B.Eng. (Hons) in Industrial & Systems Engineering, "
    "2nd Major in CS and a Minor in Math"
)
DEFAULT_PORTFOLIO = "https://rahul-mitra.vercel.app/"
LINKEDIN = "https://www.linkedin.com/in/rahulmitra-dev/"


def build_readme(username: str, user: dict[str, Any]) -> str:
    bio = _clean_text(user.get("bio") or DEFAULT_BIO)
    portfolio = _clean_url(user.get("blog")) or DEFAULT_PORTFOLIO
    hero_src = _asset_src("assets/hero-geometry.svg")
    contribution_src = _asset_src("assets/contribution-3d.svg")
    stats_src = _asset_src("assets/github-stats.svg")

    return f'''<div align="center">
  <img src="{hero_src}" width="100%" alt="Custom geometric animated profile banner" />
</div>

{bio}

[GitHub](https://github.com/{username}) | [Portfolio]({portfolio}) | [LinkedIn]({LINKEDIN})

## Contributions

<p align="center">
  <img src="{contribution_src}" width="100%" alt="3D contribution graph" />
</p>

## Profile Snapshot

<p align="center">
  <img src="{stats_src}" width="100%" alt="Custom GitHub profile insights with geometric animation" />
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
    else:
        try:
            user = fetch_user(args.username, args.token)
        except OSError as exc:
            print(f"GitHub request failed: {exc}", file=sys.stderr)
            return 1

    readme = build_readme(args.username, user)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(readme, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def _clean_text(value: str) -> str:
    return " ".join(str(value).replace("|", "/").split())


def _clean_url(value: str | None) -> str:
    value = (value or "").strip()
    return value if value.startswith(("http://", "https://")) else ""


def _asset_src(path: str) -> str:
    asset = Path(path)
    if not asset.exists():
        return path
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
    return f"{path}?v={digest}"


if __name__ == "__main__":
    raise SystemExit(main())
