# The Four Scapes of Cinema

**INFO 230 — Digital Humanities / Cultural Analytics · UC Berkeley, Spring 2026 · Moe Alhassan**

A network analysis of 1,778 films and 16,000+ film professionals, mapping collaboration, geographic origin, financial flows, and genre through Arjun Appadurai's framework of global cultural flows.

**[View the interactive site →](https://moealhassan.github.io/four-scapes-of-cinema/)**

### Research Questions

1. Do directors who collaborate with geographically diverse casts produce higher ratings and/or ROI?
2. Do tightly-knit collaboration clusters produce better-rated films?
3. Where do the four network layers converge and diverge — and what do these disjunctures reveal?

### Key Findings

- **The diversity paradox is a budget effect.** Geographic diversity correlates with lower ratings, but 61% of this is explained by budget.
- **International and domestic cinema are structurally different worlds.** NMI = 0.24 between cross-origin and same-origin networks.
- **Tight circles make better films.** Writer clustering is the strongest predictor of film quality (β = 7.03, p < 0.001).
- **Financial returns are decoupled from network structure.** No network metric significantly predicts ROI.

### Project Structure

```
src/             # Python analysis pipeline (8 scripts)
site-v2/         # Interactive site source (Vite + D3)
notebook.ipynb   # Companion analysis notebook
docs/            # GitHub Pages deployment
```

### Data Sources

- [IMDb Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/)
- [TMDB API](https://www.themoviedb.org/) (budget/revenue)
- [Wikidata](https://www.wikidata.org/) (geographic origins via SPARQL)

### Setup

```bash
pip install -r requirements.txt
cd src && python 01_download_data.py  # Download IMDb datasets
```

Run scripts `01` through `08` sequentially to reproduce the full pipeline.
