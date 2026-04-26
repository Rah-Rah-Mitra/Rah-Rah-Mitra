"""Shared GitHub profile data helpers for README asset generation."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

API_BASE = "https://api.github.com"
API_VERSION = "2026-03-10"
CONTRIB_URL = "https://github.com/users/{username}/contributions"
GRAPHQL_URL = "https://api.github.com/graphql"
USER_AGENT = "rah-rah-mitra-readme-generator"

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
TD_ID_RE = re.compile(r"contribution-day-component-(?P<row>\d+)-(?P<col>\d+)")
TOOLTIP_COUNT_RE = re.compile(r"^(?P<count>[\d,]+) contributions? on ")


@dataclass(frozen=True)
class ContributionCell:
    date: str
    level: int
    count: int
    col: int
    row: int


@dataclass(frozen=True)
class ContributionSnapshot:
    cells: list[ContributionCell]
    total: int
    source: str


class ContributionFetchError(RuntimeError):
    """Raised when live contribution data cannot be fetched or parsed."""


class _ContributionHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.td_cells: list[dict[str, Any]] = []
        self.rect_cells: list[dict[str, Any]] = []
        self._cells_by_id: dict[str, dict[str, Any]] = {}
        self._tooltip_for: str | None = None
        self._tooltip_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._tooltip_for is not None:
            self._tooltip_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "tool-tip" or self._tooltip_for is None:
            return

        cell = self._cells_by_id.get(self._tooltip_for)
        if cell is not None:
            cell["count"] = _parse_tooltip_count("".join(self._tooltip_text))

        self._tooltip_for = None
        self._tooltip_text = []

    def _handle_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value for key, value in attrs if value is not None}
        tag = tag.lower()

        if tag == "td" and "data-date" in attr and "data-level" in attr:
            cell = self._parse_td_cell(attr)
            if cell is not None:
                self.td_cells.append(cell)
                cell_id = attr.get("id")
                if cell_id:
                    self._cells_by_id[cell_id] = cell
            return

        if tag == "rect" and "data-date" in attr and "data-level" in attr:
            cell = self._parse_rect_cell(attr)
            if cell is not None:
                self.rect_cells.append(cell)
            return

        if tag == "tool-tip":
            self._tooltip_for = attr.get("for")
            self._tooltip_text = []

    @staticmethod
    def _parse_td_cell(attr: dict[str, str]) -> dict[str, Any] | None:
        row: int
        col: int
        match = TD_ID_RE.search(attr.get("id", ""))
        if match:
            row = int(match.group("row"))
            col = int(match.group("col"))
        elif attr.get("data-ix", "").isdigit():
            col = int(attr["data-ix"])
            row = 0
        else:
            return None

        return {
            "date": attr["data-date"],
            "level": _parse_level(attr["data-level"]),
            "count": 0,
            "col": col,
            "row": row,
        }

    @staticmethod
    def _parse_rect_cell(attr: dict[str, str]) -> dict[str, Any] | None:
        try:
            return {
                "date": attr["data-date"],
                "level": _parse_level(attr["data-level"]),
                "count": 0,
                "x": float(attr.get("x", "0")),
                "y": float(attr.get("y", "0")),
            }
        except ValueError:
            return None


def fetch_user(username: str, token: str | None = None) -> dict[str, Any]:
    return get_json(f"{API_BASE}/users/{urllib.parse.quote(username)}", token)


def fetch_repos(username: str, token: str | None = None) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"{API_BASE}/users/{urllib.parse.quote(username)}/repos"
            f"?type=owner&sort=updated&per_page=100&page={page}"
        )
        batch = get_json(url, token)
        if not batch:
            return repos
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def fetch_events(username: str, token: str | None = None) -> list[dict[str, Any]]:
    return get_json(f"{API_BASE}/users/{urllib.parse.quote(username)}/events/public?per_page=100", token)


def fetch_contribution_snapshot(username: str, token: str | None = None) -> ContributionSnapshot:
    clean_token = _clean_token(token)
    errors: list[str] = []

    if clean_token:
        try:
            return _fetch_contributions_graphql(username, clean_token)
        except Exception as exc:  # noqa: BLE001 - fallback to public calendar is intentional.
            errors.append(f"GraphQL contribution fetch failed: {exc}")

    try:
        return _fetch_public_contributions(username)
    except Exception as exc:  # noqa: BLE001 - report all attempted sources together.
        errors.append(f"Public contribution calendar fetch failed: {exc}")

    raise ContributionFetchError("; ".join(errors) or "No contribution data source succeeded")


def parse_contribution_cells(markup: str) -> list[ContributionCell]:
    parser = _ContributionHTMLParser()
    parser.feed(markup)

    if parser.td_cells:
        return [
            ContributionCell(
                date=cell["date"],
                level=cell["level"],
                count=cell["count"],
                col=cell["col"],
                row=cell["row"],
            )
            for cell in sorted(parser.td_cells, key=lambda cell: (cell["col"], cell["row"]))
        ]

    if parser.rect_cells:
        xs = sorted({cell["x"] for cell in parser.rect_cells})
        ys = sorted({cell["y"] for cell in parser.rect_cells})
        x_index = {x: i for i, x in enumerate(xs)}
        y_index = {y: i for i, y in enumerate(ys)}
        return [
            ContributionCell(
                date=cell["date"],
                level=cell["level"],
                count=cell["count"],
                col=x_index[cell["x"]],
                row=y_index[cell["y"]],
            )
            for cell in sorted(parser.rect_cells, key=lambda cell: (cell["x"], cell["y"]))
        ]

    return []


def get_json(url: str, token: str | None = None) -> Any:
    req = urllib.request.Request(url, headers=_headers(token=token))
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def owned_work_repos(username: str, repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        repo
        for repo in repos
        if not repo.get("fork") and repo.get("name", "").casefold() != username.casefold()
    ]


def _fetch_contributions_graphql(username: str, token: str) -> ContributionSnapshot:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
                weekday
              }
            }
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8"),
        headers=_headers(token=token, content_type="application/json"),
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("errors"):
        raise ContributionFetchError(payload["errors"][0].get("message", "GraphQL returned errors"))

    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    cells: list[ContributionCell] = []
    for col, week in enumerate(calendar["weeks"]):
        for day in week["contributionDays"]:
            cells.append(
                ContributionCell(
                    date=day["date"],
                    level=LEVEL_MAP.get(day["contributionLevel"], 0),
                    count=int(day["contributionCount"]),
                    col=col,
                    row=int(day["weekday"]),
                )
            )

    if not cells:
        raise ContributionFetchError("GraphQL returned no contribution cells")

    return ContributionSnapshot(
        cells=sorted(cells, key=lambda cell: (cell.col, cell.row)),
        total=int(calendar.get("totalContributions") or sum(cell.count for cell in cells)),
        source="graphql",
    )


def _fetch_public_contributions(username: str) -> ContributionSnapshot:
    req = urllib.request.Request(
        CONTRIB_URL.format(username=urllib.parse.quote(username)),
        headers=_headers(accept="text/html"),
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        markup = response.read().decode("utf-8")

    cells = parse_contribution_cells(markup)
    if not cells:
        raise ContributionFetchError("No contribution cells found in public calendar HTML")

    return ContributionSnapshot(cells=cells, total=sum(cell.count for cell in cells), source="public-html")


def _headers(
    *,
    token: str | None = None,
    accept: str = "application/vnd.github+json",
    content_type: str | None = None,
) -> dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": API_VERSION,
    }
    clean_token = _clean_token(token)
    if clean_token:
        headers["Authorization"] = f"Bearer {clean_token}"
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _clean_token(token: str | None) -> str | None:
    if token is None:
        return None
    token = token.strip()
    return token or None


def _parse_level(value: str) -> int:
    if value.isdigit():
        return max(0, min(4, int(value)))
    return LEVEL_MAP.get(value, 0)


def _parse_tooltip_count(text: str) -> int:
    text = " ".join(text.split())
    match = TOOLTIP_COUNT_RE.match(text)
    if not match:
        return 0
    return int(match.group("count").replace(",", ""))
