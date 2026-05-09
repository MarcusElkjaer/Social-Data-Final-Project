#!/usr/bin/env python3
"""Generate lightweight SVG figures for the explainer notebook."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = ROOT / "site" / "data"
FIG_DIR = ROOT / "notebooks" / "figures"
SITE_FIG_DIR = ROOT / "site" / "notebooks" / "figures"


def load(name: str):
    return json.loads((SITE_DATA / name).read_text())


def write(name: str, svg: str) -> None:
    for fig_dir in [FIG_DIR, SITE_FIG_DIR]:
        fig_dir.mkdir(parents=True, exist_ok=True)
        (fig_dir / name).write_text(svg, encoding="utf-8")


def axis_label(text: str, x: float, y: float, anchor: str = "middle") -> str:
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="label">{text}</text>'


def chart_style() -> str:
    return """
    <style>
      .bg { fill: #fffdf8; }
      .axis { stroke: #d8d0c2; stroke-width: 1; }
      .grid { stroke: #eee7da; stroke-width: 1; }
      .label { fill: #62706c; font: 12px system-ui, sans-serif; }
      .title { fill: #17201d; font: 700 18px system-ui, sans-serif; }
      .note { fill: #7a5d2a; font: 700 12px system-ui, sans-serif; }
    </style>
    """


def annual_svg() -> str:
    data = load("annual_reports.json")
    width, height = 900, 440
    left, right, top, bottom = 62, 24, 42, 48
    xs = [d["year"] for d in data]
    ys = [d["reports"] for d in data]
    min_x, max_x = min(xs), max(xs)
    max_y = max(ys)

    def sx(x):
        return left + (x - min_x) / (max_x - min_x) * (width - left - right)

    def sy(y):
        return height - bottom - y / max_y * (height - top - bottom)

    points = " ".join(f"{sx(d['year']):.1f},{sy(d['reports']):.1f}" for d in data)
    ticks = []
    for year in [1910, 1930, 1950, 1970, 1990, 2010]:
        ticks.append(f'<line x1="{sx(year):.1f}" y1="{top}" x2="{sx(year):.1f}" y2="{height-bottom}" class="grid"/>')
        ticks.append(axis_label(str(year), sx(year), height - 18))
    for value in [0, 2500, 5000, 7500]:
        y = sy(value)
        ticks.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        ticks.append(axis_label(str(value), 48, y + 4, "end"))

    band_x = sx(1995)
    band_w = sx(2005) - sx(1995)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
      {chart_style()}
      <rect width="{width}" height="{height}" class="bg"/>
      <text x="{left}" y="26" class="title">Reports by year</text>
      {"".join(ticks)}
      <rect x="{band_x:.1f}" y="{top}" width="{band_w:.1f}" height="{height-top-bottom}" fill="#f2d49c" opacity="0.45"/>
      <text x="{band_x + 8:.1f}" y="{top + 22}" class="note">online reporting era</text>
      <polyline points="{points}" fill="none" stroke="#d65d47" stroke-width="3"/>
      <line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" class="axis"/>
      <line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" class="axis"/>
    </svg>"""


def shapes_svg() -> str:
    data = load("shape_counts.json")[:10]
    width, height = 900, 440
    left, right, top, bottom = 112, 28, 42, 36
    max_v = max(d["reports"] for d in data)
    bar_h = (height - top - bottom) / len(data)
    parts = [chart_style(), f'<rect width="{width}" height="{height}" class="bg"/>', f'<text x="{left}" y="26" class="title">Top reported shapes</text>']
    for i, d in enumerate(data):
        y = top + i * bar_h + 4
        w = d["reports"] / max_v * (width - left - right)
        parts.append(axis_label(d["shape"], left - 12, y + bar_h * 0.55, "end"))
        parts.append(f'<rect x="{left}" y="{y:.1f}" width="{w:.1f}" height="{bar_h-8:.1f}" rx="3" fill="#117c78"/>')
        parts.append(axis_label(f"{d['reports']:,}", left + w + 8, y + bar_h * 0.55, "start"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(parts)}</svg>'


def heatmap_svg() -> str:
    data = load("month_hour.json")
    width, height = 900, 470
    left, right, top, bottom = 54, 28, 42, 42
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    inner_w, inner_h = width - left - right, height - top - bottom
    cell_w, cell_h = inner_w / 24, inner_h / 12
    max_v = max(d["reports"] for d in data)

    def color(value):
        t = math.sqrt(value / max_v) if max_v else 0
        r = int(255 * t + 255 * (1 - t))
        g = int(245 * (1 - t) + 98 * t)
        b = int(205 * (1 - t) + 53 * t)
        return f"rgb({r},{g},{b})"

    parts = [chart_style(), f'<rect width="{width}" height="{height}" class="bg"/>', f'<text x="{left}" y="26" class="title">Reports by month and hour</text>']
    for d in data:
        x = left + d["hour"] * cell_w
        y = top + (d["month"] - 1) * cell_h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w-1:.1f}" height="{cell_h-1:.1f}" fill="{color(d["reports"])}"/>')
    for i, month in enumerate(months):
        parts.append(axis_label(month, left - 10, top + i * cell_h + cell_h * 0.65, "end"))
    for hour in [0, 6, 12, 18, 23]:
        parts.append(axis_label(f"{hour}:00", left + hour * cell_w, height - 16))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(parts)}</svg>'


def hotspots_svg() -> str:
    data = load("hotspots.json")[:12]
    width, height = 900, 430
    left, right, top, bottom = 64, 28, 42, 52
    max_reports = max(d["total_reports"] for d in data)
    max_years = max(d["active_years"] for d in data)
    parts = [chart_style(), f'<rect width="{width}" height="{height}" class="bg"/>', f'<text x="{left}" y="26" class="title">Persistent hotspot bins: total reports vs active years</text>']
    for d in data:
        x = left + d["total_reports"] / max_reports * (width - left - right)
        y = height - bottom - d["active_years"] / max_years * (height - top - bottom)
        r = 5 + math.sqrt(d["total_reports"]) * 0.8
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#d65d47" fill-opacity="0.58" stroke="#7b2f23"/>')
    parts.append(f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" class="axis"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" class="axis"/>')
    parts.append(axis_label("total reports in bin", width / 2, height - 12))
    parts.append(axis_label("active years", 18, height / 2, "middle"))
    parts.append(axis_label("Each point is one high-persistence spatial bin.", left + 8, height - bottom - 10, "start"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(parts)}</svg>'


def city_hotspots_svg() -> str:
    data = load("city_counts.json")[:12]
    width, height = 900, 440
    left, right, top, bottom = 132, 36, 42, 36
    max_v = max(d["reports"] for d in data)
    bar_h = (height - top - bottom) / len(data)
    parts = [chart_style(), f'<rect width="{width}" height="{height}" class="bg"/>', f'<text x="{left}" y="26" class="title">Top US city hotspots</text>']
    for i, d in enumerate(data):
        y = top + i * bar_h + 4
        w = d["reports"] / max_v * (width - left - right)
        label = f'{d["city"]}, {d["state"]}'
        parts.append(axis_label(label, left - 12, y + bar_h * 0.55, "end"))
        parts.append(f'<rect x="{left}" y="{y:.1f}" width="{w:.1f}" height="{bar_h-8:.1f}" rx="3" fill="#d65d47"/>')
        parts.append(axis_label(f"{d['reports']:,}", left + w + 8, y + bar_h * 0.55, "start"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(parts)}</svg>'


def duration_by_shape_svg() -> str:
    data = load("duration_by_shape.json")[:16]
    width, height = 900, 470
    left, right, top, bottom = 112, 36, 42, 42
    max_v = max(d["median"] for d in data)
    bar_h = (height - top - bottom) / len(data)

    def minutes(seconds):
        return f"{seconds / 60:.0f}m"

    parts = [chart_style(), f'<rect width="{width}" height="{height}" class="bg"/>', f'<text x="{left}" y="26" class="title">Median duration by common shape</text>']
    for i, d in enumerate(data):
        y = top + i * bar_h + 4
        w = d["median"] / max_v * (width - left - right)
        parts.append(axis_label(d["shape"], left - 12, y + bar_h * 0.55, "end"))
        parts.append(f'<rect x="{left}" y="{y:.1f}" width="{w:.1f}" height="{bar_h-8:.1f}" rx="3" fill="#8d6b2f"/>')
        parts.append(axis_label(minutes(d["median"]), left + w + 8, y + bar_h * 0.55, "start"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(parts)}</svg>'


def era_comparison_svg() -> str:
    data = load("duration_by_era_shape.json")
    width, height = 900, 320
    left, top = 70, 62
    card_w, card_h = 360, 190
    parts = [chart_style(), f'<rect width="{width}" height="{height}" class="bg"/>', '<text x="70" y="30" class="title">Before and after the web</text>']
    for i, d in enumerate(data):
        x = left + i * (card_w + 70)
        parts.append(f'<rect x="{x}" y="{top}" width="{card_w}" height="{card_h}" rx="8" fill="#fffdf8" stroke="#d8d0c2"/>')
        parts.append(axis_label(d["label"], x + 18, top + 30, "start"))
        parts.append(f'<text x="{x + 18}" y="{top + 76}" fill="#17201d" font="700 34px system-ui, sans-serif">{d["reports"]:,}</text>')
        parts.append(axis_label("reports", x + 18, top + 98, "start"))
        parts.append(axis_label(f'Median duration: {d["median"] / 60:.0f}m', x + 18, top + 132, "start"))
        parts.append(axis_label(f'Top shape: {d["top_shape"]} ({d["top_shape_share"]:.1%})', x + 18, top + 158, "start"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(parts)}</svg>'


def main() -> None:
    write("annual_reports.svg", annual_svg())
    write("shape_counts.svg", shapes_svg())
    write("month_hour_heatmap.svg", heatmap_svg())
    write("hotspot_persistence.svg", hotspots_svg())
    write("city_hotspots.svg", city_hotspots_svg())
    write("duration_by_shape.svg", duration_by_shape_svg())
    write("era_comparison.svg", era_comparison_svg())
    print(f"Wrote notebook figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
