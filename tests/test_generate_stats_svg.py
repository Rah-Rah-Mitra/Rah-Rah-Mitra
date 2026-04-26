from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_stats_svg import build_svg, summarize  # noqa: E402


class StatsSvgTests(unittest.TestCase):
    def test_summarize_counts_owned_work_repos_and_public_activity(self) -> None:
        repos = [
            {
                "name": "Rah-Rah-Mitra",
                "fork": False,
                "language": "Python",
                "stargazers_count": 99,
                "forks_count": 12,
                "open_issues_count": 4,
            },
            {
                "name": "Arcane",
                "fork": False,
                "language": "Rust",
                "stargazers_count": 3,
                "forks_count": 1,
                "open_issues_count": 2,
            },
            {
                "name": "Portfolio",
                "fork": False,
                "language": "TypeScript",
                "stargazers_count": 5,
                "forks_count": 2,
                "open_issues_count": 0,
            },
            {
                "name": "Forked-Tool",
                "fork": True,
                "language": "Go",
                "stargazers_count": 7,
                "forks_count": 8,
                "open_issues_count": 9,
            },
        ]
        events = [{"type": "PushEvent"}, {"type": "IssuesEvent"}, {"type": "PushEvent"}]

        metrics = summarize("Rah-Rah-Mitra", repos, events, contributions=1234)

        self.assertEqual(metrics["owned_repos"], 2)
        self.assertEqual(metrics["total_stars"], 8)
        self.assertEqual(metrics["total_forks"], 3)
        self.assertEqual(metrics["total_issues"], 2)
        self.assertEqual(metrics["contributions"], 1234)
        self.assertEqual(metrics["recent_pushes"], 2)
        self.assertIn("Rust (1)", metrics["language_label"])
        self.assertIn("TypeScript (1)", metrics["language_label"])

    def test_build_svg_uses_two_sections_and_removes_signal_panel(self) -> None:
        user = {
            "name": "Rahul Mitra",
            "followers": 4,
            "following": 18,
            "public_repos": 18,
        }
        metrics = {
            "owned_repos": 11,
            "total_stars": 1,
            "total_forks": 0,
            "total_issues": 2,
            "language_label": "Python (4) / Rust (2) / Jupyter Notebook (2)",
            "contributions": 837,
            "recent_pushes": 40,
        }

        svg = build_svg("Rah-Rah-Mitra", user, metrics, offline=False)

        self.assertIn('width="1100" height="460"', svg)
        self.assertIn("GitHub Snapshot", svg)
        self.assertIn("Known Tech Stack", svg)
        self.assertIn("Rust", svg)
        self.assertIn("React", svg)
        self.assertIn("Docker/Compose", svg)
        self.assertIn(">LIVE</text>", svg)
        self.assertNotIn("Live profile snapshot", svg)
        self.assertNotIn("Signal", svg)


if __name__ == "__main__":
    unittest.main()
