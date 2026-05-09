#!/usr/bin/env python3
"""Create a composite annual chart similar to the provided ggplot example.

Produces a stacked bar chart of reports by year colored by country, draws a
vertical line at 1993, annotates 1985 as the X-Files start, and insets a pie
chart of reported shapes (using an inferno colormap). Reads the cleaned CSV
at `data/processed/ufo_sightings_clean.csv` and writes `site/figures/annual_by_year.png`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_CSV = ROOT / "data" / "processed" / "ufo_sightings_clean.csv"
OUT_DIR = ROOT / "site" / "figures"
OUT_PATH = OUT_DIR / "annual_by_year.png"


def load_processed(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def make_composite(df: pd.DataFrame, anno_year: int = 1985) -> None:
    # base style and font sizes
    plt.style.use("ggplot")
    mpl.rcParams.update({
        "figure.facecolor": "#f7f7f7",
        "axes.facecolor": "#f0f0f0",
        "axes.edgecolor": "#dddddd",
        "axes.titlesize": 16,
        "axes.labelsize": 12,
        "legend.frameon": True,
    })

    # aggregate by year and country for stacked bars
    by_year_country = df.groupby(["year", "country"]).size().reset_index(name="count")
    pivot = by_year_country.pivot(index="year", columns="country", values="count").fillna(0).astype(int)
    years = pivot.index.values

    # prefer a consistent color mapping for common country codes
    country_colors = {
        "us": "#b35806",
        "unknown": "#5e3c99",
        "gb": "#f39b22",
        "de": "#66c2a5",
        "ca": "#a6d854",
        "au": "#8da0cb",
    }
    countries = list(pivot.columns)
    colors = [country_colors.get(c, mpl.cm.Paired(i / max(1, len(countries) - 1))) for i, c in enumerate(countries)]

    fig, ax = plt.subplots(figsize=(14, 6))

    # stacked bars with thin white separators
    bottom = pd.Series([0] * len(years), index=years)
    for i, country in enumerate(countries):
        vals = pivot[country]
        ax.bar(years, vals, bottom=bottom, color=colors[i], edgecolor="white", linewidth=0.25, label=country, width=0.9)
        bottom += vals

    ax.set_xlim(years.min() - 1, years.max() + 1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Reports")
    ax.set_title("UFO sightings overview\nby year, shape, location", pad=14)

    # vertical line at 1993 and annotation for X-Files (1985)
    ax.axvline(1993, color="black", linewidth=1.8, zorder=3)
    y_max = bottom.max()
    # annotate so the arrow points directly at the 1993 line
    ax.text(
        1984.5,
        y_max * 0.93,
        "X-Files\nTV-show starts",
        ha="left",
        va="center",
        color="black",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#dddddd", lw=0.5),
        zorder=5,
    )
    arrow_start_x = 1981.5
    arrow_start_y = y_max * 0.905
    arrow_tip_x = 1993
    arrow_tip_y = y_max * 0.89
    ax.plot([arrow_start_x, arrow_tip_x], [arrow_start_y, arrow_tip_y], color="black", lw=1.1, zorder=4)
    ax.plot(arrow_tip_x, arrow_tip_y, marker=">", color="black", markersize=8, zorder=5)

    ax.set_ylim(0, max(y_max * 1.07, 10))

    # cleaner legend on right with boxed background
    leg = ax.legend(title="country", bbox_to_anchor=(1.02, 0.9), loc="upper left", framealpha=1)
    leg.get_frame().set_edgecolor("#e0e0e0")

    # inset pie (shapes) — show top 10 shapes for clarity so the list stays compact
    shapes = df["shape_clean"].fillna("unknown")
    shape_counts = shapes.value_counts()
    top_n = 10
    top = shape_counts.iloc[:top_n]
    if len(shape_counts) > top_n:
        top["other"] = shape_counts.iloc[top_n:].sum()

    n_shapes = len(top)
    inf_cmap = mpl.colormaps.get_cmap("inferno") if hasattr(mpl, 'colormaps') else mpl.cm.get_cmap("inferno")
    shape_colors = [inf_cmap(i / max(1, n_shapes - 1)) for i in range(n_shapes)]

    inset_ax = fig.add_axes([0.04, 0.60, 0.14, 0.23])  # pie only
    wedges, texts = inset_ax.pie(
        top.values,
        colors=shape_colors,
        wedgeprops={"edgecolor": "white", "linewidth": 0.25},
        radius=1.0,
    )
    inset_ax.set_aspect('equal')
    inset_ax.set_title("Top reported shapes", fontsize=10, pad=2)

    # dedicated legend panel keeps the shape list inside the chart area
    legend_ax = fig.add_axes([0.16, 0.58, 0.20, 0.28])
    legend_ax.axis("off")
    legend_labels = [f"{s} ({top[s]})" for s in top.index]
    y_positions = list(reversed([0.05 + i * 0.086 for i in range(len(legend_labels))]))
    for y, label, color in zip(y_positions, legend_labels, shape_colors):
        legend_ax.add_patch(
            plt.Rectangle((0.0, y - 0.018), 0.06, 0.03, transform=legend_ax.transAxes, facecolor=color, edgecolor="none")
        )
        legend_ax.text(0.08, y, label, transform=legend_ax.transAxes, fontsize=8, va="center", ha="left")

    plt.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=220, bbox_inches='tight')
    print(f"Wrote composite figure to {OUT_PATH}")


def parse_args():
    p = argparse.ArgumentParser(description="Create composite annual UFO plot (stacked by country + inset pie of shapes)")
    p.add_argument("--anno-year", type=int, default=1985, help="Year for the X-Files annotation")
    return p.parse_args()


def main():
    args = parse_args()
    if not PROCESSED_CSV.exists():
        raise SystemExit(f"Missing processed CSV: {PROCESSED_CSV} — run `python scripts/build_data.py` first")
    df = load_processed(PROCESSED_CSV)
    make_composite(df, anno_year=args.anno_year)


if __name__ == "__main__":
    main()
