<div align="center">
  <img src="assets/hero-geometry.svg" width="100%" alt="Animated geometric profile header" />
</div>

## 👋 Hi, I'm Rahul Mitra

I build at the intersection of **Cybersecurity**, **Software Engineering**, and **Data Science**.

<div align="center">
  <a href="https://www.linkedin.com/in/rahulmitra-dev/" target="_blank">
    <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" />
  </a>
  <a href="https://rahul-mitra.vercel.app/" target="_blank">
    <img src="https://img.shields.io/badge/Portfolio-255E63?style=for-the-badge&logo=rss&logoColor=white" alt="Portfolio" />
  </a>
</div>

---

## 🛠️ Tech Stack

<p align="center">
  <img src="https://skillicons.dev/icons?i=java,python,spring,docker,git,kubernetes,aws,mysql,postgres,redis,mongodb,idea,vscode&perline=6" alt="Skills" />
</p>

---

## 📈 Custom GitHub Stats (No third-party stats widgets)

<p align="center">
  <img src="assets/github-stats.svg" width="100%" alt="Custom animated GitHub stats" />
</p>

This stats card is generated directly from the GitHub API via `scripts/generate_stats_svg.py` and rendered as a native SVG animation.

- No external readme-stats library
- Geometric animated theme designed for GitHub README compatibility
- Auto-refresh via GitHub Actions (`.github/workflows/update-readme-stats.yml`)

> Note: In this local environment, the included card may show offline placeholder values. In GitHub Actions it refreshes with live profile data.

---

## ⚙️ Automation

- **CI check** on push/PR: validates that stats generation works and README references the custom asset.
- **Daily scheduled workflow**: updates `assets/github-stats.svg` and commits refreshed metrics.

