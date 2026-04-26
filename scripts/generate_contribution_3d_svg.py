#!/usr/bin/env python3
"""Generate a 3D-style contribution graph SVG from GitHub's native contributions feed."""

from __future__ import annotations

import argparse
import re
import urllib.error
import urllib.request
from pathlib import Path

SOURCE_TMPL = "https://github.com/users/{username}/contributions"
RECT_RE = re.compile(
    r'<rect[^>]*data-date="(?P<date>[^"]+)"[^>]*data-level="(?P<level>[0-4])"[^>]*x="(?P<x>\d+)"[^>]*y="(?P<y>\d+)"[^>]*/?>'
)


def fetch_contribution_svg(username: str) -> str:
    req = urllib.request.Request(
        SOURCE_TMPL.format(username=username),
        headers={"User-Agent": "rah-rah-mitra-contrib-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_cells(svg: str):
    cells = []
    for m in RECT_RE.finditer(svg):
        cells.append(
            {
                "date": m.group("date"),
                "level": int(m.group("level")),
                "x": int(m.group("x")),
                "y": int(m.group("y")),
            }
        )
    return cells


def iso_bar(x: float, y: float, w: float, d: float, h: float, color_top: str, color_left: str, color_right: str) -> str:
    top = f"{x},{y-h} {x+w},{y-h-d*0.55} {x+w+d},{y-h} {x+d},{y-h+d*0.55}"
    left = f"{x},{y-h} {x+d},{y-h+d*0.55} {x+d},{y+d*0.55} {x},{y}"
    right = f"{x+d},{y-h+d*0.55} {x+w+d},{y-h} {x+w+d},{y} {x+d},{y+d*0.55}"
    return (
        f'<polygon points="{left}" fill="{color_left}"/>'
        f'<polygon points="{right}" fill="{color_right}"/>'
        f'<polygon points="{top}" fill="{color_top}"/>'
    )


def build_svg(username: str, cells, offline: bool) -> str:
    # GitHub contribution rect spacing is typically 13px (x,y)
    xs = sorted({c["x"] for c in cells})
    ys = sorted({c["y"] for c in cells})
    x_index = {x: i for i, x in enumerate(xs)}
    y_index = {y: i for i, y in enumerate(ys)}

    cell_w = 10
    cell_d = 5
    base_x = 36
    base_y = 330
    dx = 11
    dy = 7
    row_drop = 15

    shades = {
        0: ("#0f172a", "#0b1220", "#111a2d", 2),
        1: ("#1d4ed8", "#1e3a8a", "#1d4ed8", 8),
        2: ("#0ea5e9", "#0369a1", "#0284c7", 14),
        3: ("#22d3ee", "#0891b2", "#06b6d4", 20),
        4: ("#a78bfa", "#7c3aed", "#8b5cf6", 26),
    }

    bars = []
    for cell in sorted(cells, key=lambda c: (y_index[c["y"]], x_index[c["x"]])):
        col = x_index[cell["x"]]
        row = y_index[cell["y"]]
        x = base_x + col * dx + row * 3
        y = base_y - col * dy + row * row_drop
        top, left, right, h = shades[cell["level"]]
        bars.append(iso_bar(x, y, cell_w, cell_d, h, top, left, right))

    note = "Offline preview" if offline else "Derived from github.com/users/<user>/contributions"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460" role="img" aria-labelledby="title desc">
  <title id="title">{username} 3D contribution graph</title>
  <desc id="desc">Isometric 3D visualization of GitHub contributions.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
  </defs>
  <rect width="1100" height="460" rx="24" fill="url(#bg)"/>
  <text x="34" y="48" fill="#e2e8f0" font-size="28" font-weight="700">GitHub Contribution Graph · 3D Isometric View</text>
  <text x="34" y="78" fill="#93c5fd" font-size="16">{username}</text>
  <text x="34" y="430" fill="#64748b" font-size="13">{note}</text>
  {''.join(bars)}
</svg>
'''


def offline_cells():
    cells = []
    for col in range(24):
        for row in range(7):
            level = (col * 3 + row * 2) % 5
            cells.append({"x": col * 13, "y": row * 13, "level": level, "date": "offline"})
    return cells


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a 3D contribution graph SVG")
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    try:
        cells = offline_cells() if args.offline else parse_cells(fetch_contribution_svg(args.username))
    except urllib.error.URLError:
        return 1

    svg = build_svg(args.username, cells, args.offline)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
