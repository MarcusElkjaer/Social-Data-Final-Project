#!/usr/bin/env python3
"""Build cleaned UFO sighting data and compact files for the website.

The raw file is the classic NUFORC scrubbed CSV: 11 columns, no header.
This script intentionally uses only the Python standard library so it can run
in a fresh course environment before notebook dependencies are installed.
"""

from __future__ import annotations

import csv
import html
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "ufo_sightings_raw.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
SITE_DATA_DIR = ROOT / "site" / "data"

CLEAN_PATH = PROCESSED_DIR / "ufo_sightings_clean.csv"
SUMMARY_PATH = SITE_DATA_DIR / "summary.json"

RAW_COLUMNS = [
    "datetime_raw",
    "city",
    "state",
    "country",
    "shape",
    "duration_seconds_raw",
    "duration_text",
    "comments",
    "date_posted_raw",
    "latitude_raw",
    "longitude_raw",
]

CLEAN_COLUMNS = [
    "datetime",
    "year",
    "month",
    "weekday",
    "hour",
    "city",
    "state",
    "country",
    "shape_clean",
    "duration_seconds",
    "latitude",
    "longitude",
    "comments",
]

SHAPE_ALIASES = {
    "changed": "changing",
    "changing": "changing",
    "chevron": "chevron",
    "cigar": "cigar",
    "circle": "circle",
    "cone": "cone",
    "cross": "cross",
    "cylinder": "cylinder",
    "diamond": "diamond",
    "disk": "disk",
    "egg": "egg",
    "fireball": "fireball",
    "flash": "flash",
    "formation": "formation",
    "light": "light",
    "other": "other",
    "oval": "oval",
    "rectangle": "rectangle",
    "sphere": "sphere",
    "teardrop": "teardrop",
    "triangle": "triangle",
    "unknown": "unknown",
}

COUNTRY_NAMES = {
    "us": "United States",
    "ca": "Canada",
    "gb": "United Kingdom",
    "au": "Australia",
    "de": "Germany",
}

US_STATE_NAMES = {
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas",
    "ca": "California", "co": "Colorado", "ct": "Connecticut", "de": "Delaware",
    "dc": "District of Columbia", "fl": "Florida", "ga": "Georgia", "hi": "Hawaii",
    "id": "Idaho", "il": "Illinois", "in": "Indiana", "ia": "Iowa",
    "ks": "Kansas", "ky": "Kentucky", "la": "Louisiana", "me": "Maine",
    "md": "Maryland", "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota",
    "ms": "Mississippi", "mo": "Missouri", "mt": "Montana", "ne": "Nebraska",
    "nv": "Nevada", "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico",
    "ny": "New York", "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio",
    "ok": "Oklahoma", "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island",
    "sc": "South Carolina", "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas",
    "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington",
    "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming",
}

# 2010 Census state resident population. Used as a simple denominator, not a
# historical population model.
US_STATE_POP_2010 = {
    "al": 4779736, "ak": 710231, "az": 6392017, "ar": 2915918, "ca": 37253956,
    "co": 5029196, "ct": 3574097, "de": 897934, "dc": 601723, "fl": 18801310,
    "ga": 9687653, "hi": 1360301, "id": 1567582, "il": 12830632, "in": 6483802,
    "ia": 3046355, "ks": 2853118, "ky": 4339367, "la": 4533372, "me": 1328361,
    "md": 5773552, "ma": 6547629, "mi": 9883640, "mn": 5303925, "ms": 2967297,
    "mo": 5988927, "mt": 989415, "ne": 1826341, "nv": 2700551, "nh": 1316470,
    "nj": 8791894, "nm": 2059179, "ny": 19378102, "nc": 9535483, "nd": 672591,
    "oh": 11536504, "ok": 3751351, "or": 3831074, "pa": 12702379, "ri": 1052567,
    "sc": 4625364, "sd": 814180, "tn": 6346105, "tx": 25145561, "ut": 2763885,
    "vt": 625741, "va": 8001024, "wa": 6724540, "wv": 1852994, "wi": 5686986,
    "wy": 563626,
}

STOPWORDS = {
    "the", "and", "was", "were", "with", "that", "this", "for", "from", "over",
    "then", "when", "have", "had", "saw", "seen", "sky", "object", "objects",
    "ufo", "ufos", "there", "they", "like", "looked", "very", "into", "out",
    "about", "after", "before", "while", "would", "could", "around", "above",
    "just", "one", "two", "three", "near", "north", "south", "east", "west",
}


def parse_datetime(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    adjusted = False
    if " 24:" in value:
        value = value.replace(" 24:", " 00:")
        adjusted = True
    try:
        dt = datetime.strptime(value, "%m/%d/%Y %H:%M")
    except ValueError:
        return None
    if adjusted:
        dt += timedelta(days=1)
    return dt.isoformat(timespec="minutes")


def clean_text(value: str) -> str:
    return html.unescape(value or "").replace("\n", " ").strip()


def clean_country(value: str) -> str:
    value = (value or "").strip().lower()
    return value if value else "unknown"


def clean_shape(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return "unknown"
    return SHAPE_ALIASES.get(value, "other")


def parse_float(value: str) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def valid_lat_lon(lat: float | None, lon: float | None) -> bool:
    return lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180


def hex_key(lat: float, lon: float, cell_deg: float = 2.0) -> tuple[int, int, float, float]:
    """Approximate equal-angle hex bin with row offsets.

    It is not an equal-area H3 grid, but it gives the site a stable hex-style
    aggregation without adding compiled geospatial dependencies.
    """
    row_height = cell_deg * 0.8660254
    row = math.floor((lat + 90) / row_height)
    offset = 0.5 * cell_deg if row % 2 else 0.0
    col = math.floor((lon + 180 - offset) / cell_deg)
    center_lat = -90 + (row + 0.5) * row_height
    center_lon = -180 + offset + (col + 0.5) * cell_deg
    return row, col, round(center_lat, 4), round(center_lon, 4)


def decade_for(year: int) -> int:
    return (year // 10) * 10


def words_from_comment(comment: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-z]{3,}", comment.lower())
        if word not in STOPWORDS
    ]


def load_clean_rows() -> tuple[list[dict[str, object]], Counter]:
    rows: list[dict[str, object]] = []
    issues: Counter = Counter()
    with RAW_PATH.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for raw in reader:
            if len(raw) != len(RAW_COLUMNS):
                issues["wrong_column_count"] += 1
                continue
            record = dict(zip(RAW_COLUMNS, raw))
            dt_text = parse_datetime(record["datetime_raw"])
            if not dt_text:
                issues["bad_datetime"] += 1
                continue
            dt = datetime.fromisoformat(dt_text)
            lat = parse_float(record["latitude_raw"])
            lon = parse_float(record["longitude_raw"])
            duration = parse_float(record["duration_seconds_raw"])
            if duration is None or duration < 0:
                issues["bad_duration"] += 1
                duration = None
            country = clean_country(record["country"])
            shape = clean_shape(record["shape"])
            rows.append(
                {
                    "datetime": dt_text,
                    "year": dt.year,
                    "month": dt.month,
                    "weekday": dt.strftime("%A"),
                    "hour": dt.hour,
                    "city": clean_text(record["city"]).lower(),
                    "state": (record["state"] or "").strip().lower(),
                    "country": country,
                    "shape_clean": shape,
                    "duration_seconds": "" if duration is None else round(duration, 2),
                    "latitude": "" if lat is None else lat,
                    "longitude": "" if lon is None else lon,
                    "comments": clean_text(record["comments"]),
                }
            )
            if not valid_lat_lon(lat, lon):
                issues["bad_or_missing_coordinates"] += 1
    return rows, issues


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def build() -> None:
    if not RAW_PATH.exists():
        raise SystemExit(f"Missing raw file: {RAW_PATH}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    rows, issues = load_clean_rows()
    write_csv(CLEAN_PATH, rows, CLEAN_COLUMNS)

    by_year = Counter()
    by_month_hour = Counter()
    by_shape = Counter()
    by_shape_decade = Counter()
    by_country = Counter()
    by_state = Counter()
    word_counts = Counter()
    duration_values = []
    valid_geo_rows = []
    min_year, max_year = 9999, 0

    for row in rows:
        year = int(row["year"])
        min_year = min(min_year, year)
        max_year = max(max_year, year)
        by_year[year] += 1
        by_month_hour[(int(row["month"]), int(row["hour"]))] += 1
        by_shape[str(row["shape_clean"])] += 1
        by_shape_decade[(decade_for(year), str(row["shape_clean"]))] += 1
        by_country[str(row["country"])] += 1
        if row["country"] == "us" and row["state"] in US_STATE_POP_2010:
            by_state[str(row["state"])] += 1
        if row["duration_seconds"] != "":
            duration_values.append(float(row["duration_seconds"]))
        word_counts.update(words_from_comment(str(row["comments"])))
        lat = parse_float(row["latitude"])
        lon = parse_float(row["longitude"])
        if valid_lat_lon(lat, lon):
            valid_geo_rows.append(row)

    year_data = [{"year": y, "reports": by_year[y]} for y in range(min_year, max_year + 1)]
    heatmap_data = [
        {"month": month, "hour": hour, "reports": by_month_hour[(month, hour)]}
        for month in range(1, 13)
        for hour in range(24)
    ]
    shape_data = [{"shape": shape, "reports": count} for shape, count in by_shape.most_common()]
    top_shapes = [shape for shape, _ in by_shape.most_common(8)]
    shape_decade_data = []
    for decade in range(decade_for(min_year), decade_for(max_year) + 1, 10):
        decade_total = sum(by_shape_decade[(decade, shape)] for shape in by_shape)
        for shape in top_shapes:
            count = by_shape_decade[(decade, shape)]
            shape_decade_data.append(
                {
                    "decade": decade,
                    "shape": shape,
                    "reports": count,
                    "share": 0 if decade_total == 0 else count / decade_total,
                }
            )

    country_data = [
        {
            "country": COUNTRY_NAMES.get(country, country.upper()),
            "country_code": country,
            "reports": count,
        }
        for country, count in by_country.most_common(12)
    ]
    state_data = []
    for state, count in by_state.most_common():
        pop = US_STATE_POP_2010[state]
        state_data.append(
            {
                "state": state.upper(),
                "state_name": US_STATE_NAMES[state],
                "reports": count,
                "population_2010": pop,
                "reports_per_million": count / pop * 1_000_000,
            }
        )

    hex_totals: dict[str, dict[str, object]] = {}
    hex_years: dict[str, Counter] = defaultdict(Counter)
    hex_decades: dict[str, set[int]] = defaultdict(set)
    hex_shapes: dict[str, Counter] = defaultdict(Counter)
    decade_bins: dict[int, Counter] = defaultdict(Counter)

    for row in valid_geo_rows:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        year = int(row["year"])
        decade = decade_for(year)
        r, c, center_lat, center_lon = hex_key(lat, lon)
        key = f"{r}:{c}"
        if key not in hex_totals:
            hex_totals[key] = {
                "id": key,
                "lat": center_lat,
                "lon": center_lon,
                "row": r,
                "col": c,
                "total_reports": 0,
            }
        hex_totals[key]["total_reports"] = int(hex_totals[key]["total_reports"]) + 1
        hex_years[key][year] += 1
        hex_decades[key].add(decade)
        hex_shapes[key][str(row["shape_clean"])] += 1
        decade_bins[decade][key] += 1

    observed_span = max_year - min_year + 1
    hotspot_rows = []
    for key, item in hex_totals.items():
        active_years = len(hex_years[key])
        top_shape, top_shape_count = hex_shapes[key].most_common(1)[0]
        yearly_counts = list(hex_years[key].values())
        max_year_share = max(yearly_counts) / sum(yearly_counts)
        hotspot_rows.append(
            {
                **item,
                "active_years": active_years,
                "active_decades": len(hex_decades[key]),
                "persistence_ratio": active_years / observed_span,
                "top_shape": top_shape,
                "top_shape_count": top_shape_count,
                "burstiness": max_year_share,
            }
        )
    hotspot_rows.sort(key=lambda row: (-row["active_years"], -int(row["total_reports"])))

    decade_bin_rows = []
    for decade, counts in sorted(decade_bins.items()):
        for key, count in counts.items():
            base = hex_totals[key]
            decade_bin_rows.append(
                {
                    "decade": decade,
                    "id": key,
                    "lat": base["lat"],
                    "lon": base["lon"],
                    "reports": count,
                    "total_reports": base["total_reports"],
                    "active_years": len(hex_years[key]),
                    "active_decades": len(hex_decades[key]),
                    "persistence_ratio": len(hex_years[key]) / observed_span,
                    "top_shape": hex_shapes[key].most_common(1)[0][0],
                }
            )

    duration_sorted = sorted(duration_values)
    def percentile(p: float) -> float:
        if not duration_sorted:
            return 0
        idx = int((len(duration_sorted) - 1) * p)
        return round(duration_sorted[idx], 2)

    summary = {
        "raw_rows": sum(1 for _ in RAW_PATH.open(encoding="utf-8", errors="replace")),
        "clean_rows": len(rows),
        "valid_geo_rows": len(valid_geo_rows),
        "date_range": {"min_year": min_year, "max_year": max_year},
        "maven_stated_range": "1949-2014",
        "issues": dict(issues),
        "top_country": country_data[0] if country_data else None,
        "top_shape": shape_data[0] if shape_data else None,
        "duration_seconds": {
            "median": percentile(0.5),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        },
        "top_words": [
            {"word": word, "count": count}
            for word, count in word_counts.most_common(30)
        ],
    }

    write_json(SUMMARY_PATH, summary)
    write_json(SITE_DATA_DIR / "annual_reports.json", year_data)
    write_json(SITE_DATA_DIR / "month_hour.json", heatmap_data)
    write_json(SITE_DATA_DIR / "shape_counts.json", shape_data)
    write_json(SITE_DATA_DIR / "shape_by_decade.json", shape_decade_data)
    write_json(SITE_DATA_DIR / "country_counts.json", country_data)
    write_json(SITE_DATA_DIR / "state_counts.json", state_data)
    write_json(SITE_DATA_DIR / "hotspots.json", hotspot_rows[:600])
    write_json(SITE_DATA_DIR / "hex_decade_bins.json", decade_bin_rows)

    print(f"Clean rows: {len(rows):,}")
    print(f"Valid coordinate rows: {len(valid_geo_rows):,}")
    print(f"Actual year range: {min_year}-{max_year}")
    print(f"Wrote {CLEAN_PATH}")
    print(f"Wrote website data to {SITE_DATA_DIR}")


if __name__ == "__main__":
    build()
