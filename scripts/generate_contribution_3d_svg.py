#!/usr/bin/env python3
"""Generate a centered 3D-style contribution graph SVG from GitHub contributions."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from html import escape
from pathlib import Path

from github_profile_data import ContributionCell, ContributionFetchError, fetch_contribution_snapshot


def bar_symbol(level: int, w: float, d: float, h: float, color_top: str, color_left: str, color_right: str) -> str:
    top = f"0,{-h} {w},{-h-d*0.55} {w+d},{-h} {d},{-h+d*0.55}"
    left = f"0,{-h} {d},{-h+d*0.55} {d},{d*0.55} 0,0"
    right = f"{d},{-h+d*0.55} {w+d},{-h} {w+d},0 {d},{d*0.55}"
    return (
        f'<g id="bar-{level}">'
        f'<polygon points="{left}" fill="{color_left}"/>'
        f'<polygon points="{right}" fill="{color_right}"/>'
        f'<polygon points="{top}" fill="{color_top}"/>'
        "</g>"
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
                "level": cell.level,
                "date": cell.date,
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
    origin_y = (height - graph_h) / 2 - min_y - 8

    bars = []
    positioned = []
    for bar in sorted(geom, key=lambda item: (item["y"], item["x"])):
        x = origin_x + bar["x"]
        y = origin_y + bar["y"]
        positioned.append({**bar, "screen_x": x, "screen_y": y})
        bars.append(
            f'<use href="#bar-{bar["level"]}" transform="translate({fmt(x)} {fmt(y)})"/>'
        )

    bar_defs = "".join(
        bar_symbol(level, cell_w, cell_d, style[3], style[0], style[1], style[2]) for level, style in shades.items()
    )
    legend_items = []
    lx, ly = 930, 68
    for level in range(5):
        top, _, _, _, label = shades[level]
        legend_items.append(
            f'<rect x="{lx}" y="{ly + level * 24}" width="14" height="14" rx="3" fill="{top}"/>'
            f'<text x="{lx + 21}" y="{ly + 12 + level * 24}" fill="#cbd5e1" font-size="13">{label}</text>'
        )

    total = sum(cell.count for cell in cells)
    active_days = sum(1 for cell in cells if cell.count > 0 or cell.level > 0)
    date_range = visible_date_range(cells)
    month_labels = build_month_labels(positioned)
    live_label = "PREVIEW" if offline else "LIVE"
    safe_username = escape(username)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460" role="img" aria-labelledby="title desc">
  <title id="title">{safe_username} 3D contribution graph</title>
  <desc id="desc">Centered isometric 3D visualization of GitHub contributions with legend.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    {bar_defs}
  </defs>
  <rect width="1100" height="460" rx="24" fill="url(#bg)"/>
  <text x="34" y="52" fill="#e2e8f0" font-size="32" font-weight="700">GitHub Contribution Graph - 3D Isometric View</text>
  <text x="34" y="84" fill="#93c5fd" font-size="18">{safe_username}</text>
  <text x="34" y="120" fill="#5eead4" font-size="22" font-weight="700">{total:,} contributions</text>
  <text x="34" y="148" fill="#cbd5e1" font-size="16">{active_days} active days in the visible calendar</text>
  <text x="34" y="174" fill="#64748b" font-size="15">{escape(date_range)}</text>
  <g transform="translate(34 398)">
    <rect width="88" height="26" rx="13" fill="#052e2b" stroke="#22d3ee" opacity="0.92">
      <animate attributeName="opacity" values="0.62;1;0.62" dur="2.2s" repeatCount="indefinite"/>
    </rect>
    <circle cx="15" cy="13" r="4" fill="#5eead4">
      <animate attributeName="opacity" values="0.35;1;0.35" dur="1.4s" repeatCount="indefinite"/>
    </circle>
    <text x="28" y="17" fill="#d1fae5" font-size="12" font-weight="700">{live_label}</text>
  </g>
  <text x="930" y="52" fill="#93c5fd" font-size="15">Legend</text>
  {''.join(legend_items)}
  <g id="contribution-graph">
    <animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" dur="8s" repeatCount="indefinite"/>
    {''.join(bars)}
    <g id="month-labels">{''.join(month_labels)}</g>
  </g>
</svg>
'''


def fmt(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def visible_date_range(cells: list[ContributionCell]) -> str:
    dates = [parsed for cell in cells if (parsed := parse_date(cell.date))]
    if not dates:
        return "Generated contribution preview"
    start = min(dates)
    end = max(dates)
    return f"{start.strftime('%b %d, %Y')} - {end.strftime('%b %d, %Y')}"


def build_month_labels(positioned: list[dict[str, object]]) -> list[str]:
    first_by_month: dict[tuple[int, int], dict[str, object]] = {}
    for item in sorted(positioned, key=lambda value: str(value["date"])):
        parsed = parse_date(str(item["date"]))
        if parsed is None:
            continue
        first_by_month.setdefault((parsed.year, parsed.month), {**item, "parsed": parsed})

    months = list(first_by_month.values())
    if not months:
        return []

    front_edge_by_col: dict[int, dict[str, object]] = {}
    for item in positioned:
        col = int(item["col"])
        current = front_edge_by_col.get(col)
        if current is None or int(item["row"]) > int(current["row"]):
            front_edge_by_col[col] = item

    selected = months[-12:] if len(months) > 12 else months
    labels = []
    for item in selected:
        parsed = item["parsed"]
        axis_point = front_edge_by_col.get(int(item["col"]), item)
        labels.append(
            f'<text x="{fmt(float(axis_point["screen_x"]) + 15)}" y="{fmt(float(axis_point["screen_y"]) + 24)}" '
            'fill="#64748b" font-size="11" text-anchor="middle">'
            f"{parsed.strftime('%b')}"
            "</text>"
        )
    return labels


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


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
