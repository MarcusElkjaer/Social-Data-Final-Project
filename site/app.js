const fmt = d3.format(",");
const pct = d3.format(".1%");

const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const files = {
  summary: "data/summary.json",
  annual: "data/annual_reports.json",
  heatmap: "data/month_hour.json",
  shapes: "data/shape_counts.json",
  shapeDecades: "data/shape_by_decade.json",
  countries: "data/country_counts.json",
  states: "data/state_counts.json",
  cities: "data/city_counts.json",
  durationShapes: "data/duration_by_shape.json",
  durationEras: "data/duration_by_era_shape.json",
  area51: "data/area51_summary.json",
  hotspots: "data/hotspots.json",
  hexDecades: "data/hex_decade_bins.json",
  land: "data/land-110m.json"
};

Promise.all(Object.values(files).map((path) => d3.json(path))).then((loaded) => {
  const data = Object.fromEntries(Object.keys(files).map((key, index) => [key, loaded[index]]));
  renderMetrics(data.summary);
  renderHeroMap(data.land, data.hotspots);
  renderShapeBars(data.shapes);
  renderShapeGroupStack(data.shapes);
  renderAnnualLine(data.annual);
  renderHeatmap(data.heatmap);
  renderStateBars(data.states);
  renderCityBars(data.cities);
  renderArea51(data.area51);
  renderDurationBars(data.durationShapes);
  renderEraCards(data.durationEras);
  renderWords(data.summary.top_words);
  renderCountryBars(data.countries);
  renderHotspotMap(data.land, data.hexDecades, data.hotspots);
});

function renderMetrics(summary) {
  const items = [
    { value: fmt(summary.clean_rows), label: "clean report rows" },
    { value: pct(summary.us_report_share), label: "of reports are coded as United States" },
    { value: `${summary.date_range.min_year}-${summary.date_range.max_year}`, label: "actual raw date range" },
    { value: summary.top_shape.shape, label: `${fmt(summary.top_shape.reports)} reports, most common shape` }
  ];

  d3.select("#summary-metrics")
    .selectAll(".metric")
    .data(items)
    .join("div")
    .attr("class", "metric")
    .html((d) => `<strong>${d.value}</strong><span>${d.label}</span>`);
}

function sizeSvg(selector) {
  const svg = d3.select(selector);
  const node = svg.node();
  const box = node.getBoundingClientRect();
  const width = Math.max(320, box.width || node.clientWidth || 800);
  const height = Math.max(300, box.height || parseInt(svg.style("min-height"), 10) || 360);
  svg.attr("viewBox", [0, 0, width, height]);
  return { svg, width, height };
}

function renderHeroMap(land, hotspots) {
  const { svg, width, height } = sizeSvg("#hero-map");
  const projection = d3.geoNaturalEarth1().fitSize([width, height], topojson.feature(land, land.objects.land));
  const path = d3.geoPath(projection);
  const max = d3.max(hotspots, (d) => d.total_reports);
  const radius = d3.scaleSqrt().domain([1, max]).range([1.5, 18]);

  svg.append("path")
    .datum({ type: "Sphere" })
    .attr("fill", "#202b38")
    .attr("d", path);

  svg.append("path")
    .datum(topojson.feature(land, land.objects.land))
    .attr("fill", "#314253")
    .attr("d", path);

  svg.append("g")
    .attr("opacity", 0.75)
    .selectAll("circle")
    .data(hotspots.slice(0, 520))
    .join("circle")
    .attr("cx", (d) => projection([d.lon, d.lat])?.[0])
    .attr("cy", (d) => projection([d.lon, d.lat])?.[1])
    .attr("r", (d) => radius(d.total_reports))
    .attr("fill", "#f2b24b")
    .attr("stroke", "#fff4d8")
    .attr("stroke-width", 0.5)
    .attr("fill-opacity", 0.42);
}

function shortDuration(seconds) {
  if (seconds >= 3600) {
    const hours = seconds / 3600;
    return `${d3.format(".1f")(hours)}h`;
  }
  if (seconds >= 60) {
    return `${d3.format(".0f")(seconds / 60)}m`;
  }
  return `${d3.format(".0f")(seconds)}s`;
}

function renderShapeBars(data) {
  const top = data.slice(0, 10).reverse();
  const { svg, width, height } = sizeSvg("#shape-bars");
  const margin = { top: 8, right: 18, bottom: 28, left: 86 };
  const x = d3.scaleLinear().domain([0, d3.max(top, (d) => d.reports)]).nice().range([margin.left, width - margin.right]);
  const y = d3.scaleBand().domain(top.map((d) => d.shape)).range([height - margin.bottom, margin.top]).padding(0.22);

  svg.append("g")
    .attr("fill", "#117c78")
    .selectAll("rect")
    .data(top)
    .join("rect")
    .attr("x", margin.left)
    .attr("y", (d) => y(d.shape))
    .attr("width", (d) => x(d.reports) - margin.left)
    .attr("height", y.bandwidth())
    .attr("rx", 3);

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(d3.format("~s")));

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(${margin.left},0)`)
    .call(d3.axisLeft(y).tickSize(0))
    .call((g) => g.select(".domain").remove());
}

function renderShapeGroupStack(shapes) {
  const groups = [
    { label: "lights / flashes", shapes: ["light", "fireball", "flash"], fill: "#d65d47" },
    { label: "round forms", shapes: ["circle", "sphere", "disk", "oval", "egg"], fill: "#117c78" },
    { label: "uncertain labels", shapes: ["unknown", "other", "changing", "formation", "teardrop"], fill: "#8d6b2f" },
    { label: "structured forms", shapes: ["triangle", "rectangle", "diamond", "chevron", "cylinder", "cigar", "cross", "cone"], fill: "#3f6f9f" }
  ];
  const counts = new Map(shapes.map((d) => [d.shape, d.reports]));
  const total = d3.sum(shapes, (d) => d.reports);
  const rows = groups
    .map((group) => ({
      ...group,
      reports: d3.sum(group.shapes, (shape) => counts.get(shape) || 0)
    }))
    .sort((a, b) => b.reports - a.reports);

  const stack = d3.select("#shape-group-stack");
  stack.selectAll("*").remove();

  stack.append("div")
    .attr("class", "shape-stack__bar")
    .selectAll("div")
    .data(rows)
    .join("div")
    .attr("class", "shape-stack__segment")
    .style("width", (d) => `${(d.reports / total) * 100}%`)
    .style("background", (d) => d.fill)
    .attr("title", (d) => `${d.label}: ${fmt(d.reports)} reports (${pct(d.reports / total)})`);

  stack.append("div")
    .attr("class", "shape-stack__legend")
    .selectAll("div")
    .data(rows)
    .join("div")
    .attr("class", "shape-stack__item")
    .html((d) => `
      <span class="shape-stack__swatch" style="background:${d.fill}"></span>
      <span class="shape-stack__label">${d.label}</span>
      <strong>${pct(d.reports / total)}</strong>
      <small>${fmt(d.reports)}</small>
    `);
}

function renderLabeledBars(selector, data, options) {
  const { svg, width, height } = sizeSvg(selector);
  svg.selectAll("*").remove();
  const margin = options.margin || { top: 8, right: 78, bottom: 30, left: 92 };
  const maxValue = d3.max(data, options.value) || 1;
  const x = d3.scaleLinear().domain([0, maxValue]).nice().range([margin.left, width - margin.right]);
  const y = d3.scaleBand().domain(data.map(options.label)).range([height - margin.bottom, margin.top]).padding(0.22);

  svg.append("g")
    .attr("fill", options.fill || "#117c78")
    .selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", margin.left)
    .attr("y", (d) => y(options.label(d)))
    .attr("width", (d) => Math.max(0, x(options.value(d)) - margin.left))
    .attr("height", y.bandwidth())
    .attr("rx", 3);

  svg.append("g")
    .attr("class", "bar-value")
    .selectAll("text")
    .data(data)
    .join("text")
    .attr("x", (d) => x(options.value(d)) + 7)
    .attr("y", (d) => y(options.label(d)) + y.bandwidth() / 2 + 4)
    .text((d) => options.valueLabel(d));

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(options.tickFormat || d3.format("~s")));

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(${margin.left},0)`)
    .call(d3.axisLeft(y).tickSize(0))
    .call((g) => g.select(".domain").remove());
}

function renderAnnualLine(data) {
  const { svg, width, height } = sizeSvg("#annual-line");
  const margin = { top: 18, right: 24, bottom: 38, left: 52 };
  const x = d3.scaleLinear().domain(d3.extent(data, (d) => d.year)).range([margin.left, width - margin.right]);
  const y = d3.scaleLinear().domain([0, d3.max(data, (d) => d.reports)]).nice().range([height - margin.bottom, margin.top]);
  const line = d3.line()
    .x((d) => x(d.year))
    .y((d) => y(d.reports))
    .curve(d3.curveMonotoneX);

  svg.append("rect")
    .attr("x", x(1995))
    .attr("y", margin.top)
    .attr("width", x(2005) - x(1995))
    .attr("height", height - margin.top - margin.bottom)
    .attr("fill", "#f2d49c")
    .attr("opacity", 0.45);

  svg.append("path")
    .datum(data)
    .attr("fill", "none")
    .attr("stroke", "#d65d47")
    .attr("stroke-width", 3)
    .attr("d", line);

  svg.append("text")
    .attr("x", x(1995) + 6)
    .attr("y", margin.top + 18)
    .attr("fill", "#7a5d2a")
    .attr("font-size", 12)
    .attr("font-weight", 800)
    .text("online reporting era");

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(d3.axisBottom(x).tickFormat(d3.format("d")).ticks(7));

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(${margin.left},0)`)
    .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format("~s")));
}

function renderHeatmap(data) {
  const { svg, width, height } = sizeSvg("#heatmap");
  const margin = { top: 18, right: 18, bottom: 34, left: 42 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const cellW = innerW / 24;
  const cellH = innerH / 12;
  const color = d3.scaleSequentialSqrt(d3.interpolateYlOrRd).domain([0, d3.max(data, (d) => d.reports)]);

  svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
    .selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", (d) => d.hour * cellW)
    .attr("y", (d) => (d.month - 1) * cellH)
    .attr("width", Math.max(1, cellW - 1))
    .attr("height", Math.max(1, cellH - 1))
    .attr("fill", (d) => color(d.reports));

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(${margin.left},${height - margin.bottom})`)
    .call(d3.axisBottom(d3.scaleLinear().domain([0, 23]).range([0, innerW])).ticks(8).tickFormat((d) => `${d}:00`));

  svg.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(${margin.left},${margin.top})`)
    .call(d3.axisLeft(d3.scaleBand().domain(monthNames).range([0, innerH])).tickSize(0))
    .call((g) => g.select(".domain").remove());
}

function renderStateBars(states) {
  let mode = "reports";
  const buttons = d3.selectAll("[data-state-mode]");
  buttons.on("click", function () {
    mode = this.dataset.stateMode;
    buttons.classed("active", function () { return this.dataset.stateMode === mode; });
    draw();
  });

  function draw() {
    const top = [...states].sort((a, b) => d3.descending(a[mode], b[mode])).slice(0, 12).reverse();
    const { svg, width, height } = sizeSvg("#state-bars");
    svg.selectAll("*").remove();
    const margin = { top: 8, right: 58, bottom: 30, left: 52 };
    const x = d3.scaleLinear().domain([0, d3.max(top, (d) => d[mode])]).nice().range([margin.left, width - margin.right]);
    const y = d3.scaleBand().domain(top.map((d) => d.state)).range([height - margin.bottom, margin.top]).padding(0.2);

    svg.append("g")
      .attr("fill", mode === "reports" ? "#3f6f9f" : "#d65d47")
      .selectAll("rect")
      .data(top)
      .join("rect")
      .attr("x", margin.left)
      .attr("y", (d) => y(d.state))
      .attr("width", (d) => x(d[mode]) - margin.left)
      .attr("height", y.bandwidth())
      .attr("rx", 3);

    svg.append("g")
      .attr("class", "axis")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).ticks(4).tickFormat(mode === "reports" ? d3.format("~s") : d3.format(".0f")));

    svg.append("g")
      .attr("class", "axis")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).tickSize(0))
      .call((g) => g.select(".domain").remove());
  }
  draw();
}

function renderCityBars(cities) {
  const top = cities.slice(0, 12).reverse();
  renderLabeledBars("#city-bars", top, {
    label: (d) => `${d.city}, ${d.state}`,
    value: (d) => d.reports,
    valueLabel: (d) => fmt(d.reports),
    fill: "#d65d47",
    margin: { top: 8, right: 58, bottom: 30, left: 128 },
    tickFormat: d3.format("~s")
  });
}

function renderArea51(area51) {
  const items = [
    { value: fmt(area51.nearby_reports), label: "reports near the Area 51 bounding region" },
    { value: fmt(area51.las_vegas_reports), label: "reports from Las Vegas alone" },
    { value: fmt(area51.nevada_reports), label: "reports from all of Nevada" }
  ];

  d3.select("#area51-callout")
    .selectAll(".mini-metric")
    .data(items)
    .join("div")
    .attr("class", "mini-metric")
    .html((d) => `<strong>${d.value}</strong><span>${d.label}</span>`);
}

function renderDurationBars(durationShapes) {
  const rows = durationShapes.slice(0, 16).reverse();
  renderLabeledBars("#duration-bars", rows, {
    label: (d) => d.shape,
    value: (d) => d.median,
    valueLabel: (d) => shortDuration(d.median),
    fill: "#8d6b2f",
    margin: { top: 8, right: 58, bottom: 30, left: 92 },
    tickFormat: shortDuration
  });
}

function renderEraCards(eras) {
  d3.select("#era-cards")
    .selectAll(".era-card")
    .data(eras)
    .join("div")
    .attr("class", "era-card")
    .html((d) => `
      <span>${d.label}</span>
      <strong>${fmt(d.reports)}</strong>
      <small>reports</small>
      <dl>
        <dt>Median duration</dt><dd>${shortDuration(d.median)}</dd>
        <dt>Top shape</dt><dd>${d.top_shape} (${pct(d.top_shape_share)})</dd>
        <dt>Archive share</dt><dd>${pct(d.report_share)}</dd>
      </dl>
    `);
}

function renderCountryBars(countries) {
  const rows = countries.slice(0, 6).reverse();
  renderLabeledBars("#country-bars", rows, {
    label: (d) => d.country,
    value: (d) => d.reports,
    valueLabel: (d) => fmt(d.reports),
    fill: "#3f6f9f",
    margin: { top: 8, right: 76, bottom: 30, left: 132 },
    tickFormat: d3.format("~s")
  });
}

function renderWords(words) {
  const max = d3.max(words, (d) => d.count);
  const size = d3.scaleSqrt().domain([0, max]).range([16, 48]);
  d3.select("#word-cloud")
    .selectAll("span")
    .data(words.slice(0, 24))
    .join("span")
    .style("font-size", (d) => `${size(d.count)}px`)
    .style("color", (_, i) => d3.schemeTableau10[i % 10])
    .text((d) => d.word);
}

function renderHotspotMap(land, hexDecades, hotspots) {
  const svg = d3.select("#hotspot-map");
  const tooltip = d3.select("#tooltip");
  const slider = d3.select("#decade-slider");
  const label = d3.select("#decade-label");
  let mode = "reports";

  const byDecade = d3.group(hexDecades, (d) => +d.decade);
  const persistent = hotspots.slice(0, 600);
  const buttons = d3.selectAll("[data-map-mode]");

  buttons.on("click", function () {
    mode = this.dataset.mapMode;
    buttons.classed("active", function () { return this.dataset.mapMode === mode; });
    draw();
  });
  slider.on("input", draw);

  function draw() {
    const box = svg.node().getBoundingClientRect();
    const width = Math.max(360, box.width || 1000);
    const height = Math.max(460, box.height || 620);
    svg.attr("viewBox", [0, 0, width, height]);
    svg.selectAll("*").remove();

    const landFeature = topojson.feature(land, land.objects.land);
    const projection = d3.geoNaturalEarth1().fitSize([width, height], landFeature);
    const path = d3.geoPath(projection);
    const decade = +slider.property("value");
    label.text(mode === "reports" ? decade : "all years");

    svg.append("path")
      .datum({ type: "Sphere" })
      .attr("fill", "#e9f1ef")
      .attr("d", path);

    svg.append("path")
      .datum(landFeature)
      .attr("fill", "#d7dfd9")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 0.5)
      .attr("d", path);

    const rows = mode === "reports" ? (byDecade.get(decade) || []) : persistent;
    const value = mode === "reports"
      ? (d) => d.reports
      : (d) => d.persistence_ratio;
    const maxValue = d3.max(rows, value) || 1;
    const color = mode === "reports"
      ? d3.scaleSequentialSqrt(d3.interpolateOrRd).domain([0, maxValue])
      : d3.scaleSequential(d3.interpolatePuBuGn).domain([0, maxValue]);

    const radius = d3.scaleSqrt()
      .domain([0, mode === "reports" ? maxValue : d3.max(rows, (d) => d.total_reports)])
      .range([2, mode === "reports" ? 18 : 22]);

    svg.append("g")
      .selectAll("path")
      .data(rows.filter((d) => projection([d.lon, d.lat])))
      .join("path")
      .attr("d", (d) => hexPath(projection([d.lon, d.lat]), radius(mode === "reports" ? d.reports : d.total_reports)))
      .attr("fill", (d) => color(value(d)))
      .attr("stroke", "#24322d")
      .attr("stroke-width", 0.35)
      .attr("fill-opacity", 0.76)
      .on("mousemove", (event, d) => {
        tooltip
          .attr("hidden", null)
          .style("left", `${event.offsetX + 14}px`)
          .style("top", `${event.offsetY + 14}px`)
          .html(tooltipHtml(d, mode));
      })
      .on("mouseleave", () => tooltip.attr("hidden", true));
  }

  draw();
  window.addEventListener("resize", debounce(draw, 150));
}

function hexPath(point, radius) {
  const [cx, cy] = point;
  const coords = d3.range(6).map((i) => {
    const angle = Math.PI / 6 + i * Math.PI / 3;
    return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)];
  });
  return `M${coords.map((d) => d.join(",")).join("L")}Z`;
}

function tooltipHtml(d, mode) {
  if (mode === "reports") {
    return `
      <strong>${fmt(d.reports)} reports in the ${d.decade}s</strong>
      ${fmt(d.total_reports)} total reports<br>
      ${d.active_years} active years, ${d.active_decades} active decades<br>
      Top shape: ${d.top_shape}
    `;
  }
  return `
    <strong>${fmt(d.total_reports)} total reports</strong>
    ${d.active_years} active years, ${d.active_decades} active decades<br>
    Persistence ratio: ${pct(d.persistence_ratio)}<br>
    Top shape: ${d.top_shape}
  `;
}

function debounce(fn, wait) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), wait);
  };
}
