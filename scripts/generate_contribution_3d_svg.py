#!/usr/bin/env python3
"""Generate a centered 3D-style contribution graph SVG from GitHub contributions."""

from __future__ import annotations

import argparse
import os
import sys
from html import escape
from pathlib import Path

from github_profile_data import ContributionCell, ContributionFetchError, fetch_contribution_snapshot


def iso_bar(
    x: float,
    y: float,
    w: float,
    d: float,
    h: float,
    color_top: str,
    color_left: str,
    color_right: str,
) -> str:
    top = f"{x},{y-h} {x+w},{y-h-d*0.55} {x+w+d},{y-h} {x+d},{y-h+d*0.55}"
    left = f"{x},{y-h} {x+d},{y-h+d*0.55} {x+d},{y+d*0.55} {x},{y}"
    right = f"{x+d},{y-h+d*0.55} {x+w+d},{y-h} {x+w+d},{y} {x+d},{y+d*0.55}"
    return (
        f'<polygon points="{left}" fill="{color_left}"/>'
        f'<polygon points="{right}" fill="{color_right}"/>'
        f'<polygon points="{top}" fill="{color_top}"/>'
    )


def build_svg(username: str, cells: list[ContributionCell], offline: bool, source: str = "offline") -> str:
    cols = sorted({cell.col for cell in cells})
    rows = sorted({cell.row for cell in cells})
    col_index = {col: i for i, col in enumerate(cols)}
    row_index = {row: i for i, row in enumerate(rows)}

    cell_w, cell_d = 9, 5
    dx, dy, row_shift = 11, 5.6, 3
    row_drop = 13

    shades = {
        0: ("#0f172a", "#0b1220", "#111a2d", 2, "No activity"),
        1: ("#1d4ed8", "#1e3a8a", "#1d4ed8", 8, "Low"),
        2: ("#0ea5e9", "#0369a1", "#0284c7", 14, "Moderate"),
        3: ("#22d3ee", "#0891b2", "#06b6d4", 20, "High"),
        4: ("#a78bfa", "#7c3aed", "#8b5cf6", 26, "Peak"),
    }

    geom = []
    for cell in cells:
        col = col_index[cell.col]
        row = row_index[cell.row]
        x = col * dx + row * row_shift
        y = -col * dy + row * row_drop
        top, left, right, height, _ = shades[cell.level]
        geom.append(
            {
                "x": x,
                "y": y,
                "height": height,
                "top": top,
                "left": left,
                "right": right,
                "col": col,
                "row": row,
            }
        )

    min_x = min(bar["x"] for bar in geom)
    max_x = max(bar["x"] + cell_w + cell_d for bar in geom)
    min_y = min(bar["y"] - bar["height"] for bar in geom)
    max_y = max(bar["y"] + cell_d * 0.55 for bar in geom)

    width, height = 1100, 460
    graph_w = max_x - min_x
    graph_h = max_y - min_y
    origin_x = (width - graph_w) / 2 - min_x
    origin_y = (height - graph_h) / 2 - min_y + 26

    bars = []
    for bar in sorted(geom, key=lambda item: (item["y"], item["x"])):
        bars.append(
            iso_bar(
                origin_x + bar["x"],
                origin_y + bar["y"],
                cell_w,
                cell_d,
                bar["height"],
                bar["top"],
                bar["left"],
                bar["right"],
            )
        )

    legend_items = []
    lx, ly = 820, 118
    for level in range(5):
        top, _, _, _, label = shades[level]
        legend_items.append(
            f'<rect x="{lx}" y="{ly + level * 28}" width="16" height="16" rx="4" fill="{top}"/>'
            f'<text x="{lx + 24}" y="{ly + 13 + level * 28}" fill="#cbd5e1" font-size="13">{label}</text>'
        )

    total = sum(cell.count for cell in cells)
    active_days = sum(1 for cell in cells if cell.count > 0 or cell.level > 0)
    note = "Offline preview" if offline else f"Live GitHub contribution snapshot via {source}"
    safe_username = escape(username)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460" role="img" aria-labelledby="title desc">
  <title id="title">{safe_username} 3D contribution graph</title>
  <desc id="desc">Centered isometric 3D visualization of GitHub contributions with legend.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
  </defs>
  <rect width="1100" height="460" rx="24" fill="url(#bg)"/>
  <text x="34" y="48" fill="#e2e8f0" font-size="28" font-weight="700">GitHub Contribution Graph - 3D Isometric View</text>
  <text x="34" y="78" fill="#93c5fd" font-size="16">{safe_username}</text>
  <text x="34" y="110" fill="#5eead4" font-size="18" font-weight="700">{total:,} contributions</text>
  <text x="34" y="134" fill="#cbd5e1" font-size="14">{active_days} active days in the visible calendar</text>
  <text x="820" y="94" fill="#93c5fd" font-size="15">Legend</text>
  {''.join(legend_items)}
  <text x="34" y="430" fill="#64748b" font-size="13">{escape(note)}</text>
  {''.join(bars)}
</svg>
'''


def offline_cells() -> list[ContributionCell]:
    cells = []
    for col in range(24):
        for row in range(7):
            level = (col * 3 + row * 2) % 5
            cells.append(
                ContributionCell(
                    date="offline",
                    level=level,
                    count=level * 3,
                    col=col,
                    row=row,
                )
            )
    return cells


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a 3D contribution graph SVG")
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--token", default=os.getenv("GH_STATS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    if args.offline:
        cells = offline_cells()
        source = "offline"
    else:
        try:
            snapshot = fetch_contribution_snapshot(args.username, args.token)
        except ContributionFetchError as exc:
            print(f"Failed to fetch contribution cells: {exc}", file=sys.stderr)
            return 1
        cells = snapshot.cells
        source = snapshot.source

    if not cells:
        print("No contribution cells found; refusing to write an empty live graph.", file=sys.stderr)
        return 1

    svg = build_svg(args.username, cells, args.offline, source)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
