#!/usr/bin/env python3
"""Render analysis.json → evolution-map.html (interactive visualization).

Generates a single self-contained HTML file with D3.js v7 (from CDN).
Four panels: Timeline Swim Lanes, Citation Network, Author Sidebar, Detail Panel.

Usage:
    python3 render_html.py
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_PATH = SCRIPT_DIR / "analysis.json"
OUTPUT_PATH = SCRIPT_DIR / "evolution-map.html"

# Thread display order and colors
THREAD_COLORS = {
    "pos_casper": "#e63946",
    "sharding_da": "#457b9d",
    "plasma_l2": "#2a9d8f",
    "fee_markets": "#e9c46a",
    "pbs_mev": "#f4a261",
    "ssf": "#d62828",
    "issuance_economics": "#6a994e",
    "inclusion_lists": "#bc6c25",
    "based_preconf": "#7209b7",
    "zk_proofs": "#4361ee",
    "state_execution": "#606c38",
    "privacy_identity": "#9d4edd",
}

THREAD_ORDER = [
    "pos_casper", "sharding_da", "plasma_l2", "fee_markets",
    "pbs_mev", "ssf", "issuance_economics", "inclusion_lists",
    "based_preconf", "zk_proofs", "state_execution", "privacy_identity",
]

# Top author colors (up to 15, rest gray)
AUTHOR_COLORS = [
    "#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261",
    "#d62828", "#6a994e", "#bc6c25", "#7209b7", "#4361ee",
    "#606c38", "#9d4edd", "#264653", "#a8dadc", "#b5838d",
]


def main():
    with open(ANALYSIS_PATH) as f:
        data = json.load(f)

    viz_data = prepare_viz_data(data)
    viz_json = json.dumps(viz_data, separators=(",", ":"))

    html = generate_html(viz_json, data)

    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Written: {OUTPUT_PATH} ({size_kb:.0f} KB)")


def prepare_viz_data(data):
    """Prepare a compact version of analysis data for the HTML visualization."""
    topics = data["topics"]
    authors = data["authors"]
    threads = data["research_threads"]
    forks = data["forks"]
    graph = data["graph"]

    compact_topics = {}
    for tid, t in topics.items():
        compact_topics[tid] = {
            "id": t["id"],
            "t": t["title"],
            "a": t["author"],
            "d": t["date"],
            "inf": t["influence_score"],
            "th": t.get("research_thread"),
            "era": t.get("era"),
            "lk": t["like_count"],
            "vw": t["views"],
            "pc": t["posts_count"],
            "ind": t["in_degree"],
            "eips": t.get("eip_mentions", []),
            "peips": t.get("primary_eips", []),
            "cat": t.get("category_name", ""),
            "exc": t.get("first_post_excerpt", "")[:200],
            "out": t.get("outgoing_refs", []),
            "inc": t.get("incoming_refs", []),
            "parts": [p["username"] for p in t.get("participants", [])[:3]],
        }

    compact_authors = {}
    author_list = sorted(authors.values(), key=lambda a: a["influence_score"], reverse=True)
    for i, a in enumerate(author_list):
        compact_authors[a["username"]] = {
            "u": a["username"],
            "tc": a["topics_created"],
            "tp": a["total_posts"],
            "lk": a["total_likes"],
            "ind": a["total_in_degree"],
            "inf": a["influence_score"],
            "yrs": a["active_years"],
            "cats": a["category_focus"],
            "ths": a["thread_focus"],
            "tops": a["top_topics"][:5],
            "co": dict(list(a["co_researchers"].items())[:5]),
            "rank": i,
        }

    compact_threads = {}
    for tid, th in threads.items():
        compact_threads[tid] = {
            "id": tid,
            "n": th["name"],
            "tc": th["topic_count"],
            "dr": th["date_range"],
            "ka": dict(list(th["key_authors"].items())[:5]),
            "eips": th.get("eip_mentions", []),
            "tops": th["top_topics"][:10],
        }

    compact_forks = []
    for f in forks:
        compact_forks.append({
            "n": f["name"],
            "d": f["date"],
            "el": f.get("el_name"),
            "cl": f.get("cl_name"),
            "cn": f.get("combined_name"),
            "eips": f["eips"][:8],
            "rt": f.get("related_topics", [])[:10],
        })

    return {
        "meta": data["metadata"],
        "topics": compact_topics,
        "authors": compact_authors,
        "threads": compact_threads,
        "forks": compact_forks,
        "eras": data["eras"],
        "graph": {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        },
        "coGraph": data["co_author_graph"],
    }


def generate_html(viz_json, data):
    """Generate the full HTML document."""
    meta = data["metadata"]

    # Build the JS/CSS as a plain string to avoid f-string brace hell
    # We'll insert the data blob and a few Python values, but keep JS braces literal
    # by using a template with explicit markers.

    # Write CSS, HTML structure, then JS separately
    css = _build_css()
    js = _build_js()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ethereum Research Evolution Map</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
{css}
</style>
</head>
<body>
<div id="app">
  <header>
    <h1>Ethereum Research Evolution Map</h1>
    <div class="stats">
      <span>{meta['included']} topics</span>
      <span>{meta['included_edges']} citations</span>
      <span>2017\u20132026</span>
    </div>
    <div class="controls">
      <button id="btn-timeline" class="active" onclick="showView('timeline')">Timeline</button>
      <button id="btn-network" onclick="showView('network')">Network</button>
    </div>
  </header>
  <div id="main-area">
    <div id="timeline-view"></div>
    <div id="network-view"></div>
    <div id="detail-panel">
      <button class="close-btn" onclick="closeDetail()">&times;</button>
      <div id="detail-content"></div>
    </div>
  </div>
  <div id="sidebar">
    <div class="sidebar-section">
      <input type="text" id="search-box" placeholder="Search topics, authors, EIPs...">
    </div>
    <div class="sidebar-section">
      <h3>Research Threads</h3>
      <div id="thread-legend" class="thread-legend"></div>
    </div>
    <div class="sidebar-section">
      <h3>Top Authors</h3>
      <div id="author-list"></div>
    </div>
  </div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
const DATA = {viz_json};
const THREAD_COLORS = {json.dumps(THREAD_COLORS)};
const THREAD_ORDER = {json.dumps(THREAD_ORDER)};
const AUTHOR_COLORS = {json.dumps(AUTHOR_COLORS)};
{js}
</script>
</body>
</html>"""


def _build_css():
    return """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0a0a0f; color: #e0e0e0; overflow: hidden; height: 100vh; }
#app { display: grid; grid-template-rows: auto 1fr; grid-template-columns: 1fr 300px; height: 100vh; }

header { grid-column: 1 / -1; padding: 12px 20px; background: #12121a;
         border-bottom: 1px solid #2a2a3a; display: flex; align-items: center; gap: 20px; }
header h1 { font-size: 18px; font-weight: 600; color: #fff; white-space: nowrap; }
header .stats { font-size: 12px; color: #888; display: flex; gap: 15px; }
header .stats span { white-space: nowrap; }
.controls { display: flex; gap: 8px; margin-left: auto; }
.controls button { background: #1e1e2e; border: 1px solid #333; color: #ccc;
                   padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; }
.controls button:hover { background: #2a2a3e; }
.controls button.active { background: #333366; border-color: #5555aa; color: #fff; }

#main-area { grid-column: 1; overflow: hidden; position: relative; }
#sidebar { grid-column: 2; background: #12121a; border-left: 1px solid #2a2a3a; overflow-y: auto; }
#sidebar::-webkit-scrollbar { width: 6px; }
#sidebar::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

#timeline-view, #network-view { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
#timeline-view { display: block; }
#network-view { display: none; }

/* Timeline */
.timeline-container { width: 100%; height: 100%; overflow-x: auto; overflow-y: auto; }
.timeline-container::-webkit-scrollbar { height: 10px; width: 10px; }
.timeline-container::-webkit-scrollbar-thumb { background: #333; border-radius: 5px; }
.fork-line { stroke: #444; stroke-width: 1; stroke-dasharray: 4,4; }
.fork-label { fill: #666; font-size: 10px; font-weight: 500; }
.era-bg { opacity: 0.03; }

/* CRITICAL: pointer-events:all so circles with transparent fill are still hoverable */
.topic-circle { cursor: pointer; pointer-events: all; }
.edge-line { stroke: #556; }

/* Network */
.net-node { cursor: pointer; }
.net-link { stroke: #334; }
.fork-diamond { fill: #ffcc00; stroke: #aa8800; stroke-width: 1.5; cursor: pointer; }

/* Sidebar */
.sidebar-section { padding: 12px 14px; border-bottom: 1px solid #1e1e2e; }
.sidebar-section h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
                      color: #666; margin-bottom: 8px; }
.thread-legend { display: flex; flex-wrap: wrap; gap: 4px; }
.thread-chip { font-size: 10px; padding: 2px 6px; border-radius: 3px; cursor: pointer;
               opacity: 0.7; transition: opacity 0.15s; white-space: nowrap; }
.thread-chip:hover, .thread-chip.active { opacity: 1; }
.author-item { padding: 6px 0; cursor: pointer; display: flex; align-items: center; gap: 8px; }
.author-item:hover { background: #1a1a2a; }
.author-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.author-name { font-size: 12px; flex: 1; min-width: 0; overflow: hidden;
               text-overflow: ellipsis; white-space: nowrap; }
.author-count { font-size: 10px; color: #666; flex-shrink: 0; }
.author-item.active .author-name { color: #fff; font-weight: 600; }

/* Detail panel */
#detail-panel { display: none; position: absolute; top: 0; right: 0; width: 420px; height: 100%;
                background: #15151f; border-left: 1px solid #2a2a3a; overflow-y: auto;
                z-index: 100; padding: 16px; }
#detail-panel.open { display: block; }
#detail-panel .close-btn { position: absolute; top: 8px; right: 12px; background: none;
                           border: none; color: #666; font-size: 18px; cursor: pointer; }
#detail-panel .close-btn:hover { color: #fff; }
#detail-panel h2 { font-size: 16px; color: #fff; margin-bottom: 4px;
                   padding-right: 30px; line-height: 1.3; }
#detail-panel .meta { font-size: 12px; color: #888; margin-bottom: 12px; }
#detail-panel .meta a { color: #7788cc; text-decoration: none; }
#detail-panel .meta a:hover { text-decoration: underline; }
.detail-stat { display: flex; justify-content: space-between; padding: 4px 0;
               font-size: 12px; border-bottom: 1px solid #1a1a2a; }
.detail-stat .label { color: #888; }
.detail-stat .value { color: #ccc; }
.detail-excerpt { font-size: 12px; color: #999; margin: 12px 0; line-height: 1.5; font-style: italic; }
.detail-refs { margin-top: 12px; }
.detail-refs h4 { font-size: 11px; text-transform: uppercase; color: #666; margin-bottom: 6px; }
.detail-refs .ref-item { font-size: 11px; padding: 3px 0; }
.detail-refs .ref-item a { color: #7788cc; text-decoration: none; cursor: pointer; }
.detail-refs .ref-item a:hover { text-decoration: underline; }
.eip-tag { display: inline-block; font-size: 10px; padding: 1px 5px; background: #1e2a3a;
           border: 1px solid #2a3a5a; border-radius: 3px; margin: 1px; color: #88aacc; }
.eip-tag.primary { background: #1a3a1a; border-color: #2a5a2a; color: #88cc88; }
.fork-tag { display: inline-block; font-size: 10px; padding: 1px 5px; background: #3a3a1a;
            border: 1px solid #5a5a2a; border-radius: 3px; margin: 1px; color: #cccc88; }

#search-box { width: 100%; padding: 6px 8px; background: #1a1a2a; border: 1px solid #333;
              border-radius: 4px; color: #ccc; font-size: 12px; margin-bottom: 8px; }
#search-box:focus { outline: none; border-color: #555; }

.tooltip { position: fixed; background: #1e1e2e; border: 1px solid #444; border-radius: 4px;
           padding: 8px 12px; font-size: 11px; color: #ccc; pointer-events: none;
           z-index: 500; max-width: 350px; line-height: 1.4; display: none;
           box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
"""


def _build_js():
    # Return JS as a plain string — no Python f-string interpolation needed
    # (DATA, THREAD_COLORS etc. are injected as separate <script> constants)
    return r"""
// === GLOBALS ===
let activeView = 'timeline';
let activeThread = null;
let activeAuthor = null;
let simulation = null;
let hoveredTopicId = null;

// Build index: topic_id -> set of connected topic_ids (for edge highlighting)
const topicEdgeIndex = {};
DATA.graph.edges.forEach(e => {
  const s = String(e.source), t = String(e.target);
  if (!topicEdgeIndex[s]) topicEdgeIndex[s] = new Set();
  if (!topicEdgeIndex[t]) topicEdgeIndex[t] = new Set();
  topicEdgeIndex[s].add(Number(e.target));
  topicEdgeIndex[t].add(Number(e.source));
});

// Author color map
const authorList = Object.values(DATA.authors).sort((a,b) => b.inf - a.inf);
const authorColorMap = {};
authorList.forEach((a, i) => { authorColorMap[a.u] = i < 15 ? AUTHOR_COLORS[i] : '#555'; });

// === INIT ===
document.addEventListener('DOMContentLoaded', () => {
  buildSidebar();
  buildTimeline();
  setupSearch();
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeDetail(); clearFilters(); }
  });
});

// === VIEW SWITCHING ===
function showView(view) {
  activeView = view;
  document.getElementById('timeline-view').style.display = view === 'timeline' ? 'block' : 'none';
  document.getElementById('network-view').style.display = view === 'network' ? 'block' : 'none';
  document.getElementById('btn-timeline').classList.toggle('active', view === 'timeline');
  document.getElementById('btn-network').classList.toggle('active', view === 'network');
  if (view === 'network' && !document.querySelector('#network-view svg')) buildNetwork();
}

// === SIDEBAR ===
function buildSidebar() {
  const legend = document.getElementById('thread-legend');
  THREAD_ORDER.forEach(tid => {
    const th = DATA.threads[tid];
    if (!th) return;
    const chip = document.createElement('span');
    chip.className = 'thread-chip';
    chip.style.background = THREAD_COLORS[tid] + '33';
    chip.style.color = THREAD_COLORS[tid];
    chip.style.border = '1px solid ' + THREAD_COLORS[tid] + '66';
    chip.textContent = th.n.split('&')[0].trim();
    chip.title = th.n + ' (' + th.tc + ' topics)';
    chip.onclick = () => toggleThread(tid);
    chip.dataset.thread = tid;
    legend.appendChild(chip);
  });

  const list = document.getElementById('author-list');
  authorList.slice(0, 25).forEach((a, i) => {
    const item = document.createElement('div');
    item.className = 'author-item';
    item.dataset.author = a.u;
    item.innerHTML = '<span class="author-dot" style="background:' + authorColorMap[a.u] + '"></span>' +
      '<span class="author-name">' + a.u + '</span>' +
      '<span class="author-count">' + a.tc + '</span>';
    item.onclick = () => toggleAuthor(a.u);
    list.appendChild(item);
  });
}

function clearFilters() {
  activeThread = null;
  activeAuthor = null;
  document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.author-item').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  applyFilters();
}

function toggleThread(tid) {
  activeThread = activeThread === tid ? null : tid;
  activeAuthor = null;
  document.querySelectorAll('.thread-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.thread === activeThread));
  document.querySelectorAll('.author-item').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  applyFilters();
}

function toggleAuthor(username) {
  activeAuthor = activeAuthor === username ? null : username;
  activeThread = null;
  document.querySelectorAll('.author-item').forEach(c =>
    c.classList.toggle('active', c.dataset.author === activeAuthor));
  document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  applyFilters();
}

function applyFilters() {
  if (activeView === 'timeline') filterTimeline();
  else filterNetwork();
}

// === SEARCH ===
function setupSearch() {
  const box = document.getElementById('search-box');
  let timeout;
  box.addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      const q = box.value.toLowerCase().trim();
      if (!q) { applyFilters(); return; }
      // Clear sidebar filters when searching
      activeThread = null;
      activeAuthor = null;
      document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
      document.querySelectorAll('.author-item').forEach(c => c.classList.remove('active'));
      filterBySearch(q);
    }, 200);
  });
}

function filterBySearch(q) {
  const matching = new Set();
  Object.values(DATA.topics).forEach(t => {
    if (t.t.toLowerCase().includes(q) || t.a.toLowerCase().includes(q) ||
        (t.cat && t.cat.toLowerCase().includes(q)) ||
        t.eips.some(e => ('eip-'+e).includes(q) || (''+e) === q)) {
      matching.add(t.id);
    }
  });
  highlightTopicSet(matching);
}

function highlightTopicSet(ids) {
  if (activeView === 'timeline') {
    d3.selectAll('.topic-circle')
      .attr('opacity', d => ids.has(d.id) ? 0.9 : 0.04)
      .attr('r', d => ids.has(d.id) ? tlRScale(d.inf) * 1.3 : tlRScale(d.inf));
    d3.selectAll('.edge-line').attr('stroke-opacity', 0.01);
  } else {
    d3.selectAll('.net-node circle').attr('opacity', d => ids.has(d.id) ? 0.9 : 0.06);
    d3.selectAll('.net-link').attr('stroke-opacity', 0.02);
  }
}

// === TIMELINE ===
let tlRScale; // shared so search can use it

function buildTimeline() {
  const container = document.getElementById('timeline-view');
  const width = Math.max(container.clientWidth, 3200);
  const height = container.clientHeight || 700;

  const margin = {top: 50, right: 40, bottom: 30, left: 180};
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  // Group topics by thread for swim lanes
  const threadTopics = {};
  THREAD_ORDER.forEach(tid => { threadTopics[tid] = []; });
  threadTopics['_other'] = [];

  Object.values(DATA.topics).forEach(t => {
    const th = t.th;
    if (th && threadTopics[th]) threadTopics[th].push(t);
    else threadTopics['_other'].push(t);
  });

  const laneOrder = [...THREAD_ORDER.filter(t => (threadTopics[t]||[]).length > 0), '_other'];
  const laneH = plotH / laneOrder.length;

  // Time scale
  const allDates = Object.values(DATA.topics).map(t => new Date(t.d)).filter(d => !isNaN(d));
  const xScale = d3.scaleTime()
    .domain([d3.min(allDates), d3.max(allDates)])
    .range([0, plotW]);

  // Size scale
  const maxInf = d3.max(Object.values(DATA.topics), t => t.inf) || 1;
  const rScale = d3.scaleSqrt().domain([0, maxInf]).range([2.5, 14]);
  tlRScale = rScale; // expose for search

  // Create SVG
  const wrapper = document.createElement('div');
  wrapper.className = 'timeline-container';
  container.appendChild(wrapper);

  const svg = d3.select(wrapper).append('svg')
    .attr('width', width)
    .attr('height', height);

  const g = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

  // Era backgrounds
  const eraColors = ['#334', '#343', '#334', '#433', '#343'];
  DATA.eras.forEach((era, i) => {
    const x0 = xScale(new Date(era.start));
    const x1 = xScale(new Date(era.end));
    g.append('rect').attr('class', 'era-bg')
      .attr('x', x0).attr('y', 0).attr('width', x1-x0).attr('height', plotH)
      .attr('fill', eraColors[i] || '#333');
    g.append('text').attr('x', (x0+x1)/2).attr('y', -8)
      .attr('text-anchor', 'middle').attr('fill', '#555').attr('font-size', 10)
      .text(era.name);
  });

  // Fork lines
  DATA.forks.forEach(f => {
    if (!f.d) return;
    const x = xScale(new Date(f.d));
    g.append('line').attr('class', 'fork-line')
      .attr('x1', x).attr('x2', x).attr('y1', -5).attr('y2', plotH);
    g.append('text').attr('class', 'fork-label')
      .attr('x', x).attr('y', plotH + 15).attr('text-anchor', 'middle')
      .text(f.cn || f.n);
  });

  // Swim lane labels + separators
  const laneIdx = {};
  laneOrder.forEach((tid, i) => {
    laneIdx[tid] = i;
    const y = i * laneH + laneH / 2;
    const name = tid === '_other' ? 'Other' : (DATA.threads[tid] ? DATA.threads[tid].n : tid);
    const color = tid === '_other' ? '#555' : (THREAD_COLORS[tid] || '#555');
    g.append('text').attr('x', -10).attr('y', y)
      .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
      .attr('fill', color).attr('font-size', 11).attr('font-weight', 500)
      .text(name.length > 22 ? name.slice(0, 20) + '\u2026' : name);
    if (i > 0) {
      g.append('line').attr('x1', 0).attr('x2', plotW)
        .attr('y1', i * laneH).attr('y2', i * laneH)
        .attr('stroke', '#1a1a2a').attr('stroke-width', 0.5);
    }
  });

  // Position topics within swim lanes using deterministic jitter
  const topicPos = {};
  Object.values(DATA.topics).forEach(t => {
    const th = (t.th && laneIdx[t.th] !== undefined) ? t.th : '_other';
    const lane = laneIdx[th];
    const x = xScale(new Date(t.d));
    const yBase = lane * laneH + laneH * 0.12;
    const yRange = laneH * 0.76;
    const y = yBase + (hashCode(t.id) % 100) / 100 * yRange;
    topicPos[t.id] = {x: x, y: y};
  });

  // Draw edges (below circles)
  const edgeG = g.append('g');
  DATA.graph.edges.forEach(e => {
    const s = topicPos[e.source];
    const t = topicPos[e.target];
    if (s && t) {
      edgeG.append('line').attr('class', 'edge-line')
        .attr('x1', s.x).attr('y1', s.y).attr('x2', t.x).attr('y2', t.y)
        .attr('stroke-opacity', 0.06)
        .datum({source: e.source, target: e.target});
    }
  });

  // Draw topic circles
  const circleG = g.append('g');
  Object.values(DATA.topics).forEach(t => {
    const pos = topicPos[t.id];
    if (!pos) return;
    const color = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';

    circleG.append('circle')
      .attr('class', 'topic-circle')
      .attr('cx', pos.x).attr('cy', pos.y)
      .attr('r', rScale(t.inf))
      .attr('fill', color)
      .attr('stroke', color)
      .attr('stroke-width', 0.5)
      .attr('opacity', 0.65)
      .datum(t)
      .on('click', function(ev, d) { showDetail(d); })
      .on('mouseover', function(ev, d) { onTimelineHover(ev, d, true); })
      .on('mouseout', function(ev, d) { onTimelineHover(ev, d, false); });
  });

  // X axis
  const xAxis = d3.axisBottom(xScale).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
  g.append('g').attr('transform', 'translate(0,' + plotH + ')').call(xAxis)
    .selectAll('text').attr('fill', '#666').attr('font-size', 10);
  g.selectAll('.domain, .tick line').attr('stroke', '#333');
}

function onTimelineHover(ev, d, entering) {
  if (entering) {
    hoveredTopicId = d.id;
    showTooltip(ev, d);

    // Highlight this topic and its direct connections
    const connected = topicEdgeIndex[String(d.id)] || new Set();

    d3.selectAll('.topic-circle')
      .attr('opacity', function(t) {
        if (t.id === d.id) return 1;
        if (connected.has(t.id)) return 0.8;
        // Respect active filter
        if (activeThread && t.th !== activeThread) return 0.03;
        if (activeAuthor && t.a !== activeAuthor) return 0.03;
        return 0.12;
      });

    d3.selectAll('.edge-line')
      .attr('stroke-opacity', function(e) {
        if (e.source === d.id || e.target === d.id) return 0.5;
        return 0.02;
      })
      .attr('stroke', function(e) {
        if (e.source === d.id || e.target === d.id) return '#88aaff';
        return '#556';
      });
  } else {
    hoveredTopicId = null;
    hideTooltip();
    // Restore to current filter state
    filterTimeline();
  }
}

function filterTimeline() {
  const hasFilter = activeThread || activeAuthor;

  d3.selectAll('.topic-circle')
    .attr('opacity', function(d) {
      if (hasFilter) {
        if (activeThread && d.th !== activeThread) return 0.04;
        if (activeAuthor && d.a !== activeAuthor) return 0.04;
        return 0.85;
      }
      return 0.7;
    })
    .attr('r', function(d) { return tlRScale(d.inf); });

  d3.selectAll('.edge-line')
    .attr('stroke', '#556')
    .attr('stroke-opacity', function(e) {
      if (!hasFilter) return 0.06;
      const sT = DATA.topics[e.source];
      const tT = DATA.topics[e.target];
      if (activeThread) {
        if (sT && tT && sT.th === activeThread && tT.th === activeThread) return 0.25;
        return 0.01;
      }
      if (activeAuthor) {
        if ((sT && sT.a === activeAuthor) || (tT && tT.a === activeAuthor)) return 0.25;
        return 0.01;
      }
      return 0.06;
    });
}

// === NETWORK ===
function buildNetwork() {
  const container = document.getElementById('network-view');
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  const g = svg.append('g');

  // Zoom
  svg.call(d3.zoom().scaleExtent([0.15, 5]).on('zoom', function(ev) {
    g.attr('transform', ev.transform);
  }));

  // Prepare data
  const nodes = DATA.graph.nodes.map(function(n) { return Object.assign({}, n); });
  const nodeMap = {};
  nodes.forEach(function(n) { nodeMap[n.id] = n; });

  const links = DATA.graph.edges
    .filter(function(e) { return nodeMap[e.source] && nodeMap[e.target]; })
    .map(function(e) { return {source: e.source, target: e.target}; });

  // Add fork nodes as diamonds
  DATA.forks.forEach(function(f) {
    if (!f.d) return;
    var forkNode = {id: 'fork_' + f.n, title: f.cn || f.n, isFork: true, date: f.d};
    nodes.push(forkNode);
    nodeMap[forkNode.id] = forkNode;
    (f.rt || []).forEach(function(tid) {
      if (nodeMap[tid]) links.push({source: forkNode.id, target: tid});
    });
  });

  const maxInf = d3.max(nodes, function(n) { return n.influence || 0; }) || 1;
  const rScale = d3.scaleSqrt().domain([0, maxInf]).range([3, 16]);

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(function(d) { return d.id; }).distance(60).strength(0.1))
    .force('charge', d3.forceManyBody().strength(-30))
    .force('center', d3.forceCenter(width/2, height/2))
    .force('collision', d3.forceCollide().radius(function(d) {
      return (d.isFork ? 8 : rScale(d.influence || 0)) + 2;
    }));

  const link = g.append('g').selectAll('line')
    .data(links).join('line')
    .attr('class', 'net-link')
    .attr('stroke-opacity', 0.12);

  const node = g.append('g').selectAll('g')
    .data(nodes).join('g')
    .attr('class', 'net-node')
    .call(d3.drag()
      .on('start', function(ev, d) {
        if (!ev.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', function(ev, d) { d.fx = ev.x; d.fy = ev.y; })
      .on('end', function(ev, d) {
        if (!ev.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      })
    );

  // Fork diamonds
  node.filter(function(d) { return d.isFork; }).append('rect')
    .attr('class', 'fork-diamond')
    .attr('width', 12).attr('height', 12)
    .attr('transform', 'rotate(45)')
    .attr('x', -6).attr('y', -6);

  // Topic circles
  node.filter(function(d) { return !d.isFork; }).append('circle')
    .attr('r', function(d) { return rScale(d.influence || 0); })
    .attr('fill', function(d) { return THREAD_COLORS[d.thread] || '#555'; })
    .attr('stroke', function(d) { return THREAD_COLORS[d.thread] || '#555'; })
    .attr('stroke-width', 0.5)
    .attr('opacity', 0.65);

  // Events
  node.on('click', function(ev, d) {
    if (d.isFork) return;
    var t = DATA.topics[d.id];
    if (t) showDetail(t);
  });

  node.on('mouseover', function(ev, d) {
    if (d.isFork) return;
    var t = DATA.topics[d.id];
    if (t) showTooltip(ev, t);

    // Highlight connections
    var connected = new Set();
    links.forEach(function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      if (sid === d.id) connected.add(tid);
      if (tid === d.id) connected.add(sid);
    });
    connected.add(d.id);

    node.selectAll('circle').attr('opacity', function(n) {
      return connected.has(n.id) ? 1 : 0.08;
    });
    link.attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (connected.has(sid) && connected.has(tid)) ? 0.6 : 0.02;
    });
  });

  node.on('mouseout', function() {
    hideTooltip();
    // Restore to filter state
    filterNetwork();
  });

  simulation.on('tick', function() {
    link.attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
    node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
  });
}

function filterNetwork() {
  var hasFilter = activeThread || activeAuthor;

  d3.selectAll('.net-node circle').attr('opacity', function(d) {
    var t = DATA.topics[d.id];
    if (!t) return 0.7;
    if (hasFilter) {
      if (activeThread && t.th !== activeThread) return 0.05;
      if (activeAuthor && t.a !== activeAuthor) return 0.05;
      return 0.85;
    }
    return 0.7;
  });

  d3.selectAll('.net-link').attr('stroke-opacity', function() {
    return hasFilter ? 0.04 : 0.12;
  });
}

// === DETAIL PANEL ===
function showDetail(t) {
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');

  // EIP tags — distinguish primary (topic is about this EIP) from mentions
  var primarySet = new Set(t.peips || []);

  var thread = t.th ? DATA.threads[t.th] : null;
  var threadName = thread ? thread.n : 'Unassigned';
  var threadColor = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';

  // Build refs HTML
  var outRefs = '';
  if (t.out && t.out.length > 0) {
    outRefs = t.out.slice(0, 10).map(function(id) {
      var ref = DATA.topics[id];
      if (!ref) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + id + '])">' +
             escHtml(ref.t) + '</a></div>';
    }).join('');
  }

  var incRefs = '';
  if (t.inc && t.inc.length > 0) {
    incRefs = t.inc.slice(0, 10).map(function(id) {
      var ref = DATA.topics[id];
      if (!ref) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + id + '])">' +
             escHtml(ref.t) + '</a></div>';
    }).join('');
  }

  content.innerHTML =
    '<h2>' + escHtml(t.t) + '</h2>' +
    '<div class="meta">by <strong>' + escHtml(t.a) + '</strong> \u00b7 ' + t.d +
    ' \u00b7 <a href="https://ethresear.ch/t/' + t.id + '" target="_blank">Open on ethresear.ch \u2192</a></div>' +
    '<div class="detail-stat"><span class="label">Thread</span><span class="value" style="color:' + threadColor + '">' + threadName + '</span></div>' +
    '<div class="detail-stat"><span class="label">Influence</span><span class="value">' + t.inf.toFixed(3) + '</span></div>' +
    '<div class="detail-stat"><span class="label">Views</span><span class="value">' + t.vw.toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Likes</span><span class="value">' + t.lk + '</span></div>' +
    '<div class="detail-stat"><span class="label">Posts</span><span class="value">' + t.pc + '</span></div>' +
    '<div class="detail-stat"><span class="label">Cited by</span><span class="value">' + t.ind + ' topics</span></div>' +
    '<div class="detail-stat"><span class="label">Category</span><span class="value">' + escHtml(t.cat) + '</span></div>' +
    (t.exc ? '<div class="detail-excerpt">' + escHtml(t.exc) + '</div>' : '') +
    (t.peips && t.peips.length > 0 ? '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIPs discussed:</strong> ' +
      t.peips.map(function(e) { return '<span class="eip-tag primary">EIP-' + e + '</span>'; }).join(' ') + '</div>' : '') +
    (t.eips && t.eips.length > (t.peips||[]).length ?
      '<div style="margin:4px 0"><strong style="font-size:11px;color:#666">Also mentions:</strong> ' +
      (t.eips || []).filter(function(e) { return !primarySet.has(e); }).map(function(e) {
        return '<span class="eip-tag">EIP-' + e + '</span>';
      }).join(' ') + '</div>' : '') +
    (outRefs ? '<div class="detail-refs"><h4>References (' + t.out.length + ')</h4>' + outRefs + '</div>' : '') +
    (incRefs ? '<div class="detail-refs"><h4>Cited by (' + t.inc.length + ')</h4>' + incRefs + '</div>' : '');

  panel.classList.add('open');
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('open');
}

// === TOOLTIP ===
function showTooltip(ev, t) {
  var tip = document.getElementById('tooltip');
  var primary = (t.peips && t.peips.length > 0) ? ' [EIP-' + t.peips.join(', EIP-') + ']' : '';
  tip.innerHTML = '<strong>' + escHtml(t.t) + '</strong><br>' +
                  escHtml(t.a) + ' \u00b7 ' + t.d + ' \u00b7 inf: ' + t.inf.toFixed(2) +
                  primary;
  tip.style.display = 'block';

  // Position near cursor, fixed to viewport
  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  // Keep on screen
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

// === UTILS ===
function hashCode(n) {
  return ((n * 2654435761) >>> 0) % 10000;
}

function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
}
"""


if __name__ == "__main__":
    main()
