import * as d3 from "d3";

const app = document.getElementById("app");

// ---- Data loading ----
const load = (name) => fetch(`./data/${name}.json`).then(r => r.json());

async function main() {
  const [
    scatter, mediation, quartiles, networkStats, communityNmi,
    corrData, topPeople, writerComm, somData, countryData,
    disjunctureScores, communityGraph, egoNetworks, smallMultiples,
    butterflyData,
  ] = await Promise.all([
    load("diversity-scatter"), load("mediation"), load("budget-quartiles"),
    load("network-stats"), load("community-nmi"), load("centrality-correlation"),
    load("top-people"), load("writer-communities"), load("som-grid"),
    load("country-map"), load("disjuncture-scores"), load("community-graph"),
    load("ego-networks"), load("small-multiples"),
    fetch("./data/butterfly.json").then(r => r.json()),
  ]);

  app.innerHTML = `
    ${heroSection()}
    <div class="divider"></div>
    ${section1(scatter)}
    <div class="divider"></div>
    ${section2()}
    <div class="divider"></div>
    ${section3(networkStats)}
    <div class="divider"></div>
    ${section4(communityNmi)}
    <div class="divider"></div>
    ${section5(writerComm)}
    <div class="divider"></div>
    ${section6()}
    <div class="divider"></div>
    ${methodologySection()}
    <div class="footer">INFO 230 · Moe Alhassan · Spring 2026</div>
  `;

  // ---- Render D3 visualizations after DOM is ready ----
  renderScatter(scatter);
  renderMediation(mediation);
  renderQuartiles(quartiles);
  renderNmiChart(communityNmi);
  renderNetworkExplorer(communityGraph, topPeople, egoNetworks, smallMultiples);
  renderSpotlight(topPeople);
  renderButterfly(butterflyData);
  renderSom(somData);
}

// ============================================================
// SECTIONS (return HTML strings)
// ============================================================

const REPO = "https://github.com/MoeAlhassan/four-scapes-of-cinema/blob/main";

function srcLink(path, label) {
  return `<a class="src-link" href="${REPO}/${path}" target="_blank" rel="noopener">↗ ${label || "View source"}</a>`;
}

function heroSection() {
  return `
    <div class="hero">
      <div class="kicker">Network Analysis · Cultural Analytics · INFO 230</div>
      <h1>The Four Scapes of Cinema</h1>
      <p class="subtitle">I took 1,778 films and 16,000 people from IMDb and built 5 different networks from the same data. Each one tells a different story.</p>
      <p class="byline">Moe Alhassan · Spring 2026</p>
      <div class="hero-links">
        <a href="https://github.com/MoeAlhassan/four-scapes-of-cinema" target="_blank" rel="noopener">GitHub Repo</a>
        <a href="${REPO}/notebook.ipynb" target="_blank" rel="noopener">Analysis Notebook</a>
      </div>
    </div>`;
}

function section1() {
  return `
    <div class="section-heading"><h2>Do diverse casts make worse films?</h2></div>
    <div class="prose-col prose">
      <p>I gave every director a geographic diversity score based on where their cast and crew come from. 0 = everyone's from the same country. 1 = spread across the globe.</p>
      <p>Does that score correlate with ratings?</p>
      <p>Yeah. Negatively. More diverse casts, lower ratings.</p>
      <div class="callout red">
        <div class="big">β = −0.59</div>
        <div class="desc">Every unit increase in geographic diversity = ~0.6 point drop in avg rating.<br><em>p &lt; 0.001, N = 797 directors</em></div>
      </div>
    </div>
    <div class="viz-col viz" id="scatter-viz"></div>
    <div class="prose-col prose"><p>But that's not the whole story.</p>
    ${srcLink("src/07_outcome_analysis.py", "Regression source")}
    </div>`;
}

function section2() {
  return `
    <div class="section-heading"><h2>It's the money</h2></div>
    <div class="prose-col prose">
      <p>I checked if budget is actually what's driving that correlation. Diverse casts tend to show up in expensive international co-productions. Expensive co-productions tend to get lower critic scores.</p>
      <p>Control for budget and 61% of the diversity effect goes away. What's left isn't statistically significant (p = 0.175).</p>
    </div>
    <div class="viz-col viz" id="mediation-viz"></div>
    <div class="prose-col prose"><p>Split directors into budget quartiles and it's pretty clear:</p></div>
    <div class="viz-col viz" id="quartile-viz"></div>
    <div class="prose-col prose"><p>So the real question is: who works with whom, how does money flow through those relationships, and do different types of connections create different structures? To answer that I needed to look at the whole network.</p>
    ${srcLink("src/07_outcome_analysis.py", "Mediation analysis source")}
    </div>`;
}

function section3(stats) {
  const cards = stats.map(s => `
    <div class="stat-card">
      <div class="val">${s.nodes.toLocaleString()}</div>
      <div class="lbl">${s.name.replace(/_/g, " ")}</div>
      <div style="color:var(--text-dim);font-size:11px;margin-top:4px">${s.edges.toLocaleString()} edges · ${s.components} comp.</div>
    </div>`).join("");

  return `
    <div class="section-heading"><h2>Five networks from one dataset</h2></div>
    <div class="prose-col prose">
      <p>Arjun Appadurai argues that globalization moves through separate channels: people, media, money, ideas. And these channels don't line up. The gaps between them are where interesting stuff happens.</p>
      <p>I used that framework to build 5 networks from the same 1,778 films. Same people, different lenses:</p>
      <div class="stats-row">${cards}</div>
      <ul>
        <li><span class="tag mediascape">Mediascape</span> Who works with whom through shared films.</li>
        <li><span class="tag ethno-cross">Cross-Origin</span> Only connections between people from <strong>different countries</strong>.</li>
        <li><span class="tag ethno-same">Same-Origin</span> Only connections between people from the <strong>same country</strong>.</li>
        <li><span class="tag financescape">Financescape</span> Collaboration weighted by budget and revenue.</li>
        <li><span class="tag ideoscape">Ideoscape</span> Collaboration weighted by genre similarity.</li>
      </ul>
      <p>One thing that jumped out: the same-origin network breaks into hundreds of disconnected pieces. National cinema islands. Cross-origin collaboration is what stitches them into one global industry.</p>
      <h3 style="margin-top:40px;color:var(--text-bright)">Explore the networks</h3>
      <p>Pick a scape below. Click a community to see who's in it. Click a person for their ego network.</p>
    </div>
    <div class="viz" id="network-explorer" style="max-width:1100px;margin:40px auto;padding:0 24px"></div>
    <div class="prose-col">${srcLink("src/04_build_networks.py", "Network construction")} · ${srcLink("src/05_network_metrics.py", "Metrics & communities")}</div>`;
}

function section4(nmi) {
  return `
    <div class="section-heading"><h2>Where the networks disagree</h2></div>
    <div class="prose-col prose">
      <p>If all 5 networks grouped people the same way, this would be boring. They don't.</p>
      <p>I compared community structures across each pair using NMI (Normalized Mutual Information). 1 = identical groupings. 0 = totally independent. Below 0.3 = a real gap.</p>
    </div>
    <div class="viz-col viz" id="nmi-viz"></div>
    <div class="prose-col">
      <div class="callout teal">
        <div class="big">0.24</div>
        <div class="desc">NMI between cross-origin and same-origin networks. The groups that form through international work look nothing like the groups that form domestically.</div>
      </div>
    </div>
    <div class="prose-col prose">
      <h3 style="margin-top:40px;color:var(--text-bright)">Look up anyone in the top 500</h3>
      <p>See how a specific person ranks across the different networks:</p>
    </div>
    <div class="viz" id="spotlight-viz" style="max-width:1200px;margin:40px auto;padding:0 24px"></div>
    <div class="prose-col">${srcLink("src/06_disjuncture.py", "Disjuncture analysis source")}</div>`;
}

function section5(writerComm) {
  return `
    <div class="section-heading"><h2>Tight circles make better films</h2></div>
    <div class="prose-col prose">
      <p>Writer clustering predicts film quality. That's the strongest result in this analysis. Writers who work in tight circles (where their collaborators also work with each other) make higher-rated films, even controlling for budget (β = 7.03, p &lt; 0.001, R² = 0.187).</p>
      <p>Anderson and Spielberg share 12 collaborators. They use them completely differently:</p>
    </div>
    <div class="viz-col viz" id="butterfly-viz"></div>
    <div class="prose-col prose">
      <p>Anderson (clustering: 0.017) keeps bringing the same people back. Goldblum shows up 3 times. Stockhausen, 4. His collaborators work with each other across his films.</p>
      <p>Spielberg (clustering: 0.003) assembles mostly new crews every time. 24 films, mostly one-offs. Debra Zane cast 4 of them but that's the exception.</p>
      <p>Both make great stuff (Anderson avg: 7.6, Spielberg: 7.5). But across the full dataset, tight circles track with higher ratings.</p>
      <h3 style="margin-top:40px;color:var(--text-bright)">Archetype map</h3>
      <p>18 measurements per person (connectivity across all 5 networks, clustering, diversity, ratings, ROI), projected onto a 2D grid. Nearby cells = similar profiles.</p>
    </div>
    <div class="viz-col viz" id="som-viz"></div>
    <div class="prose-col">${srcLink("src/08_som.py", "SOM source")} · ${srcLink("src/07_outcome_analysis.py", "Writer regression")}</div>`;
}

function section6() {
  return `
    <div class="section-heading"><h2>What I found</h2></div>
    <div class="prose-col prose">
      <p>The diversity/ratings correlation is a budget story. Diverse casts show up in expensive productions. Expensive productions get lower ratings. Control for budget and the effect goes away.</p>
      <p>International and domestic collaboration produce different community structures. NMI of 0.24. The groups that form through cross-border work don't match the groups that form domestically.</p>
      <p>Writer clustering predicts quality. Strongest signal in the data (β = 7.03, p &lt; 0.001). Repeated collaboration seems to build something that ends up in the final product.</p>
      <p>None of this predicts box office. No network metric I tested has a significant relationship with ROI.</p>
      <div class="stats-row">
        <div class="stat-card"><div class="val">1,778</div><div class="lbl">Films</div></div>
        <div class="stat-card"><div class="val">16,191</div><div class="lbl">People</div></div>
        <div class="stat-card"><div class="val">5</div><div class="lbl">Networks</div></div>
        <div class="stat-card"><div class="val">76%</div><div class="lbl">Geographic Coverage</div></div>
        <div class="stat-card"><div class="val">0.24</div><div class="lbl">Key NMI</div></div>
      </div>
      <h3 style="color:var(--text-bright)">Limitations</h3>
      <ul>
        <li>IMDb vote-count bias. This corpus skews toward English-language Hollywood. It reflects IMDb's user base, not global filmmaking.</li>
        <li>No temporal slicing. 1927 and 2025 are in the same network. Collaboration patterns change over decades, and I'm ignoring that.</li>
        <li>76% geographic coverage. ~1 in 4 people don't have country data in Wikidata. Weakest for supporting crew.</li>
        <li>Broad genres. IMDb has 28 genre tags. "Drama" covers a lot of ground.</li>
      </ul>
      <h3 style="color:var(--text-bright);margin-top:24px">Where this could go next</h3>
      <ul>
        <li>Slice by decade. Watch the structure change over time.</li>
        <li>Add prestige TV. Probably has very different collaboration patterns.</li>
        <li>Add gender and see how it interacts with geographic diversity.</li>
        <li>Lower the vote threshold and build separate networks for Bollywood, Korean cinema, Nollywood.</li>
      </ul>
    </div>`;
}

function methodologySection() {
  return `
    <div class="section-heading"><h2>Methodology</h2></div>
    <div class="prose-col prose">
      <details><summary>Data sources</summary>
        <p>Cast, crew, and ratings from <strong>IMDb's public datasets</strong> (March 2026). I filtered to the 1,778 movies with 153,000+ user ratings. Budget and box office from <strong>TMDB</strong> (98% coverage). Country of origin from <strong>Wikidata</strong>, queried via SPARQL for citizenship or birthplace. That worked for about 76% of people; coverage is better for directors and leads than for crew.</p>
      </details>
      <details><summary>Network construction</summary>
        <p>Two people are connected if they worked on the same film. I downweight large-cast films proportionally: a shared credit on a 5-person indie crew counts more than one on a 200-person blockbuster.</p>
        <p>The <strong>cross-origin network</strong> keeps only edges between people from different countries (109k edges). The <strong>same-origin network</strong> keeps only edges within the same country (120k edges). The <strong>financescape</strong> is restricted to films with both budget and revenue data (1,735 films).</p>
      </details>
      <details><summary>Community detection</summary>
        <p>I used the <strong>Leiden algorithm</strong> to find natural groupings. It works like detecting friend groups: you don't define the groups up front, the algorithm finds clusters of people who work together more densely than you'd expect by chance.</p>
        <p><strong>Geographic diversity</strong> is measured per director: how spread out are their collaborators across countries? 0 = all one country, closer to 1 = evenly distributed.</p>
      </details>
      <details><summary>Diversity and budget</summary>
        <p>Geographic diversity correlates with lower ratings, but I tested whether budget is doing the actual work. Diverse casts show up in big productions, and big productions score lower. Controlling for budget kills 61% of the effect and makes the remainder statistically insignificant.</p>
        <p><em>OLS with robust standard errors, N = 772 directors.</em></p>
      </details>
      <details><summary>Writer clustering</summary>
        <p>I measured how tight each writer's collaboration circle is (do your collaborators also work with each other?) and tested whether that predicts ratings, controlling for budget. It does. Strongest result in the whole analysis.</p>
        <p><em>β = 7.03, p &lt; 0.001, R² = 0.187, N = 2,244.</em></p>
      </details>
      <details><summary>Self-Organizing Map</summary>
        <p>18 measurements per person (connectivity in each network, clustering, diversity, ratings, ROI), projected onto a 15x15 2D grid. The grid puts people with similar profiles in nearby cells. The labeled regions are archetypes that fell out of the projection naturally.</p>
      </details>
    </div>`;
}

// ============================================================
// D3 VISUALIZATIONS
// ============================================================

function renderScatter(data) {
  const container = d3.select("#scatter-viz");
  const width = 860, height = 520, m = {top: 30, right: 40, bottom: 50, left: 60};
  const w = width - m.left - m.right, h = height - m.top - m.bottom;

  const svg = container.append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .style("width", "100%").style("max-width", width + "px").style("height", "auto");
  const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

  const x = d3.scaleLinear().domain([0, 1]).range([0, w]);
  const y = d3.scaleLinear().domain([4, 9.5]).range([h, 0]);

  // Axes
  g.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x).ticks(5))
    .selectAll("text").attr("fill", "#888");
  g.append("g").call(d3.axisLeft(y).ticks(6)).selectAll("text").attr("fill", "#888");
  g.selectAll(".domain, .tick line").attr("stroke", "#333");

  // Axis labels
  svg.append("text").attr("x", width/2).attr("y", height - 8).attr("text-anchor", "middle").attr("fill", "#888").attr("font-size", "13px").text("Geographic Diversity (Blau Index) →");
  svg.append("text").attr("x", 16).attr("y", m.top - 10).attr("fill", "#888").attr("font-size", "13px").text("↑ Average Rating");

  // Tooltip (fixed position, follows mouse)
  const tooltip = d3.select("body").append("div")
    .style("position", "fixed").style("background", "rgba(20,20,32,0.95)")
    .style("padding", "10px 14px").style("border-radius", "8px")
    .style("font-size", "13px").style("color", "#ddd").style("pointer-events", "none")
    .style("opacity", 0).style("z-index", 1000)
    .style("border", "1px solid #333").style("box-shadow", "0 4px 12px rgba(0,0,0,0.5)");

  // Dots — draw smaller ones first (behind), larger on top
  const sorted = [...data].sort((a, b) => a.n_films - b.n_films);

  g.selectAll("circle").data(sorted).join("circle")
    .attr("cx", d => x(d.blau)).attr("cy", d => y(d.rating))
    .attr("r", d => Math.max(3, Math.sqrt(d.n_films) * 2))
    .attr("fill", "#6c5ce7").attr("fill-opacity", 0.4)
    .attr("stroke", "#6c5ce7").attr("stroke-opacity", 0.6).attr("stroke-width", 0.8)
    .style("cursor", "crosshair")
    .on("mouseover", function(event, d) {
      d3.select(this).attr("fill-opacity", 0.9).attr("stroke-opacity", 1).attr("stroke-width", 2);
      tooltip.style("opacity", 1)
        .html(`<strong>${d.name}</strong><br>Diversity: ${d.blau.toFixed(2)}<br>Rating: ${d.rating}<br>Films: ${d.n_films}`);
    })
    .on("mousemove", function(event) {
      tooltip.style("left", (event.clientX + 16) + "px").style("top", (event.clientY - 16) + "px");
    })
    .on("mouseout", function() {
      d3.select(this).attr("fill-opacity", 0.4).attr("stroke-opacity", 0.6).attr("stroke-width", 0.8);
      tooltip.style("opacity", 0);
    });

  // Regression line
  const xVals = data.map(d => d.blau), yVals = data.map(d => d.rating);
  const xMean = d3.mean(xVals), yMean = d3.mean(yVals);
  const slope = d3.sum(xVals.map((xi, i) => (xi - xMean) * (yVals[i] - yMean))) / d3.sum(xVals.map(xi => (xi - xMean) ** 2));
  const intercept = yMean - slope * xMean;
  g.append("line")
    .attr("x1", x(0)).attr("y1", y(intercept))
    .attr("x2", x(1)).attr("y2", y(slope + intercept))
    .attr("stroke", "#e63946").attr("stroke-width", 2.5).attr("stroke-dasharray", "8,5");

  // Notable director labels
  const notables = [
    "Christopher Nolan", "Martin Scorsese", "Bong Joon Ho",
    "Steven Spielberg", "Quentin Tarantino", "Denis Villeneuve",
    "Hayao Miyazaki", "Wes Anderson", "David Fincher",
    "Greta Gerwig", "Jordan Peele",
  ];
  const labeled = data.filter(d => notables.includes(d.name));

  // Draw labels with offset to avoid overlap
  const labelGroup = g.append("g").attr("class", "labels");
  labeled.forEach(d => {
    const cx = x(d.blau), cy = y(d.rating);
    // Offset label to upper-right by default
    const lx = cx + 8, ly = cy - 10;
    labelGroup.append("line")
      .attr("x1", cx).attr("y1", cy).attr("x2", lx).attr("y2", ly)
      .attr("stroke", "#555").attr("stroke-width", 0.8);
    labelGroup.append("text")
      .attr("x", lx + 3).attr("y", ly)
      .attr("fill", "#ccc").attr("font-size", "10px").attr("font-family", "Inter, sans-serif")
      .text(d.name);
  });
}

function renderMediation(data) {
  const container = d3.select("#mediation-viz");
  const width = 680, height = 340;
  const svg = container.append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .style("width", "100%").style("max-width", width + "px").style("height", "auto");

  const nodes = [
    {id: "div", label: "Geographic\nDiversity", x: 80, y: 200, color: "#00b894"},
    {id: "bud", label: "Film\nBudget", x: 340, y: 70, color: "#fdcb6e"},
    {id: "rat", label: "Film\nRating", x: 600, y: 200, color: "#6c5ce7"},
  ];

  svg.append("defs").append("marker").attr("id", "ah").attr("viewBox", "0 0 10 10")
    .attr("refX", 8).attr("refY", 5).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto")
    .append("path").attr("d", "M 0 0 L 10 5 L 0 10 z").attr("fill", "#888");

  const arrows = [
    {x1: 120, y1: 200, x2: 300, y2: 85, label: `β = ${data.x_to_mediator.coef.toFixed(2)}***`, sig: true},
    {x1: 380, y1: 85, x2: 560, y2: 200, label: `β = ${data.mediator_effect.coef.toFixed(2)}***`, sig: true},
    {x1: 120, y1: 210, x2: 560, y2: 210, label: `β = ${data.direct_effect.coef.toFixed(2)} (n.s.)`, sig: false},
  ];

  arrows.forEach(a => {
    svg.append("line").attr("x1", a.x1).attr("y1", a.y1).attr("x2", a.x2).attr("y2", a.y2)
      .attr("stroke", a.sig ? "#ddd" : "#444").attr("stroke-width", a.sig ? 3 : 2)
      .attr("stroke-dasharray", a.sig ? "none" : "8,5").attr("marker-end", "url(#ah)").attr("opacity", a.sig ? 0.9 : 0.4);
    svg.append("text").attr("x", (a.x1+a.x2)/2 + (a.sig ? -8 : 0)).attr("y", (a.y1+a.y2)/2 + (a.sig ? -14 : 22))
      .attr("text-anchor", "middle").attr("fill", a.sig ? "#ccc" : "#555").attr("font-size", "12px").text(a.label);
  });

  nodes.forEach(n => {
    const g = svg.append("g").attr("transform", `translate(${n.x},${n.y})`);
    g.append("circle").attr("r", 40).attr("fill", n.color).attr("opacity", 0.85);
    n.label.split("\n").forEach((line, i) => {
      g.append("text").attr("text-anchor", "middle").attr("dy", (i - 0.5) * 15)
        .attr("fill", "#fff").attr("font-size", "11px").attr("font-weight", "600").text(line);
    });
  });

  svg.append("text").attr("x", width/2).attr("y", height - 12).attr("text-anchor", "middle")
    .attr("fill", "#fdcb6e").attr("font-size", "15px").attr("font-weight", "600")
    .text(`${Math.round(data.pct_mediated)}% of the effect is mediated by budget`);
}

function renderQuartiles(data) {
  const container = d3.select("#quartile-viz");
  const width = 500, height = 300, m = {top: 20, right: 20, bottom: 40, left: 50};
  const w = width - m.left - m.right, h = height - m.top - m.bottom;

  const svg = container.append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .style("width", "100%").style("max-width", width + "px").style("height", "auto");
  const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

  const x = d3.scaleBand().domain(data.map(d => d.quartile)).range([0, w]).padding(0.3);
  const y = d3.scaleLinear().domain([6.4, 7.8]).range([h, 0]);

  g.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x)).selectAll("text").attr("fill", "#888");
  g.append("g").call(d3.axisLeft(y).ticks(4)).selectAll("text").attr("fill", "#888");
  g.selectAll(".domain, .tick line").attr("stroke", "#333");

  g.selectAll("rect").data(data).join("rect")
    .attr("x", d => x(d.quartile)).attr("y", d => y(d.avg_rating))
    .attr("width", x.bandwidth()).attr("height", d => h - y(d.avg_rating))
    .attr("fill", "#fdcb6e").attr("opacity", 0.8).attr("rx", 3);

  g.selectAll(".bar-label").data(data).join("text")
    .attr("x", d => x(d.quartile) + x.bandwidth()/2).attr("y", d => y(d.avg_rating) - 6)
    .attr("text-anchor", "middle").attr("fill", "#ccc").attr("font-size", "12px")
    .text(d => d.avg_rating.toFixed(2));
}

function renderNmiChart(data) {
  const container = d3.select("#nmi-viz");
  const sorted = [...data].sort((a, b) => a.nmi - b.nmi);
  const width = 760, height = 380, m = {top: 20, right: 20, bottom: 90, left: 60};
  const w = width - m.left - m.right, h = height - m.top - m.bottom;

  const svg = container.append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .style("width", "100%").style("max-width", width + "px").style("height", "auto");
  const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

  const labels = sorted.map(d => `${d.scape_1}\n↔ ${d.scape_2}`);
  const x = d3.scaleBand().domain(labels).range([0, w]).padding(0.2);
  const y = d3.scaleLinear().domain([0, 0.75]).range([h, 0]);
  const color = d3.scaleSequential(d3.interpolateViridis).domain([0, 0.7]);

  g.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x))
    .selectAll("text").attr("fill", "#888").attr("font-size", "9px")
    .style("text-anchor", "end").attr("transform", "rotate(-35)");
  g.append("g").call(d3.axisLeft(y).ticks(5)).selectAll("text").attr("fill", "#888");
  g.selectAll(".domain, .tick line").attr("stroke", "#333");

  g.selectAll("rect").data(sorted).join("rect")
    .attr("x", (d, i) => x(labels[i])).attr("y", d => y(d.nmi))
    .attr("width", x.bandwidth()).attr("height", d => h - y(d.nmi))
    .attr("fill", d => color(d.nmi)).attr("rx", 3);

  // Threshold line
  g.append("line").attr("x1", 0).attr("x2", w).attr("y1", y(0.3)).attr("y2", y(0.3))
    .attr("stroke", "#e63946").attr("stroke-width", 1.5).attr("stroke-dasharray", "6,4");
  g.append("text").attr("x", w - 4).attr("y", y(0.3) - 6)
    .attr("text-anchor", "end").attr("fill", "#e63946").attr("font-size", "11px").text("Disjuncture threshold (0.3)");
}

function renderNetworkExplorer(communityGraph, topPeople, egoData, smallMultiples) {
  const container = d3.select("#network-explorer");

  // Role colors
  const ROLE_COLORS = {
    actor: "#6c5ce7", actress: "#a29bfe", director: "#e63946",
    producer: "#fdcb6e", writer: "#00b894", composer: "#0984e3",
    cinematographer: "#e17055", editor: "#636e72",
    casting_director: "#fd79a8", production_designer: "#55efc4",
  };
  const roleColor = (role) => ROLE_COLORS[role] || "#888";

  // Country colors (top countries get distinct colors)
  const COUNTRY_COLORS = {
    "United States": "#6c5ce7", "United Kingdom": "#e63946",
    "Canada": "#fdcb6e", "France": "#00b894", "Australia": "#0984e3",
    "Germany": "#e17055", "Japan": "#fd79a8", "India": "#55efc4",
    "South Korea": "#a29bfe", "Italy": "#ffeaa7",
  };
  const countryColor = (c) => COUNTRY_COLORS[c] || "#636e72";

  let colorMode = "role"; // "role" or "country"
  const getColor = (d) => colorMode === "role" ? roleColor(d.role) : countryColor(d.country);

  const SCAPES = [
    {key: "mediascape", label: "Mediascape", color: "#6c5ce7"},
    {key: "ethnoscape_cross", label: "Cross-Origin", color: "#00b894"},
    {key: "ethnoscape_same", label: "Same-Origin", color: "#e17055"},
    {key: "financescape", label: "Financescape", color: "#fdcb6e"},
    {key: "ideoscape", label: "Ideoscape", color: "#0984e3"},
  ];
  let currentScape = "mediascape";

  // Build controls
  const controls = container.append("div").attr("class", "explorer-controls");
  const bc = container.append("div").attr("class", "breadcrumb");
  const vizArea = container.append("div");

  SCAPES.forEach(s => {
    controls.append("button").text(s.label)
      .classed("active", s.key === currentScape)
      .style("background", s.key === currentScape ? s.color : "")
      .on("click", function() {
        currentScape = s.key;
        controls.selectAll("button").classed("active", false).style("background", "");
        d3.select(this).classed("active", true).style("background", s.color);
        showOverview();
      });
  });

  function showOverview() {
    vizArea.html("");

    // Color toggle + legend row
    const topRow = vizArea.append("div").style("display", "flex").style("justify-content", "space-between")
      .style("align-items", "flex-start").style("margin-bottom", "12px").style("flex-wrap", "wrap").style("gap", "12px");

    // Color mode toggle
    const toggleDiv = topRow.append("div").style("display", "flex").style("gap", "6px").style("align-items", "center");
    toggleDiv.append("span").style("color", "#888").style("font-size", "12px").text("Color by:");
    ["role", "country"].forEach(mode => {
      toggleDiv.append("button").text(mode.charAt(0).toUpperCase() + mode.slice(1))
        .style("background", mode === colorMode ? "#444" : "#222").style("color", "#ddd")
        .style("border", "1px solid #444").style("padding", "4px 12px").style("border-radius", "4px")
        .style("cursor", "pointer").style("font-size", "12px")
        .on("click", function() {
          colorMode = mode;
          toggleDiv.selectAll("button").style("background", "#222");
          d3.select(this).style("background", "#444");
          showOverview(); // re-render
        });
    });

    // Legend
    const legendDiv = topRow.append("div").style("display", "flex").style("flex-wrap", "wrap").style("gap", "8px");
    const legendItems = colorMode === "role"
      ? Object.entries(ROLE_COLORS).filter(([k]) => !["production_designer", "editor"].includes(k))
      : Object.entries(COUNTRY_COLORS);
    legendItems.forEach(([label, color]) => {
      const item = legendDiv.append("div").style("display", "flex").style("align-items", "center").style("gap", "4px");
      item.append("div").style("width", "10px").style("height", "10px").style("border-radius", "50%")
        .style("background", color).style("flex-shrink", "0");
      item.append("span").style("font-size", "11px").style("color", "#aaa")
        .text(label.replace("_", " "));
    });

    bc.text("Hover for details. Click a person to see their ego network. Clusters = communities (people who collaborate frequently).");

    const commCol = `${currentScape}_community`;
    const degCol = `${currentScape}_degree`;

    // Filter to people who have data for this scape
    const ppl = smallMultiples.nodes.filter(d => d[commCol] != null && d[commCol] >= 0);
    if (!ppl.length) { vizArea.append("p").style("text-align", "center").style("color", "#666").text("No data for this scape"); return; }

    const idSet = new Set(ppl.map(d => d.id));
    const edgesAll = smallMultiples.edges.filter(d => idSet.has(d.source) && idSet.has(d.target));

    const graphW = 1000, graphH = 900;
    const degreeExtent = d3.extent(ppl, d => d[degCol] || 0.001);
    const rScale = d3.scaleSqrt().domain(degreeExtent).range([4, 20]);

    const svg = vizArea.append("svg")
      .attr("viewBox", `0 0 ${graphW} ${graphH}`)
      .attr("width", graphW).attr("height", graphH)
      .style("display", "block").style("margin", "0 auto");

    // Tooltip
    const tooltip = d3.select("body").append("div")
      .style("position", "fixed").style("background", "rgba(20,20,32,0.95)")
      .style("padding", "10px 14px").style("border-radius", "8px")
      .style("font-size", "13px").style("color", "#ddd").style("pointer-events", "none")
      .style("opacity", 0).style("z-index", 1000)
      .style("border", "1px solid #333").style("max-width", "260px");

    // Deep copy for simulation
    const simNodes = ppl.map(d => ({...d}));
    const simEdges = edgesAll.map(d => ({source: d.source, target: d.target, weight: d.weight}));

    // Force layout: cluster by community
    // Within-community edges are strong (pull together), cross-community edges are weak
    const simulation = d3.forceSimulation(simNodes)
      .force("charge", d3.forceManyBody().strength(-50))
      .force("center", d3.forceCenter(graphW / 2, graphH / 2))
      .force("collision", d3.forceCollide().radius(d => rScale(d[degCol] || 0.001) + 4))
      .force("link", d3.forceLink(simEdges).id(d => d.id)
        .distance(d => {
          // Same community = short, different community = long
          const s = simNodes.find(n => n.id === (d.source.id || d.source));
          const t = simNodes.find(n => n.id === (d.target.id || d.target));
          if (s && t && s[commCol] === t[commCol]) return 20;
          return 120;
        })
        .strength(d => {
          const s = simNodes.find(n => n.id === (d.source.id || d.source));
          const t = simNodes.find(n => n.id === (d.target.id || d.target));
          if (s && t && s[commCol] === t[commCol]) return 0.4;
          return 0.02;
        })
      )
      .stop();

    for (let i = 0; i < 300; i++) simulation.tick();

    // Re-center and scale to fill viewBox
    const pad = 50;
    const xExt = d3.extent(simNodes, d => d.x), yExt = d3.extent(simNodes, d => d.y);
    const dw = xExt[1] - xExt[0] || 1, dh = yExt[1] - yExt[0] || 1;
    const sc = Math.min((graphW - pad * 2) / dw, (graphH - pad * 2) / dh);
    const cxc = (xExt[0] + xExt[1]) / 2, cyc = (yExt[0] + yExt[1]) / 2;
    simNodes.forEach(d => { d.x = (d.x - cxc) * sc + graphW / 2; d.y = (d.y - cyc) * sc + graphH / 2; });

    // Edges — only show within-community edges (cross-community would be noise)
    const visibleEdges = simEdges.filter(d => {
      const sc1 = d.source[commCol], sc2 = d.target[commCol];
      return sc1 != null && sc1 === sc2;
    });

    svg.append("g").selectAll("line").data(visibleEdges).join("line")
      .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y)
      .attr("stroke", d => getColor(d.source))
      .attr("stroke-opacity", 0.15)
      .attr("stroke-width", 0.8);

    // Nodes
    const nodeG = svg.append("g").selectAll("g").data(simNodes).join("g")
      .attr("transform", d => `translate(${d.x},${d.y})`).style("cursor", "pointer");

    nodeG.append("circle")
      .attr("r", d => rScale(d[degCol] || 0.001))
      .attr("fill", d => getColor(d))
      .attr("opacity", 0.85)
      .attr("stroke", "#fff").attr("stroke-width", 0.3);

    // Labels for top 40 people
    const topN = [...simNodes].sort((a, b) => (b[degCol] || 0) - (a[degCol] || 0)).slice(0, 40);
    const topIdsSet = new Set(topN.map(d => d.id));
    nodeG.filter(d => topIdsSet.has(d.id)).append("text")
      .attr("dy", d => -rScale(d[degCol] || 4) - 4)
      .attr("text-anchor", "middle")
      .attr("fill", "#ccc").attr("font-size", "9px")
      .text(d => {
        // Show last name, or full name for short names
        const parts = (d.name || "").split(" ");
        return parts.length > 1 ? parts.slice(-1)[0] : d.name;
      });

    // Interactions
    nodeG.on("mouseover", function(event, d) {
        d3.select(this).select("circle").attr("opacity", 1).attr("stroke-width", 2.5);
        // Highlight edges connected to this node
        svg.selectAll("line")
          .attr("stroke-opacity", e =>
            (e.source.id === d.id || e.target.id === d.id) ? 0.6 : 0.05
          )
          .attr("stroke-width", e =>
            (e.source.id === d.id || e.target.id === d.id) ? 2 : 0.5
          );
        const person = topPeople.find(p => p.nconst === d.id);
        tooltip.style("opacity", 1).html(
          `<strong>${d.name}</strong><br>` +
          `<span style="color:${getColor(d)}">${(d.role || "unknown").replace(/_/g," ")}</span><br>` +
          `${d.country || person?.country || "Unknown"} · ${person?.n_films || "?"} films<br>` +
          `Rating: ${person?.avg_rating?.toFixed(1) || "?"}`
        );
      })
      .on("mousemove", (event) => {
        tooltip.style("left", (event.clientX + 14) + "px").style("top", (event.clientY - 14) + "px");
      })
      .on("mouseout", function() {
        d3.select(this).select("circle").attr("opacity", 0.85).attr("stroke-width", 0.3);
        svg.selectAll("line").attr("stroke-opacity", 0.15).attr("stroke-width", 0.8);
        tooltip.style("opacity", 0);
      })
      .on("click", (event, d) => {
        const egoEntry = egoData?.[d.id];
        if (egoEntry) {
          showEgo(d.id, d.name, d[commCol]);
        } else {
          showMembers(d[commCol]);
        }
      });
  }

  function showMembers(commId) {
    vizArea.html("");
    bc.html(`<a onclick="this.closest('.viz').querySelector('.explorer-controls button').click()">← Overview</a> → Community ${commId}`);
    // Re-attach back handler
    bc.select("a").on("click", showOverview);

    const commCol = `${currentScape}_community`;
    const members = topPeople.filter(p => p[commCol] === commId).sort((a, b) => (b[`${currentScape}_degree`] || 0) - (a[`${currentScape}_degree`] || 0));

    if (!members.length) { vizArea.append("p").style("text-align", "center").style("color", "#666").style("padding", "40px").text("No top-500 people in this community."); return; }

    const table = vizArea.append("div").attr("class", "member-table");
    table.append("div").attr("class", "member-row header").html("<div>Name</div><div>Country</div><div>Films</div><div>Rating</div><div></div>");

    members.slice(0, 40).forEach(p => {
      const row = table.append("div").attr("class", "member-row");
      row.append("div").attr("class", "name").text(p.primaryName || "");
      row.append("div").attr("class", "country").text(p.country || "—");
      row.append("div").text(p.n_films || "—");
      row.append("div").attr("class", "rating").text(p.avg_rating ? p.avg_rating.toFixed(1) : "—");
      const egoEntry = egoData?.[p.nconst];
      if (egoEntry) {
        row.append("div").append("button").attr("class", "ego-btn").text("Ego →")
          .on("click", () => showEgo(p.nconst, p.primaryName, commId));
      } else {
        row.append("div");
      }
    });
  }

  function showEgo(nconst, name, commId) {
    vizArea.html("");
    bc.html("");
    bc.append("a").text("← Overview").on("click", showOverview);
    bc.append("span").text(" → ");
    bc.append("a").text(`Community ${commId}`).on("click", () => showMembers(commId));
    bc.append("span").text(` → ${name}`);

    const person = egoData?.[nconst];
    if (!person) { vizArea.append("p").style("text-align", "center").style("color", "#666").text("No ego network data."); return; }

    vizArea.append("div").style("text-align", "center").style("font-size", "20px").style("font-weight", "600").style("color", "#fff").style("margin-bottom", "16px").text(name);
    const panels = vizArea.append("div").attr("class", "ego-panels");

    [{key: "ethnoscape_cross", label: "Cross-Origin Network", color: "#00b894"},
     {key: "ethnoscape_same", label: "Same-Origin Network", color: "#e17055"}].forEach(panel => {
      const net = person.networks[panel.key];
      if (!net?.nodes?.length) return;
      const pd = panels.append("div").attr("class", "ego-panel");
      pd.append("div").attr("class", "panel-label").style("color", panel.color).text(panel.label);
      const svg = pd.append("svg").attr("viewBox", "0 0 400 400").style("width", "100%").style("max-width", "400px").style("height", "auto");
      svg.selectAll("line").data(net.edges).join("line")
        .attr("x1", d => net.nodes.find(n => n.id === d.source)?.x ?? 0).attr("y1", d => net.nodes.find(n => n.id === d.source)?.y ?? 0)
        .attr("x2", d => net.nodes.find(n => n.id === d.target)?.x ?? 0).attr("y2", d => net.nodes.find(n => n.id === d.target)?.y ?? 0)
        .attr("stroke", "#fff").attr("stroke-opacity", 0.15);
      svg.selectAll("circle").data(net.nodes).join("circle")
        .attr("cx", d => d.x).attr("cy", d => d.y).attr("r", d => d.ego ? 14 : 5)
        .attr("fill", d => d.ego ? panel.color : "#777").attr("opacity", 0.9);
      svg.selectAll(".lbl").data(net.nodes.filter(d => d.ego)).join("text").attr("class", "lbl")
        .attr("x", d => d.x).attr("y", d => d.y - 20).attr("text-anchor", "middle")
        .attr("fill", "#fff").attr("font-size", "12px").attr("font-weight", "600").text(d => d.name);
      // Neighbor names
      svg.selectAll(".nb").data(net.nodes.filter(d => !d.ego).slice(0, 10)).join("text").attr("class", "nb")
        .attr("x", d => d.x).attr("y", d => d.y - 9).attr("text-anchor", "middle")
        .attr("fill", "#999").attr("font-size", "8px").text(d => d.name?.split(" ").pop() || "");
      pd.append("div").attr("class", "count").text(`${net.nodes.length - 1} connections`);
    });
  }

  showOverview();
}

function renderSpotlight(people) {
  const container = d3.select("#spotlight-viz");
  const SCAPES = [
    {key: "mediascape", label: "Mediascape", color: "#6c5ce7"},
    {key: "ethnoscape_cross", label: "Cross-Origin", color: "#00b894"},
    {key: "ethnoscape_same", label: "Same-Origin", color: "#e17055"},
    {key: "financescape", label: "Financescape", color: "#fdcb6e"},
    {key: "ideoscape", label: "Ideoscape", color: "#0984e3"},
  ];
  const featured = ["Hans Zimmer","Francine Maisler","Bong Joon Ho","Samuel L. Jackson","Salman Khan","Brad Pitt","Robert Eggers","Hayao Miyazaki","Danny Elfman","Joaquim de Almeida"];

  const searchDiv = container.append("div").attr("class", "spotlight-search");
  const input = searchDiv.append("input").attr("placeholder", "Search for a person...");
  const results = searchDiv.append("div").attr("class", "spotlight-results");
  const btns = container.append("div").attr("class", "featured-btns");
  const profile = container.append("div");

  function show(p) {
    profile.html("");
    const card = profile.append("div").attr("class", "profile-card");
    card.append("div").attr("class", "profile-name").text(p.primaryName);
    card.append("div").attr("class", "profile-meta").text([p.country || "Unknown", `${p.n_films || "?"} films`, `Rating: ${p.avg_rating?.toFixed(1) || "?"}`].join(" · "));
    card.append("div").style("font-size", "13px").style("color", "#666").style("margin-bottom", "16px").text("Connectivity percentile — how connected this person is compared to others in each network");

    // Compute percentile rank for each scape (among all 500 people in this dataset)
    const vals = SCAPES.map(s => {
      const key = `${s.key}_degree`;
      const raw = p[key] || 0;
      // Count how many of the 500 people have a lower value
      const allVals = people.map(pp => pp[key] || 0).filter(v => v > 0);
      const rank = allVals.filter(v => v <= raw).length;
      const pct = allVals.length > 0 ? (rank / allVals.length) * 100 : 0;
      return {...s, raw, pct, present: raw > 0};
    });

    const barH = SCAPES.length * 64 + 20;
    const barW = 1100;
    const svg = card.append("svg").attr("width", "100%").attr("height", barH)
      .attr("viewBox", `0 0 ${barW} ${barH}`);
    const x = d3.scaleLinear().domain([0, 100]).range([0, barW * 0.5]);

    vals.forEach((d, i) => {
      const yy = i * 64 + 12;
      svg.append("text").attr("x", barW * 0.2 - 12).attr("y", yy + 28)
        .attr("text-anchor", "end").attr("fill", "#aaa").attr("font-size", "18px")
        .text(d.label);

      if (d.present) {
        svg.append("rect").attr("x", barW * 0.2).attr("y", yy + 4)
          .attr("width", x(d.pct)).attr("height", 42)
          .attr("fill", d.color).attr("rx", 6).attr("opacity", 0.85);
        // Percentile label
        svg.append("text").attr("x", barW * 0.2 + x(d.pct) + 12).attr("y", yy + 30)
          .attr("fill", "#fff").attr("font-size", "17px").attr("font-weight", "600")
          .text(`Top ${(100 - d.pct).toFixed(1)}%`);
      } else {
        svg.append("text").attr("x", barW * 0.2 + 8).attr("y", yy + 30)
          .attr("fill", "#555").attr("font-size", "16px")
          .text("Not in this network");
      }
    });
  }

  input.on("input", function() {
    const q = this.value.toLowerCase().trim(); results.html("");
    if (q.length < 2) return;
    const matches = people.filter(p => p.primaryName?.toLowerCase().includes(q)).slice(0, 10);
    if (!matches.length) { results.append("div").style("color", "#666").text("No results found"); return; }
    matches.forEach(p => results.append("div").text(p.primaryName).on("click", () => { input.property("value", p.primaryName); results.html(""); show(p); }));
  });

  featured.forEach(name => {
    const p = people.find(pp => pp.primaryName === name);
    if (p) btns.append("button").text(name).on("click", () => show(p));
  });

  const first = people.find(p => p.primaryName === featured[0]);
  if (first) show(first);
}

function renderButterfly(data) {
  const container = d3.select("#butterfly-viz");
  const shared = data.shared;
  const left = data.left;
  const right = data.right;

  const maxCount = d3.max(shared, d => Math.max(d.anderson_count, d.spielberg_count));
  const rowH = 44, m = {top: 80, right: 40, bottom: 40, left: 40};
  const nameColW = 200;
  const barMaxW = 240;
  const width = m.left + barMaxW + nameColW + barMaxW + m.right;
  const height = m.top + shared.length * rowH + m.bottom;
  const centerX = m.left + barMaxW + nameColW / 2;

  const svg = container.append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .style("width", "100%").style("max-width", width + "px").style("height", "auto");

  const tooltip = d3.select("body").append("div")
    .style("position", "fixed").style("background", "rgba(20,20,32,0.95)")
    .style("padding", "10px 14px").style("border-radius", "8px")
    .style("font-size", "13px").style("color", "#ccc").style("pointer-events", "none")
    .style("opacity", 0).style("z-index", 9999).style("max-width", "320px")
    .style("border", "1px solid #333");

  const xLeft = d3.scaleLinear().domain([0, maxCount]).range([0, barMaxW]);

  // Headers
  svg.append("text").attr("x", m.left + barMaxW / 2).attr("y", 24)
    .attr("text-anchor", "middle").attr("fill", "#00b894").attr("font-size", "18px").attr("font-weight", "700")
    .text(left.name);
  svg.append("text").attr("x", m.left + barMaxW / 2).attr("y", 44)
    .attr("text-anchor", "middle").attr("fill", "#888").attr("font-size", "12px")
    .text(`Clustering: ${left.clustering} · ${left.n_films} films · Avg: ${left.avg_rating}`);

  svg.append("text").attr("x", m.left + barMaxW + nameColW + barMaxW / 2).attr("y", 24)
    .attr("text-anchor", "middle").attr("fill", "#e17055").attr("font-size", "18px").attr("font-weight", "700")
    .text(right.name);
  svg.append("text").attr("x", m.left + barMaxW + nameColW + barMaxW / 2).attr("y", 44)
    .attr("text-anchor", "middle").attr("fill", "#888").attr("font-size", "12px")
    .text(`Clustering: ${right.clustering} · ${right.n_films} films · Avg: ${right.avg_rating}`);

  // Column headers
  svg.append("text").attr("x", centerX).attr("y", m.top - 12)
    .attr("text-anchor", "middle").attr("fill", "#666").attr("font-size", "11px")
    .text("SHARED COLLABORATOR");
  svg.append("text").attr("x", m.left + barMaxW / 2).attr("y", m.top - 12)
    .attr("text-anchor", "middle").attr("fill", "#666").attr("font-size", "11px")
    .text("← Films together");
  svg.append("text").attr("x", m.left + barMaxW + nameColW + barMaxW / 2).attr("y", m.top - 12)
    .attr("text-anchor", "middle").attr("fill", "#666").attr("font-size", "11px")
    .text("Films together →");

  // Rows
  shared.forEach((d, i) => {
    const y = m.top + i * rowH + rowH / 2;

    // Alternating row background
    if (i % 2 === 0) {
      svg.append("rect").attr("x", 0).attr("y", y - rowH / 2 + 2).attr("width", width).attr("height", rowH - 4)
        .attr("fill", "rgba(255,255,255,0.02)").attr("rx", 4);
    }

    // Center name
    svg.append("text").attr("x", centerX).attr("y", y + 1)
      .attr("text-anchor", "middle").attr("fill", "#ddd").attr("font-size", "13px").attr("font-weight", "600")
      .text(d.name);
    // Role tag
    const role = d.role.replace("_", " ");
    svg.append("text").attr("x", centerX).attr("y", y + 15)
      .attr("text-anchor", "middle").attr("fill", "#666").attr("font-size", "10px")
      .text(role);

    // Left bar (Anderson) — grows leftward from center
    const leftBarW = xLeft(d.anderson_count);
    const leftBarX = m.left + barMaxW - leftBarW;
    svg.append("rect")
      .attr("x", leftBarX).attr("y", y - 10)
      .attr("width", leftBarW).attr("height", 20)
      .attr("fill", "#00b894").attr("opacity", 0.7).attr("rx", 4)
      .style("cursor", "pointer")
      .on("mouseover", (event) => {
        tooltip.style("opacity", 1).html(
          `<strong>${d.name}</strong> with ${left.name}:<br>` +
          d.anderson_films.map(f => `${f.title} (${f.rating})`).join("<br>")
        );
      })
      .on("mousemove", (event) => {
        tooltip.style("left", (event.clientX + 14) + "px").style("top", (event.clientY - 14) + "px");
      })
      .on("mouseout", () => tooltip.style("opacity", 0));

    // Left count
    svg.append("text").attr("x", leftBarX - 8).attr("y", y + 4)
      .attr("text-anchor", "end").attr("fill", "#00b894").attr("font-size", "13px").attr("font-weight", "700")
      .text(d.anderson_count);

    // Right bar (Spielberg) — grows rightward from center
    const rightBarX = m.left + barMaxW + nameColW;
    const rightBarW = xLeft(d.spielberg_count);
    svg.append("rect")
      .attr("x", rightBarX).attr("y", y - 10)
      .attr("width", rightBarW).attr("height", 20)
      .attr("fill", "#e17055").attr("opacity", 0.7).attr("rx", 4)
      .style("cursor", "pointer")
      .on("mouseover", (event) => {
        tooltip.style("opacity", 1).html(
          `<strong>${d.name}</strong> with ${right.name}:<br>` +
          d.spielberg_films.map(f => `${f.title} (${f.rating})`).join("<br>")
        );
      })
      .on("mousemove", (event) => {
        tooltip.style("left", (event.clientX + 14) + "px").style("top", (event.clientY - 14) + "px");
      })
      .on("mouseout", () => tooltip.style("opacity", 0));

    // Right count
    svg.append("text").attr("x", rightBarX + rightBarW + 8).attr("y", y + 4)
      .attr("text-anchor", "start").attr("fill", "#e17055").attr("font-size", "13px").attr("font-weight", "700")
      .text(d.spielberg_count);
  });
}

function renderSom(data) {
  const container = d3.select("#som-viz");

  // Archetype labels positioned at SOM grid coordinates (row, col)
  // Identified from feature analysis of the trained SOM
  const ARCHETYPES = [
    {row: 14, col: 1, label: "Industry Hubs", sub: "Brad Pitt, Tom Cruise, DiCaprio", color: "#fdcb6e"},
    {row: 12, col: 0, label: "Legacy Stars", sub: "Hitchcock, Connery, Aykroyd", color: "#e17055"},
    {row: 2, col: 10, label: "Classic Auteurs", sub: "Vivien Leigh, Dario Argento", color: "#00b894"},
    {row: 0, col: 10, label: "Golden Age", sub: "Cary Grant, James Mason", color: "#55efc4"},
    {row: 8, col: 6, label: "Global Directors", sub: "Cronenberg, Annaud, von Trier", color: "#0984e3"},
    {row: 9, col: 0, label: "Int'l Crossovers", sub: "Branagh, Binoche, Jackie Chan", color: "#a29bfe"},
    {row: 0, col: 0, label: "Commercial", sub: "Low-rated franchise films", color: "#e63946"},
    {row: 3, col: 6, label: "Working Actors", sub: "Majority of the industry", color: "#636e72"},
  ];

  // No toggle — just show archetypes

  const gx = data.grid_size.x, gy = data.grid_size.y;
  const cellSize = 42, margin = 16;
  const width = gx * cellSize + 2 * margin;
  const height = gy * cellSize + 2 * margin + 36;

  // No buttons needed
  const svg = container.append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .style("width", "100%").style("max-width", width + "px").style("height", "auto");

  const tooltip = d3.select("body").append("div")
    .style("position", "fixed").style("background", "rgba(20,20,32,0.95)")
    .style("padding", "10px 14px").style("border-radius", "8px")
    .style("font-size", "13px").style("color", "#ddd").style("pointer-events", "none")
    .style("opacity", 0).style("z-index", 1000)
    .style("border", "1px solid #333").style("max-width", "260px");

  // Assign each cell to its nearest archetype
  const cellArch = [];
  for (let i = 0; i < gx; i++) {
    cellArch[i] = [];
    for (let j = 0; j < gy; j++) {
      let minD = Infinity, nearest = 0;
      ARCHETYPES.forEach((a, idx) => {
        const d = Math.sqrt((i - a.row) ** 2 + (j - a.col) ** 2);
        if (d < minD) { minD = d; nearest = idx; }
      });
      cellArch[i][j] = nearest;
    }
  }

  // U-matrix extent for boundary darkening
  const uFlat = data.umatrix ? data.umatrix.flat() : [0];
  const uMin = Math.min(...uFlat), uMax = Math.max(...uFlat);

  function render() {
    svg.selectAll("*").remove();

    svg.append("text")
      .attr("x", width / 2).attr("y", 22)
      .attr("text-anchor", "middle").attr("fill", "#ccc").attr("font-size", "14px")
      .text("Film Professional Archetypes");

    const cellGroup = svg.append("g").attr("transform", `translate(${margin}, ${margin + 28})`);

    for (let i = 0; i < gx; i++) {
      for (let j = 0; j < gy; j++) {
        const pop = data.populations[i][j];
        const ppl = data.sample_people?.[i]?.[j] || [];
        const archIdx = cellArch[i][j];
        const arch = ARCHETYPES[archIdx];

        const uVal = data.umatrix?.[i]?.[j] ?? 0;
        const brightness = 1 - (uVal - uMin) / (uMax - uMin || 1);
        const base = d3.color(arch.color);
        const fill = pop > 0
          ? `rgba(${base.r}, ${base.g}, ${base.b}, ${0.15 + brightness * 0.75})`
          : "#0a0a0a";

        cellGroup.append("rect")
          .attr("x", j * cellSize).attr("y", i * cellSize)
          .attr("width", cellSize - 2).attr("height", cellSize - 2)
          .attr("fill", fill).attr("rx", 4)
          .style("cursor", "crosshair")
          .on("mouseover", (event) => {
            tooltip.style("opacity", 1).html(
              `<strong>${arch.label}</strong><br>` +
              `Population: ${pop}<br>` +
              (ppl.length ? ppl.slice(0, 4).join(", ") : "")
            );
          })
          .on("mousemove", (event) => {
            tooltip.style("left", (event.clientX + 14) + "px").style("top", (event.clientY - 14) + "px");
          })
          .on("mouseout", () => tooltip.style("opacity", 0));
      }
    }

    // Archetype labels centered in each region
    const labelGroup = cellGroup.append("g");
    ARCHETYPES.forEach((a, aIdx) => {
      // Find center of all cells belonging to this archetype
      let sumR = 0, sumC = 0, count = 0;
      for (let i = 0; i < gx; i++) {
        for (let j = 0; j < gy; j++) {
          if (cellArch[i][j] === aIdx) { sumR += i; sumC += j; count++; }
        }
      }
      const lx = (sumC / count) * cellSize + cellSize / 2;
      const ly = (sumR / count) * cellSize + cellSize / 2;
      labelGroup.append("rect")
        .attr("x", lx - 54).attr("y", ly - 18)
        .attr("width", 108).attr("height", 36).attr("rx", 6)
        .attr("fill", "rgba(0,0,0,0.8)")
        .attr("stroke", a.color).attr("stroke-width", 1.5)
        .attr("pointer-events", "none");
      labelGroup.append("text")
        .attr("x", lx).attr("y", ly - 3)
        .attr("text-anchor", "middle").attr("fill", a.color)
        .attr("font-size", "10px").attr("font-weight", "700")
        .attr("pointer-events", "none").text(a.label);
      labelGroup.append("text")
        .attr("x", lx).attr("y", ly + 10)
        .attr("text-anchor", "middle").attr("fill", "#aaa")
        .attr("font-size", "7px").attr("pointer-events", "none").text(a.sub);
    });
  }

  render("_umatrix");
}

// ---- Launch ----
main().catch(err => {
  console.error("Fatal error:", err);
  app.innerHTML = `<div style="color:#e63946;padding:40px;font-family:monospace;white-space:pre-wrap">
    <h2>Error loading page</h2>
    <p>${err.message}</p>
    <p>${err.stack}</p>
  </div>`;
});
