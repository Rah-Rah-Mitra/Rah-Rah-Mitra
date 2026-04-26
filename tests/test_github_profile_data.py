from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from github_profile_data import parse_contribution_cells  # noqa: E402


class ContributionParserTests(unittest.TestCase):
    def test_parses_current_github_td_calendar_cells_and_counts(self) -> None:
        markup = """
        <td tabindex="0" data-ix="10" data-date="2026-04-20"
            id="contribution-day-component-1-10" data-level="3"
            role="gridcell" class="ContributionCalendar-day"></td>
        <tool-tip for="contribution-day-component-1-10">1,234 contributions on April 20th.</tool-tip>
        <td tabindex="0" data-ix="10" data-date="2026-04-21"
            id="contribution-day-component-2-10" data-level="0"
            role="gridcell" class="ContributionCalendar-day"></td>
        <tool-tip for="contribution-day-component-2-10">No contributions on April 21st.</tool-tip>
        """

        cells = parse_contribution_cells(markup)

        self.assertEqual(len(cells), 2)
        self.assertEqual(cells[0].date, "2026-04-20")
        self.assertEqual(cells[0].row, 1)
        self.assertEqual(cells[0].col, 10)
        self.assertEqual(cells[0].level, 3)
        self.assertEqual(cells[0].count, 1234)
        self.assertEqual(cells[1].count, 0)

    def test_keeps_legacy_rect_calendar_support(self) -> None:
        markup = """
        <svg>
          <rect data-date="2026-04-20" data-level="2" x="13" y="0"/>
          <rect data-date="2026-04-21" data-level="1" x="13" y="13"/>
          <rect data-date="2026-04-27" data-level="4" x="26" y="0"/>
        </svg>
        """

        cells = parse_contribution_cells(markup)

        self.assertEqual([(cell.col, cell.row, cell.level) for cell in cells], [(0, 0, 2), (0, 1, 1), (1, 0, 4)])


if __name__ == "__main__":
    unittest.main()
