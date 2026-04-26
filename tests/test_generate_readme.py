from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_readme import build_readme  # noqa: E402


class ReadmeGeneratorTests(unittest.TestCase):
    def test_build_readme_uses_centered_svg_sections_and_link_buttons(self) -> None:
        readme = build_readme("Rah-Rah-Mitra", {"blog": "https://rahul-mitra.vercel.app/"})

        self.assertIn("assets/hero-geometry.svg?v=", readme)
        self.assertIn("assets/link-github.svg?v=", readme)
        self.assertIn("assets/link-portfolio.svg?v=", readme)
        self.assertIn("assets/link-linkedin.svg?v=", readme)
        self.assertIn('<a href="https://github.com/Rah-Rah-Mitra">', readme)
        self.assertIn('<a href="https://rahul-mitra.vercel.app/">', readme)
        self.assertIn('<a href="https://www.linkedin.com/in/rahulmitra-dev/">', readme)
        self.assertNotIn("##", readme)
        self.assertNotIn("[GitHub]", readme)
        self.assertNotIn("Fellow coder", readme)


if __name__ == "__main__":
    unittest.main()
