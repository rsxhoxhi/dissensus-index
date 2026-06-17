# The Dissensus Index

**A quarterly record of art controversy**

dissensusindex.com · Founded Summer Solstice, 2026

---

The Dissensus Index is a structured, longitudinal instrument tracking disputes involving artworks, artists, institutions, and cultural policy. Each case is assigned a stable identifier and followed through a defined five-stage system from emergence through resolution.

The Index publishes four times a year, keyed to the solstices and equinoxes.

## Structure

```
/
├── index.html          # Homepage / docket
├── case.html           # Case detail (dynamic, loads from data/)
├── about.html          # About the Index
├── methodology.html    # Methodology v1.0
├── cite.html           # How to cite
├── essay-hungary.html  # Issue No. 1 lead essay
├── essay-pattern.html  # Issue No. 1 pattern claim
├── css/style.css       # Stylesheet
├── data/cases.json     # Full case dataset
└── netlify.toml        # Netlify configuration
```

## Data

`data/cases.json` contains all cases with the following fields:
- `id` — stable ACI identifier (e.g. ACI-001)
- `title` — artwork or controversy name
- `artist`, `institution`, `country`, `governance_type`
- `date_controversy`, `date_discovered`
- `description`, `outcome`
- `tags`, `court_case`, `coverage_tier`
- `source` — primary source URL
- `stage` (1–5), `stage_label`

## Methodology

See `methodology.html` or dissensusindex.com/methodology.html for full staging definitions, inclusion criteria, source protocols, and known limitations.

## License

CC BY 4.0 — see LICENSE.txt. Attribution must include "Dissensus Index" and dissensusindex.com.

## Founded by

Rebecca Shields · Richmond, Virginia · rebeccashields.net
