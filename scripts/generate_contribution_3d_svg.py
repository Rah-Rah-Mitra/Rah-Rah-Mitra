#!/usr/bin/env python3
"""Generate a centered 3D-style contribution graph SVG from GitHub contributions."""

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
    return [
        {
            "date": m.group("date"),
            "level": int(m.group("level")),
            "x": int(m.group("x")),
            "y": int(m.group("y")),
        }
        for m in RECT_RE.finditer(svg)
    ]


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
    xs = sorted({c["x"] for c in cells})
    ys = sorted({c["y"] for c in cells})
    x_index = {x: i for i, x in enumerate(xs)}
    y_index = {y: i for i, y in enumerate(ys)}

    cell_w, cell_d = 10, 5
    dx, dy, row_shift = 11, 7, 3
    row_drop = 15

    shades = {
        0: ("#0f172a", "#0b1220", "#111a2d", 2, "No activity"),
        1: ("#1d4ed8", "#1e3a8a", "#1d4ed8", 8, "Low"),
        2: ("#0ea5e9", "#0369a1", "#0284c7", 14, "Moderate"),
        3: ("#22d3ee", "#0891b2", "#06b6d4", 20, "High"),
        4: ("#a78bfa", "#7c3aed", "#8b5cf6", 26, "Peak"),
    }

    geom = []
    for cell in cells:
        col = x_index[cell["x"]]
        row = y_index[cell["y"]]
        x = col * dx + row * row_shift
        y = -col * dy + row * row_drop
        top, left, right, h, _ = shades[cell["level"]]
        geom.append((x, y, h, top, left, right, row, col))

    min_x = min(x for x, *_ in geom)
    max_x = max(x + cell_w + cell_d for x, *_ in geom)
    min_y = min(y - h for _, y, h, *_ in geom)
    max_y = max(y + cell_d * 0.55 for _, y, _, *_ in geom)

    width, height = 1100, 460
    graph_w = max_x - min_x
    graph_h = max_y - min_y
    origin_x = (width - graph_w) / 2 - min_x
    origin_y = (height - graph_h) / 2 - min_y + 28

    bars = []
    for x, y, h, top, left, right, row, col in sorted(geom, key=lambda g: (g[6], g[7])):
        bars.append(iso_bar(origin_x + x, origin_y + y, cell_w, cell_d, h, top, left, right))

    legend_items = []
    lx, ly = 820, 118
    for level in range(5):
        top, _, _, _, label = shades[level]
        legend_items.append(
            f'<rect x="{lx}" y="{ly + level*28}" width="16" height="16" rx="4" fill="{top}"/>'
            f'<text x="{lx + 24}" y="{ly + 13 + level*28}" fill="#cbd5e1" font-size="13">{label}</text>'
        )

    note = "Offline preview" if offline else "Derived from github.com/users/<user>/contributions"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460" role="img" aria-labelledby="title desc">
  <title id="title">{username} 3D contribution graph</title>
  <desc id="desc">Centered isometric 3D visualization of GitHub contributions with legend.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
  </defs>
  <rect width="1100" height="460" rx="24" fill="url(#bg)"/>
  <text x="34" y="48" fill="#e2e8f0" font-size="28" font-weight="700">GitHub Contribution Graph · 3D Isometric View</text>
  <text x="34" y="78" fill="#93c5fd" font-size="16">{username}</text>
  <text x="820" y="94" fill="#93c5fd" font-size="15">Legend</text>
  {''.join(legend_items)}
  <text x="34" y="430" fill="#64748b" font-size="13">{note}</text>
  {''.join(bars)}
</svg>
'''


def offline_cells():
    cells = []
    for col in range(24):
        for row in range(7):
            cells.append({"x": col * 13, "y": row * 13, "level": (col * 3 + row * 2) % 5, "date": "offline"})
    return cells


def empty_cells(cols: int = 24, rows: int = 7):
    cells = []
    for col in range(cols):
        for row in range(rows):
            cells.append({"x": col * 13, "y": row * 13, "level": 0, "date": "unavailable"})
    return cells


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a 3D contribution graph SVG")
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    cells = []
    if args.offline:
        cells = offline_cells()
    else:
        try:
            cells = parse_cells(fetch_contribution_svg(args.username))
        except urllib.error.URLError as exc:
            print(f"Failed to fetch contributions ({exc}); falling back to empty graph.")

    if not cells:
        print("No contribution cells found; writing an empty no-activity graph.")
        cells = empty_cells()

    svg = build_svg(args.username, cells, args.offline)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
