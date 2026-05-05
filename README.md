# Seeing Things

Static narrative visualization website and explainer notebook for a social-data analysis of UFO sighting reports.

## Story

**UFO sightings are not only a mystery in the sky. They are also a map of human reporting behavior.**

The website treats the dataset as report data, not verified event data. It focuses on temporal patterns, shape language, human rhythms, geographic bias, and hotspot persistence.

## Data

The project cites Maven Analytics as the course-facing dataset page:

- https://mavenanalytics.io/data-playground/ufo-sightings

Maven links the data lineage to the National UFO Reporting Center/Kaggle source. The raw CSV used here is the archived NUFORC scrubbed file from Zenodo:

- https://zenodo.org/records/1205624

The raw CSV is preserved at `data/raw/ufo_sightings_raw.csv`. The generated cleaned file is `data/processed/ufo_sightings_clean.csv`.

Important provenance note: Maven describes the dataset as `1949-2014`, but the raw archived file contains reports from `1906-2014`. The notebook and website discuss this mismatch as a data-quality issue.

## Rebuild Data

```bash
python3 scripts/build_data.py
```

This regenerates:

- `data/processed/ufo_sightings_clean.csv`
- compact JSON files in `site/data/`

## Run Website

Because the site loads local JSON files, serve it over a local HTTP server:

```bash
python3 -m http.server 8000 --directory site
```

Open:

```text
http://localhost:8000
```

## Notebook

The explainer notebook is at `notebooks/explainer.ipynb`. It follows the course structure: Motivation, Basic Stats, Data Analysis, Genre, Visualizations, Discussion, Contributions, and References.

A copy is also placed at `site/notebooks/explainer.ipynb` so the website's notebook link works when serving the `site/` directory directly.
