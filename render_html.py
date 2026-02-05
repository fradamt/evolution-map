#!/usr/bin/env python3
"""Render analysis.json -> evolution-map.html (interactive visualization).

Generates a single self-contained HTML file with D3.js v7 (from CDN).
Five panels: Timeline Swim Lanes, Citation Network, Co-Author Network,
Author Sidebar, Detail Panel.

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
            "tg": t.get("tags", [])[:5],
            "exc": t.get("first_post_excerpt", "")[:300],
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
            "qc": th.get("quarterly_counts", []),
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
      <button id="btn-coauthor" onclick="showView('coauthor')">Authors</button>
    </div>
  </header>
  <div id="main-area">
    <div id="timeline-view"></div>
    <div id="network-view"></div>
    <div id="coauthor-view"></div>
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
      <div class="sidebar-collapse-hdr" onclick="toggleCollapse('cat')">
        <span class="toggle-arrow" id="cat-arrow">&#9656;</span>
        <h3>Categories</h3>
      </div>
      <div class="sidebar-collapse-body" id="cat-body">
        <div id="cat-chips" class="cat-chips"></div>
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-collapse-hdr" onclick="toggleCollapse('tag')">
        <span class="toggle-arrow" id="tag-arrow">&#9656;</span>
        <h3>Tags</h3>
      </div>
      <div class="sidebar-collapse-body" id="tag-body">
        <div id="tag-chips" class="tag-chips"></div>
      </div>
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

#timeline-view, #network-view, #coauthor-view { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
#timeline-view { display: block; }
#network-view { display: none; }
#coauthor-view { display: none; }

/* Timeline */
.timeline-container { width: 100%; height: 100%; overflow: hidden; }
.fork-line { stroke: #444; stroke-width: 1; stroke-dasharray: 4,4; }
.fork-label { fill: #666; font-size: 10px; font-weight: 500; }
.era-bg { opacity: 0.03; }
.histogram-bar { fill: rgba(255,255,255,0.13); }
.histogram-bar:hover { fill: rgba(255,255,255,0.25); }

/* CRITICAL: pointer-events:all so circles with transparent fill are still hoverable */
.topic-circle { cursor: pointer; pointer-events: all; }
.edge-line { stroke: #556; }

/* Arrow markers (default barely visible, highlighted more visible) */
.arrow-default { fill: #556; }
.arrow-highlight { fill: #88aaff; }
.arrow-lineage { fill: #88aaff; }
.arrow-net-default { fill: #334; }
.arrow-net-highlight { fill: #88aaff; }

/* Network */
.net-node { cursor: pointer; }
.net-link { stroke: #334; }
.fork-diamond { fill: #ffcc00; stroke: #aa8800; stroke-width: 1.5; cursor: pointer; }

/* Co-Author Network */
.coauthor-node { cursor: pointer; }
.coauthor-link { stroke: #445566; }
.coauthor-label { fill: #ccc; font-size: 11px; font-weight: 500; pointer-events: none;
                  text-anchor: middle; dominant-baseline: central; text-shadow: 0 1px 3px #000, 0 0 6px #000; }
.coauthor-label-hover { fill: #fff; font-size: 10px; font-weight: 400; pointer-events: none;
                        text-anchor: middle; dominant-baseline: central; text-shadow: 0 1px 3px #000, 0 0 6px #000; }

/* Sidebar */
.sidebar-section { padding: 12px 14px; border-bottom: 1px solid #1e1e2e; }
.sidebar-section h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
                      color: #666; margin-bottom: 8px; }
.thread-legend { display: flex; flex-direction: column; gap: 3px; }
.thread-chip { font-size: 10px; padding: 2px 6px; border-radius: 3px; cursor: pointer;
               opacity: 0.7; transition: opacity 0.15s; white-space: nowrap;
               display: flex; align-items: center; gap: 6px; }
.thread-chip:hover, .thread-chip.active { opacity: 1; }
.thread-chip .thread-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.thread-chip .thread-count { font-size: 9px; opacity: 0.6; flex-shrink: 0; }
.thread-chip .sparkline-wrap { flex-shrink: 0; position: relative; }
.thread-chip .sparkline-wrap svg { display: block; }
.author-item { padding: 6px 0; cursor: pointer; display: flex; align-items: center; gap: 8px; }
.author-item:hover { background: #1a1a2a; }
.author-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.author-name { font-size: 12px; flex: 1; min-width: 0; overflow: hidden;
               text-overflow: ellipsis; white-space: nowrap; }
.author-count { font-size: 10px; color: #666; flex-shrink: 0; }
.author-item.active .author-name { color: #fff; font-weight: 600; }

/* Collapsible sidebar sections */
.sidebar-collapse-hdr { display: flex; align-items: center; cursor: pointer;
                        user-select: none; gap: 6px; }
.sidebar-collapse-hdr h3 { margin-bottom: 0; }
.sidebar-collapse-hdr .toggle-arrow { font-size: 10px; color: #666; transition: transform 0.15s; }
.sidebar-collapse-hdr .toggle-arrow.open { transform: rotate(90deg); }
.sidebar-collapse-body { overflow: hidden; max-height: 0; transition: max-height 0.25s ease; }
.sidebar-collapse-body.open { max-height: 600px; }

/* Category chips */
.cat-chips { display: flex; flex-wrap: wrap; gap: 4px; padding-top: 8px; }
.cat-chip { font-size: 10px; padding: 2px 6px; border-radius: 3px; cursor: pointer;
            background: rgba(100,120,160,0.15); color: #8899bb; border: 1px solid rgba(100,120,160,0.25);
            opacity: 0.75; transition: opacity 0.15s, border-color 0.15s, background 0.15s;
            white-space: nowrap; display: inline-flex; align-items: center; gap: 4px; }
.cat-chip:hover { opacity: 1; }
.cat-chip.active { opacity: 1; border-color: #8899cc; background: rgba(100,120,180,0.3); color: #aabbdd; }
.cat-chip .chip-count { font-size: 9px; color: #667; }

/* Tag chips -- smaller and more compact */
.tag-chips { display: flex; flex-wrap: wrap; gap: 3px; padding-top: 8px; }
.tag-chip { font-size: 9px; padding: 1px 5px; border-radius: 3px; cursor: pointer;
            background: rgba(130,130,130,0.1); color: #889; border: 1px solid rgba(130,130,130,0.2);
            opacity: 0.7; transition: opacity 0.15s, border-color 0.15s, background 0.15s;
            white-space: nowrap; display: inline-flex; align-items: center; gap: 3px; }
.tag-chip:hover { opacity: 1; }
.tag-chip.active { opacity: 1; border-color: #99aaaa; background: rgba(130,160,160,0.25); color: #aacccc; }
.tag-chip .chip-count { font-size: 8px; color: #556; }

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

/* Thread bar in author detail */
.thread-bar-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 11px; }
.thread-bar-label { color: #888; width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
.thread-bar-track { flex: 1; height: 6px; background: #1a1a2a; border-radius: 3px; overflow: hidden; }
.thread-bar-fill { height: 100%; border-radius: 3px; }
.thread-bar-pct { color: #666; font-size: 10px; width: 32px; text-align: right; flex-shrink: 0; }

#search-box { width: 100%; padding: 6px 8px; background: #1a1a2a; border: 1px solid #333;
              border-radius: 4px; color: #ccc; font-size: 12px; margin-bottom: 8px; }
#search-box:focus { outline: none; border-color: #555; }

.tooltip { position: fixed; background: #1e1e2e; border: 1px solid #444; border-radius: 4px;
           padding: 8px 12px; font-size: 11px; color: #ccc; pointer-events: none;
           z-index: 500; max-width: 350px; line-height: 1.4; display: none;
           box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
"""


def _build_js():
    # Return JS as a plain string -- no Python f-string interpolation needed
    # (DATA, THREAD_COLORS etc. are injected as separate <script> constants)
    return r"""
// === GLOBALS ===
let activeView = 'timeline';
let activeThread = null;
let activeAuthor = null;
let activeCategory = null;
let activeTag = null;
let simulation = null;
let coAuthorSimulation = null;
let hoveredTopicId = null;
let pinnedTopicId = null;
let lineageActive = false;
let lineageSet = new Set();
let lineageEdgeSet = new Set(); // "src-tgt" strings for fast edge lookup

// Build index: topic_id -> set of connected topic_ids (for edge highlighting)
const topicEdgeIndex = {};
DATA.graph.edges.forEach(e => {
  const s = String(e.source), t = String(e.target);
  if (!topicEdgeIndex[s]) topicEdgeIndex[s] = new Set();
  if (!topicEdgeIndex[t]) topicEdgeIndex[t] = new Set();
  topicEdgeIndex[s].add(Number(e.target));
  topicEdgeIndex[t].add(Number(e.source));
});

// Build co-author edge index: author_id -> set of connected author_ids
const coAuthorEdgeIndex = {};
(DATA.coGraph.edges || []).forEach(e => {
  if (!coAuthorEdgeIndex[e.source]) coAuthorEdgeIndex[e.source] = new Set();
  if (!coAuthorEdgeIndex[e.target]) coAuthorEdgeIndex[e.target] = new Set();
  coAuthorEdgeIndex[e.source].add(e.target);
  coAuthorEdgeIndex[e.target].add(e.source);
});

// Author color map
const authorList = Object.values(DATA.authors).sort((a,b) => b.inf - a.inf);
const authorColorMap = {};
authorList.forEach((a, i) => { authorColorMap[a.u] = i < 15 ? AUTHOR_COLORS[i] : '#555'; });

// Top 15 authors by influence (for persistent labels in co-author network)
const top15Authors = new Set(authorList.slice(0, 15).map(a => a.u));

// === INIT ===
document.addEventListener('DOMContentLoaded', () => {
  buildSidebar();
  buildTimeline();
  setupSearch();
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeDetail(); clearFilters(); }
  });
  // Apply initial hash state after a short delay to ensure views are ready
  setTimeout(function() { applyHash(); }, 50);
  // Listen for browser back/forward
  window.addEventListener('hashchange', function() {
    applyHash();
  });
});

// === VIEW SWITCHING ===
function showView(view) {
  activeView = view;
  document.getElementById('timeline-view').style.display = view === 'timeline' ? 'block' : 'none';
  document.getElementById('network-view').style.display = view === 'network' ? 'block' : 'none';
  document.getElementById('coauthor-view').style.display = view === 'coauthor' ? 'block' : 'none';
  document.getElementById('btn-timeline').classList.toggle('active', view === 'timeline');
  document.getElementById('btn-network').classList.toggle('active', view === 'network');
  document.getElementById('btn-coauthor').classList.toggle('active', view === 'coauthor');
  if (view === 'network' && !document.querySelector('#network-view svg')) buildNetwork();
  if (view === 'coauthor' && !document.querySelector('#coauthor-view svg')) buildCoAuthorNetwork();
  if (lineageActive) applyLineageHighlight();
  updateHash();
}

// === SIDEBAR ===
function buildSidebar() {
  const legend = document.getElementById('thread-legend');
  THREAD_ORDER.forEach(tid => {
    const th = DATA.threads[tid];
    if (!th) return;
    const color = THREAD_COLORS[tid] || '#555';
    const chip = document.createElement('div');
    chip.className = 'thread-chip';
    chip.style.background = color + '33';
    chip.style.color = color;
    chip.style.border = '1px solid ' + color + '66';
    chip.title = th.n + ' (' + th.tc + ' topics)';
    chip.onclick = () => toggleThread(tid);
    chip.dataset.thread = tid;

    const lbl = document.createElement('span');
    lbl.className = 'thread-label';
    lbl.textContent = th.n.split('&')[0].trim();
    chip.appendChild(lbl);

    const cnt = document.createElement('span');
    cnt.className = 'thread-count';
    cnt.textContent = th.tc;
    chip.appendChild(cnt);

    // Sparkline SVG from quarterly counts
    var qc = th.qc || [];
    if (qc.length > 0) {
      var sparkW = 80, sparkH = 16;
      var maxC = Math.max(1, Math.max.apply(null, qc.map(function(d) { return d.c; })));
      var stepX = sparkW / Math.max(1, qc.length - 1);
      var points = qc.map(function(d, i) {
        var x = i * stepX;
        var y = sparkH - (d.c / maxC) * (sparkH - 2) - 1;
        return x.toFixed(1) + ',' + y.toFixed(1);
      });
      var areaPoints = points.join(' ') + ' ' + sparkW.toFixed(1) + ',' + sparkH + ' 0,' + sparkH;

      var wrap = document.createElement('span');
      wrap.className = 'sparkline-wrap';
      wrap.innerHTML =
        '<svg width="' + sparkW + '" height="' + sparkH + '" viewBox="0 0 ' + sparkW + ' ' + sparkH + '">' +
        '<polygon points="' + areaPoints + '" fill="' + color + '" opacity="0.3"/>' +
        '<polyline points="' + points.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="1" opacity="0.8"/>' +
        '</svg>';

      var svgEl = wrap.querySelector('svg');
      svgEl.style.cursor = 'default';
      svgEl.addEventListener('mousemove', (function(qcData, sw) {
        return function(ev) {
          var rect = ev.currentTarget.getBoundingClientRect();
          var mx = ev.clientX - rect.left;
          var idx = Math.round(mx / sw * (qcData.length - 1));
          idx = Math.max(0, Math.min(qcData.length - 1, idx));
          var d = qcData[idx];
          var tip = document.getElementById('tooltip');
          tip.innerHTML = d.q + ': ' + d.c + ' topic' + (d.c !== 1 ? 's' : '');
          tip.style.display = 'block';
          tip.style.left = (ev.clientX + 10) + 'px';
          tip.style.top = (ev.clientY - 24) + 'px';
          ev.stopPropagation();
        };
      })(qc, sparkW));
      svgEl.addEventListener('mouseleave', function() { hideTooltip(); });
      svgEl.addEventListener('click', function(ev) { ev.stopPropagation(); });

      chip.appendChild(wrap);
    }

    legend.appendChild(chip);
  });

  // --- Category chips ---
  const catCounts = {};
  Object.values(DATA.topics).forEach(t => {
    if (t.cat) catCounts[t.cat] = (catCounts[t.cat] || 0) + 1;
  });
  const topCats = Object.entries(catCounts).sort((a,b) => b[1] - a[1]).slice(0, 10);
  const catContainer = document.getElementById('cat-chips');
  topCats.forEach(([cat, count]) => {
    const chip = document.createElement('span');
    chip.className = 'cat-chip';
    chip.dataset.cat = cat;
    chip.innerHTML = escHtml(cat) + ' <span class="chip-count">' + count + '</span>';
    chip.title = cat + ' (' + count + ' topics)';
    chip.onclick = () => toggleCategory(cat);
    catContainer.appendChild(chip);
  });

  // --- Tag chips ---
  const tagCounts = {};
  Object.values(DATA.topics).forEach(t => {
    (t.tg || []).forEach(tag => { tagCounts[tag] = (tagCounts[tag] || 0) + 1; });
  });
  const topTags = Object.entries(tagCounts).sort((a,b) => b[1] - a[1]).slice(0, 15);
  const tagContainer = document.getElementById('tag-chips');
  topTags.forEach(([tag, count]) => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.dataset.tag = tag;
    chip.innerHTML = escHtml(tag) + ' <span class="chip-count">' + count + '</span>';
    chip.title = tag + ' (' + count + ' topics)';
    chip.onclick = () => toggleTag(tag);
    tagContainer.appendChild(chip);
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
  activeCategory = null;
  activeTag = null;
  lineageActive = false;
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.author-item').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.tag-chip').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  var btn = document.getElementById('lineage-btn');
  if (btn) { btn.textContent = 'Trace Lineage'; btn.style.borderColor = '#5566aa'; btn.style.color = '#8899cc'; }
  applyFilters();
  updateHash();
}

function toggleThread(tid) {
  activeThread = activeThread === tid ? null : tid;
  activeAuthor = null;
  lineageActive = false; lineageSet = new Set(); lineageEdgeSet = new Set();
  document.querySelectorAll('.thread-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.thread === activeThread));
  document.querySelectorAll('.author-item').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function selectThread(tid) {
  activeThread = tid;
  activeAuthor = null;
  lineageActive = false; lineageSet = new Set(); lineageEdgeSet = new Set();
  document.querySelectorAll('.thread-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.thread === activeThread));
  document.querySelectorAll('.author-item').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function toggleAuthor(username) {
  activeAuthor = activeAuthor === username ? null : username;
  activeThread = null;
  lineageActive = false; lineageSet = new Set(); lineageEdgeSet = new Set();
  document.querySelectorAll('.author-item').forEach(c =>
    c.classList.toggle('active', c.dataset.author === activeAuthor));
  document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function selectAuthor(username) {
  activeAuthor = username;
  activeThread = null;
  lineageActive = false; lineageSet = new Set(); lineageEdgeSet = new Set();
  document.querySelectorAll('.author-item').forEach(c =>
    c.classList.toggle('active', c.dataset.author === activeAuthor));
  document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function applyFilters() {
  if (activeView === 'timeline') filterTimeline();
  else if (activeView === 'network') filterNetwork();
  else if (activeView === 'coauthor') filterCoAuthorNetwork();
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
  if (activeView === 'coauthor') {
    // Search authors in co-author view
    var matchingAuthors = new Set();
    (DATA.coGraph.nodes || []).forEach(function(n) {
      if (n.id.toLowerCase().includes(q)) matchingAuthors.add(n.id);
    });
    highlightCoAuthorSet(matchingAuthors);
    return;
  }
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

function highlightCoAuthorSet(ids) {
  d3.selectAll('.coauthor-node circle').attr('opacity', function(d) {
    return ids.has(d.id) ? 1 : 0.06;
  });
  d3.selectAll('.coauthor-link').attr('stroke-opacity', 0.02);
  d3.selectAll('.coauthor-label').attr('opacity', function(d) {
    return ids.has(d.id) ? 1 : 0.1;
  });
  d3.selectAll('.coauthor-label-hover').attr('opacity', function(d) {
    return ids.has(d.id) ? 1 : 0;
  });
}

// === TIMELINE ===
let tlRScale; // shared so search can use it
let tlXScale; // current x scale (updated on zoom)
let tlXScaleOrig; // original x scale (for zoom reset)

function buildTimeline() {
  const container = document.getElementById('timeline-view');
  const width = container.clientWidth || 900;
  const height = container.clientHeight || 700;

  const histH = 24; // histogram height
  const margin = {top: 50, right: 40, bottom: 30 + histH, left: 180};
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const swimH = plotH - histH; // swim lane area above histogram

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
  const laneH = swimH / laneOrder.length;

  // Time scale
  const allDates = Object.values(DATA.topics).map(t => new Date(t.d)).filter(d => !isNaN(d));
  const xDomainOrig = [d3.min(allDates), d3.max(allDates)];
  const xScale = d3.scaleTime()
    .domain(xDomainOrig.slice())
    .range([0, plotW]);

  tlXScale = xScale;
  tlXScaleOrig = xScale.copy();

  // Size scale
  const maxInf = d3.max(Object.values(DATA.topics), t => t.inf) || 1;
  const rScale = d3.scaleSqrt().domain([0, maxInf]).range([2.5, 14]);
  tlRScale = rScale; // expose for search

  // Create SVG (fits the container -- no oversized width)
  const wrapper = document.createElement('div');
  wrapper.className = 'timeline-container';
  container.appendChild(wrapper);

  const svg = d3.select(wrapper).append('svg')
    .attr('width', width)
    .attr('height', height);

  // Clip path so zoomed content doesn't overflow into the label area
  var tlDefs = svg.append('defs');
  tlDefs.append('clipPath').attr('id', 'tl-clip')
    .append('rect').attr('x', 0).attr('y', -margin.top).attr('width', plotW).attr('height', height);

  // Arrow markers for citation edges (default: subtle, highlighted: visible)
  tlDefs.append('marker').attr('id', 'arrow-default')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-default').attr('opacity', 0.3);
  tlDefs.append('marker').attr('id', 'arrow-highlight')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-highlight').attr('opacity', 0.8);
  tlDefs.append('marker').attr('id', 'arrow-lineage')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-lineage').attr('opacity', 0.9);

  // Root group offset by margins
  const root = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

  // Fixed layer for y-axis labels (never affected by zoom)
  const fixedG = root.append('g');

  // Clipped layer for all zoomable content
  const clipG = root.append('g').attr('clip-path', 'url(#tl-clip)');
  const zoomG = clipG.append('g');

  // Era backgrounds
  const eraColors = ['#334', '#343', '#334', '#433', '#343'];
  const eraRects = [];
  const eraTexts = [];
  DATA.eras.forEach((era, i) => {
    const x0 = xScale(new Date(era.start));
    const x1 = xScale(new Date(era.end));
    eraRects.push(
      zoomG.append('rect').attr('class', 'era-bg')
        .attr('x', x0).attr('y', 0).attr('width', x1 - x0).attr('height', swimH)
        .attr('fill', eraColors[i] || '#333')
        .datum({start: new Date(era.start), end: new Date(era.end)})
    );
    eraTexts.push(
      zoomG.append('text').attr('x', (x0 + x1) / 2).attr('y', -8)
        .attr('text-anchor', 'middle').attr('fill', '#555').attr('font-size', 10)
        .text(era.name)
        .datum({start: new Date(era.start), end: new Date(era.end)})
    );
  });

  // Fork lines + labels
  const forkLines = [];
  const forkLabels = [];
  DATA.forks.forEach(f => {
    if (!f.d) return;
    const fd = new Date(f.d);
    const x = xScale(fd);
    forkLines.push(
      zoomG.append('line').attr('class', 'fork-line')
        .attr('x1', x).attr('x2', x).attr('y1', -5).attr('y2', swimH + histH)
        .datum(fd)
    );
    forkLabels.push(
      zoomG.append('text').attr('class', 'fork-label')
        .attr('x', x).attr('y', swimH + histH + 15).attr('text-anchor', 'middle')
        .text(f.cn || f.n)
        .datum(fd)
    );
  });

  // Swim lane labels + separators (labels are fixed; separators are in zoomG)
  const laneIdx = {};
  laneOrder.forEach((tid, i) => {
    laneIdx[tid] = i;
    const y = i * laneH + laneH / 2;
    const name = tid === '_other' ? 'Other' : (DATA.threads[tid] ? DATA.threads[tid].n : tid);
    const color = tid === '_other' ? '#555' : (THREAD_COLORS[tid] || '#555');
    fixedG.append('text').attr('x', -10).attr('y', y)
      .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
      .attr('fill', color).attr('font-size', 11).attr('font-weight', 500)
      .text(name.length > 22 ? name.slice(0, 20) + '\u2026' : name);
    if (i > 0) {
      fixedG.append('line').attr('x1', 0).attr('x2', plotW)
        .attr('y1', i * laneH).attr('y2', i * laneH)
        .attr('stroke', '#1a1a2a').attr('stroke-width', 0.5);
    }
  });

  // Pre-compute fixed y positions for topics (y is stable across zoom)
  Object.values(DATA.topics).forEach(t => {
    const th = (t.th && laneIdx[t.th] !== undefined) ? t.th : '_other';
    const lane = laneIdx[th];
    const yBase = lane * laneH + laneH * 0.12;
    const yRange = laneH * 0.76;
    t._yPos = yBase + (hashCode(t.id) % 100) / 100 * yRange;
    t._date = new Date(t.d);
  });

  // Draw edges (below circles)
  const edgeG = zoomG.append('g');
  DATA.graph.edges.forEach(e => {
    const sT = DATA.topics[e.source];
    const tT = DATA.topics[e.target];
    if (sT && tT && sT._yPos !== undefined && tT._yPos !== undefined) {
      edgeG.append('line').attr('class', 'edge-line')
        .attr('x1', xScale(sT._date)).attr('y1', sT._yPos)
        .attr('x2', xScale(tT._date)).attr('y2', tT._yPos)
        .attr('stroke-opacity', 0.06)
        .attr('marker-end', 'url(#arrow-default)')
        .datum({source: e.source, target: e.target, sd: sT._date, td: tT._date, sy: sT._yPos, ty: tT._yPos});
    }
  });

  // Draw topic circles
  const circleG = zoomG.append('g');
  Object.values(DATA.topics).forEach(t => {
    if (t._yPos === undefined) return;
    const color = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';

    circleG.append('circle')
      .attr('class', 'topic-circle')
      .attr('cx', xScale(t._date)).attr('cy', t._yPos)
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

  // --- Monthly activity histogram ---
  var monthBins = {};
  Object.values(DATA.topics).forEach(function(t) {
    var d = t._date;
    if (!d || isNaN(d)) return;
    var key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
    if (!monthBins[key]) monthBins[key] = {date: new Date(d.getFullYear(), d.getMonth(), 1), count: 0};
    monthBins[key].count++;
  });
  var histData = Object.values(monthBins).sort(function(a, b) { return a.date - b.date; });
  var maxCount = d3.max(histData, function(d) { return d.count; }) || 1;
  var histYScale = d3.scaleLinear().domain([0, maxCount]).range([0, histH - 2]);

  // Compute bar width: ~30 days in the time scale
  var barWidthBase = Math.max(1, xScale(new Date(2020, 1, 1)) - xScale(new Date(2020, 0, 1)));

  var histG = zoomG.append('g').attr('class', 'histogram-g')
    .attr('transform', 'translate(0,' + swimH + ')');

  histG.selectAll('.histogram-bar')
    .data(histData)
    .join('rect')
    .attr('class', 'histogram-bar')
    .attr('x', function(d) { return xScale(d.date); })
    .attr('y', function(d) { return histH - histYScale(d.count); })
    .attr('width', Math.max(1, barWidthBase * 0.85))
    .attr('height', function(d) { return histYScale(d.count); })
    .attr('rx', 1)
    .on('mouseover', function(ev, d) {
      var tip = document.getElementById('tooltip');
      var mn = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      tip.innerHTML = mn[d.date.getMonth()] + ' ' + d.date.getFullYear() + ': ' + d.count + ' topic' + (d.count !== 1 ? 's' : '');
      tip.style.display = 'block';
      tip.style.left = (ev.clientX + 10) + 'px';
      tip.style.top = (ev.clientY - 24) + 'px';
    })
    .on('mouseout', function() { hideTooltip(); });

  // X axis (below histogram + swimlanes)
  var xAxisG = root.append('g')
    .attr('class', 'x-axis')
    .attr('transform', 'translate(0,' + (swimH + histH) + ')');
  var xAxisFn = d3.axisBottom(xScale).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
  xAxisG.call(xAxisFn);
  xAxisG.selectAll('text').attr('fill', '#666').attr('font-size', 10);
  xAxisG.selectAll('.domain, .tick line').attr('stroke', '#333');

  // === D3 ZOOM (horizontal only) ===
  // Strategy: ctrl+wheel / pinch = zoom, plain wheel / trackpad = horizontal pan,
  // drag = pan, double-click = reset.
  var zoom = d3.zoom()
    .scaleExtent([0.5, 8])
    .translateExtent([[0, 0], [plotW, height]])
    .extent([[0, 0], [plotW, height]])
    .filter(function(ev) {
      // For wheel events: only let D3 zoom handle ctrl+wheel (pinch-to-zoom).
      // Plain wheel / shift+wheel are handled by our custom handler below.
      if (ev.type === 'wheel') return ev.ctrlKey || ev.metaKey;
      // Block double-click (handled separately below)
      if (ev.type === 'dblclick') return false;
      // Allow drag (button 0) and touch events
      return !ev.button;
    })
    .on('zoom', onZoom);

  svg.call(zoom);

  // Custom wheel handler: translate scroll delta into horizontal pan.
  // This runs for plain wheel events (no ctrl/meta) that D3 zoom ignores.
  svg.on('wheel.pan', function(ev) {
    if (ev.ctrlKey || ev.metaKey) return; // let D3 zoom handle pinch/ctrl+wheel
    ev.preventDefault();
    // Use deltaX for horizontal scroll (trackpad swipe) and deltaY for vertical
    // scroll wheel — both map to horizontal pan on the timeline.
    var dx = ev.deltaX !== 0 ? ev.deltaX : ev.deltaY;
    // Get current transform and shift it horizontally
    var cur = d3.zoomTransform(svg.node());
    var newT = cur.translate(-dx, 0);
    svg.call(zoom.transform, newT);
  }, {passive: false});

  // Double-click to reset zoom
  svg.on('dblclick.zoom', function() {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
  });

  function onZoom(ev) {
    // Rescale x only (horizontal pan/zoom; y stays fixed)
    var t = ev.transform;
    var newX = t.rescaleX(tlXScaleOrig);
    tlXScale = newX;

    // Update topic circles (only cx changes)
    d3.selectAll('.topic-circle').attr('cx', function(d) { return newX(d._date); });

    // Update edges
    d3.selectAll('.edge-line')
      .attr('x1', function(d) { return newX(d.sd); })
      .attr('x2', function(d) { return newX(d.td); });

    // Update era backgrounds
    eraRects.forEach(function(r) {
      var d = r.datum();
      r.attr('x', newX(d.start)).attr('width', Math.max(0, newX(d.end) - newX(d.start)));
    });
    eraTexts.forEach(function(txt) {
      var d = txt.datum();
      txt.attr('x', (newX(d.start) + newX(d.end)) / 2);
    });

    // Update fork lines + labels
    forkLines.forEach(function(l) { var d = l.datum(); l.attr('x1', newX(d)).attr('x2', newX(d)); });
    forkLabels.forEach(function(l) { var d = l.datum(); l.attr('x', newX(d)); });

    // Update histogram bars
    var zoomedBarW = Math.max(1, (newX(new Date(2020, 1, 1)) - newX(new Date(2020, 0, 1))) * 0.85);
    d3.selectAll('.histogram-bar')
      .attr('x', function(d) { return newX(d.date); })
      .attr('width', zoomedBarW);

    // Update x-axis with adaptive tick density
    var axisFn;
    if (t.k > 4) {
      axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(1)).tickFormat(d3.timeFormat('%b %Y'));
    } else if (t.k > 2) {
      axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat('%b %Y'));
    } else {
      axisFn = d3.axisBottom(newX).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
    }
    xAxisG.call(axisFn);
    xAxisG.selectAll('text').attr('fill', '#666').attr('font-size', 10);
    xAxisG.selectAll('.domain, .tick line').attr('stroke', '#333');
  }
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
        if (activeCategory && t.cat !== activeCategory) return 0.03;
        if (activeTag && !(t.tg || []).includes(activeTag)) return 0.03;
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
      })
      .attr('marker-end', function(e) {
        if (e.source === d.id || e.target === d.id) return 'url(#arrow-highlight)';
        return 'url(#arrow-default)';
      });
  } else {
    hoveredTopicId = null;
    hideTooltip();
    if (pinnedTopicId) {
      applyPinnedHighlightTimeline();
    } else {
      filterTimeline();
    }
  }
}

function topicMatchesFilter(t) {
  if (activeThread && t.th !== activeThread) return false;
  if (activeAuthor && t.a !== activeAuthor) return false;
  if (activeCategory && t.cat !== activeCategory) return false;
  if (activeTag && !(t.tg || []).includes(activeTag)) return false;
  return true;
}

// === PINNED TOPIC HIGHLIGHTING ===
function applyPinnedHighlight() {
  if (!pinnedTopicId) return;
  if (activeView === 'timeline') applyPinnedHighlightTimeline();
  else if (activeView === 'network') applyPinnedHighlightNetwork();
}

function applyPinnedHighlightTimeline() {
  if (!pinnedTopicId) return;
  var connected = topicEdgeIndex[String(pinnedTopicId)] || new Set();
  d3.selectAll('.topic-circle')
    .attr('opacity', function(t) {
      if (t.id === pinnedTopicId) return 1;
      if (connected.has(t.id)) return 0.8;
      if (!topicMatchesFilter(t)) return 0.03;
      return 0.12;
    });
  d3.selectAll('.edge-line')
    .attr('stroke-opacity', function(e) {
      if (e.source === pinnedTopicId || e.target === pinnedTopicId) return 0.5;
      return 0.02;
    })
    .attr('stroke', function(e) {
      if (e.source === pinnedTopicId || e.target === pinnedTopicId) return '#88aaff';
      return '#556';
    })
    .attr('marker-end', function(e) {
      if (e.source === pinnedTopicId || e.target === pinnedTopicId) return 'url(#arrow-highlight)';
      return 'url(#arrow-default)';
    });
}

function applyPinnedHighlightNetwork() {
  if (!pinnedTopicId) return;
  var connected = topicEdgeIndex[String(pinnedTopicId)] || new Set();
  connected = new Set(connected);
  connected.add(pinnedTopicId);

  d3.selectAll('.net-node circle').attr('opacity', function(n) {
    return connected.has(n.id) ? 1 : 0.08;
  });
  d3.selectAll('.net-link').attr('stroke-opacity', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === pinnedTopicId || tid === pinnedTopicId) ? 0.6 : 0.02;
  }).attr('marker-end', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === pinnedTopicId || tid === pinnedTopicId) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
  });
}

function highlightTopicInView(topicId) {
  // Temporarily highlight a topic (for reference link hover)
  if (activeView === 'timeline') {
    var connected = topicEdgeIndex[String(topicId)] || new Set();
    d3.selectAll('.topic-circle')
      .attr('opacity', function(t) {
        if (t.id === topicId) return 1;
        if (t.id === pinnedTopicId) return 0.7;
        if (connected.has(t.id)) return 0.8;
        if (!topicMatchesFilter(t)) return 0.03;
        return 0.12;
      })
      .attr('stroke-width', function(t) { return t.id === topicId ? 2.5 : 0.5; });
    d3.selectAll('.edge-line')
      .attr('stroke-opacity', function(e) {
        if (e.source === topicId || e.target === topicId) return 0.5;
        if (e.source === pinnedTopicId || e.target === pinnedTopicId) return 0.25;
        return 0.02;
      })
      .attr('stroke', function(e) {
        if (e.source === topicId || e.target === topicId) return '#ffaa44';
        if (e.source === pinnedTopicId || e.target === pinnedTopicId) return '#88aaff';
        return '#556';
      })
      .attr('marker-end', function(e) {
        if (e.source === topicId || e.target === topicId) return 'url(#arrow-highlight)';
        if (e.source === pinnedTopicId || e.target === pinnedTopicId) return 'url(#arrow-highlight)';
        return 'url(#arrow-default)';
      });
  } else if (activeView === 'network') {
    var connected = topicEdgeIndex[String(topicId)] || new Set();
    var connSet = new Set(connected);
    connSet.add(topicId);
    d3.selectAll('.net-node circle')
      .attr('opacity', function(n) { return connSet.has(n.id) ? 1 : (n.id === pinnedTopicId ? 0.7 : 0.08); })
      .attr('stroke-width', function(n) { return n.id === topicId ? 2.5 : 0.5; });
    d3.selectAll('.net-link').attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === topicId || tid === topicId) ? 0.6 : 0.02;
    }).attr('marker-end', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === topicId || tid === topicId) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
    });
  }
}

function restorePinnedHighlight() {
  // Revert stroke-width and restore pinned or filter state
  d3.selectAll('.topic-circle').attr('stroke-width', 0.5);
  d3.selectAll('.net-node circle').attr('stroke-width', 0.5);
  if (pinnedTopicId) {
    applyPinnedHighlight();
  } else {
    applyFilters();
  }
}

function filterTimeline() {
  if (lineageActive) { applyLineageTimeline(); return; }
  const hasFilter = activeThread || activeAuthor || activeCategory || activeTag;

  d3.selectAll('.topic-circle')
    .attr('opacity', function(d) {
      if (hasFilter) {
        return topicMatchesFilter(d) ? 0.85 : 0.04;
      }
      return 0.7;
    })
    .attr('r', function(d) { return tlRScale(d.inf); });

  d3.selectAll('.edge-line')
    .attr('stroke', '#556')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', function(e) {
      if (!hasFilter) return 0.06;
      const sT = DATA.topics[e.source];
      const tT = DATA.topics[e.target];
      if (sT && tT && topicMatchesFilter(sT) && topicMatchesFilter(tT)) return 0.25;
      return 0.01;
    })
    .attr('marker-end', 'url(#arrow-default)');
}

// === NETWORK ===
function buildNetwork() {
  const container = document.getElementById('network-view');
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  // Arrow markers for network edges
  var netDefs = svg.append('defs');
  netDefs.append('marker').attr('id', 'net-arrow-default')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-net-default').attr('opacity', 0.25);
  netDefs.append('marker').attr('id', 'net-arrow-highlight')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-net-highlight').attr('opacity', 0.8);

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
    .attr('stroke-opacity', 0.12)
    .attr('marker-end', 'url(#net-arrow-default)');

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
    }).attr('marker-end', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (connected.has(sid) && connected.has(tid)) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
    });
  });

  node.on('mouseout', function() {
    hideTooltip();
    if (pinnedTopicId) {
      applyPinnedHighlightNetwork();
    } else {
      filterNetwork();
    }
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
  if (lineageActive) { applyLineageNetwork(); return; }
  var hasFilter = activeThread || activeAuthor || activeCategory || activeTag;

  d3.selectAll('.net-node circle').attr('opacity', function(d) {
    var t = DATA.topics[d.id];
    if (!t) return 0.7;
    if (hasFilter) {
      return topicMatchesFilter(t) ? 0.85 : 0.05;
    }
    return 0.7;
  });

  d3.selectAll('.net-link')
    .attr('stroke', '#334')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', function() {
      return hasFilter ? 0.04 : 0.12;
    })
    .attr('marker-end', 'url(#net-arrow-default)');
}

// === CO-AUTHOR NETWORK ===
function buildCoAuthorNetwork() {
  var container = document.getElementById('coauthor-view');
  var width = container.clientWidth || 800;
  var height = container.clientHeight || 600;

  var svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  var g = svg.append('g');

  // Zoom
  svg.call(d3.zoom().scaleExtent([0.3, 5]).on('zoom', function(ev) {
    g.attr('transform', ev.transform);
  }));

  // Prepare co-author data
  var coNodes = (DATA.coGraph.nodes || []).map(function(n) { return Object.assign({}, n); });
  var coNodeMap = {};
  coNodes.forEach(function(n) { coNodeMap[n.id] = n; });

  var coLinks = (DATA.coGraph.edges || [])
    .filter(function(e) { return coNodeMap[e.source] && coNodeMap[e.target]; })
    .map(function(e) { return {source: e.source, target: e.target, weight: e.weight || 1}; });

  // Scales
  var maxInf = d3.max(coNodes, function(n) { return n.inf || 0; }) || 1;
  var rScale = d3.scaleSqrt().domain([0, maxInf]).range([5, 28]);

  var maxWeight = d3.max(coLinks, function(e) { return e.weight; }) || 1;
  var linkWidthScale = d3.scaleLinear().domain([1, maxWeight]).range([0.5, 4]);

  // Determine dominant thread color for each author node
  function getAuthorColor(n) {
    // Use the author color map if available (top 15 get unique colors)
    if (authorColorMap[n.id] && authorColorMap[n.id] !== '#555') return authorColorMap[n.id];
    // Otherwise, color by dominant thread
    var thrs = n.thrs || (DATA.authors[n.id] ? DATA.authors[n.id].ths : null);
    if (thrs) {
      var bestThread = null;
      var bestCount = 0;
      for (var tid in thrs) {
        if (thrs[tid] > bestCount) { bestCount = thrs[tid]; bestThread = tid; }
      }
      if (bestThread && THREAD_COLORS[bestThread]) return THREAD_COLORS[bestThread];
    }
    return '#667';
  }

  // Force simulation
  coAuthorSimulation = d3.forceSimulation(coNodes)
    .force('link', d3.forceLink(coLinks).id(function(d) { return d.id; })
      .distance(function(d) { return Math.max(40, 150 - d.weight * 10); })
      .strength(function(d) { return 0.1 + (d.weight / maxWeight) * 0.3; }))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(function(d) {
      return rScale(d.inf || 0) + 4;
    }));

  // Draw links
  var link = g.append('g').selectAll('line')
    .data(coLinks).join('line')
    .attr('class', 'coauthor-link')
    .attr('stroke-width', function(d) { return linkWidthScale(d.weight); })
    .attr('stroke-opacity', 0.2);

  // Draw nodes
  var node = g.append('g').selectAll('g')
    .data(coNodes).join('g')
    .attr('class', 'coauthor-node')
    .call(d3.drag()
      .on('start', function(ev, d) {
        if (!ev.active) coAuthorSimulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', function(ev, d) { d.fx = ev.x; d.fy = ev.y; })
      .on('end', function(ev, d) {
        if (!ev.active) coAuthorSimulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      })
    );

  // Author circles
  node.append('circle')
    .attr('r', function(d) { return rScale(d.inf || 0); })
    .attr('fill', function(d) { return getAuthorColor(d); })
    .attr('stroke', function(d) { return getAuthorColor(d); })
    .attr('stroke-width', 1)
    .attr('opacity', 0.7);

  // Persistent labels for top 15 by influence
  node.filter(function(d) { return top15Authors.has(d.id); })
    .append('text')
    .attr('class', 'coauthor-label')
    .attr('dy', function(d) { return rScale(d.inf || 0) + 12; })
    .text(function(d) { return d.id; });

  // Hover labels for all others (hidden by default)
  node.filter(function(d) { return !top15Authors.has(d.id); })
    .append('text')
    .attr('class', 'coauthor-label-hover')
    .attr('dy', function(d) { return rScale(d.inf || 0) + 10; })
    .attr('opacity', 0)
    .text(function(d) { return d.id; });

  // Click -> show author detail
  node.on('click', function(ev, d) {
    showAuthorDetail(d.id);
  });

  // Hover -> tooltip + highlight connections
  node.on('mouseover', function(ev, d) {
    showCoAuthorTooltip(ev, d);

    // Show hover label for this node
    d3.select(this).select('.coauthor-label-hover').attr('opacity', 1);

    // Highlight connections
    var connected = coAuthorEdgeIndex[d.id] || new Set();
    var connectedWithSelf = new Set(connected);
    connectedWithSelf.add(d.id);

    node.selectAll('circle').attr('opacity', function(n) {
      return connectedWithSelf.has(n.id) ? 1 : 0.08;
    });
    node.selectAll('.coauthor-label').attr('opacity', function(n) {
      return connectedWithSelf.has(n.id) ? 1 : 0.1;
    });
    // Show hover labels for connected nodes too
    node.selectAll('.coauthor-label-hover').attr('opacity', function(n) {
      return connected.has(n.id) ? 1 : (n.id === d.id ? 1 : 0);
    });
    link.attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? 0.7 : 0.02;
    }).attr('stroke', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? '#88aaff' : '#445566';
    });
  });

  node.on('mouseout', function() {
    hideTooltip();
    filterCoAuthorNetwork();
  });

  // Tick
  coAuthorSimulation.on('tick', function() {
    link.attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
    node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
  });
}

function filterCoAuthorNetwork() {
  var hasFilter = activeAuthor;

  d3.selectAll('.coauthor-node circle').attr('opacity', function(d) {
    if (hasFilter) {
      if (d.id === activeAuthor) return 1;
      var connected = coAuthorEdgeIndex[activeAuthor] || new Set();
      if (connected.has(d.id)) return 0.8;
      return 0.06;
    }
    return 0.7;
  });

  d3.selectAll('.coauthor-label').attr('opacity', function(d) {
    if (hasFilter) {
      if (d.id === activeAuthor) return 1;
      var connected = coAuthorEdgeIndex[activeAuthor] || new Set();
      if (connected.has(d.id)) return 1;
      return 0.1;
    }
    return 1;
  });

  d3.selectAll('.coauthor-label-hover').attr('opacity', function(d) {
    if (hasFilter) {
      var connected = coAuthorEdgeIndex[activeAuthor] || new Set();
      return connected.has(d.id) ? 1 : 0;
    }
    return 0;
  });

  d3.selectAll('.coauthor-link')
    .attr('stroke', '#445566')
    .attr('stroke-opacity', function(l) {
      if (!hasFilter) return 0.2;
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === activeAuthor || tid === activeAuthor) ? 0.6 : 0.02;
    });
}

function showCoAuthorTooltip(ev, d) {
  var tip = document.getElementById('tooltip');
  var a = DATA.authors[d.id];
  var topThread = '';
  if (d.thrs || (a && a.ths)) {
    var thrs = d.thrs || a.ths;
    var bestThread = null, bestCount = 0;
    for (var tid in thrs) {
      if (thrs[tid] > bestCount) { bestCount = thrs[tid]; bestThread = tid; }
    }
    if (bestThread && DATA.threads[bestThread]) {
      topThread = '<br>Top thread: <span style="color:' + (THREAD_COLORS[bestThread] || '#888') + '">' +
                  DATA.threads[bestThread].n + '</span>';
    }
  }
  tip.innerHTML = '<strong>' + escHtml(d.id) + '</strong><br>' +
    'Topics: ' + (d.tc || (a ? a.tc : '?')) +
    ' &middot; Influence: ' + ((d.inf || (a ? a.inf : 0)).toFixed(2)) +
    topThread;
  tip.style.display = 'block';

  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

// === AUTHOR DETAIL PANEL ===
function showAuthorDetail(username) {
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var a = DATA.authors[username];
  if (!a) return;

  var color = authorColorMap[username] || '#667';

  // Thread distribution bars
  var thrs = a.ths || {};
  var thrEntries = Object.entries(thrs).sort(function(a,b) { return b[1] - a[1]; });
  var thrTotal = thrEntries.reduce(function(sum, e) { return sum + e[1]; }, 0) || 1;
  var threadBarsHtml = thrEntries.slice(0, 6).map(function(entry) {
    var tid = entry[0], count = entry[1];
    var pct = Math.round(count / thrTotal * 100);
    var tColor = THREAD_COLORS[tid] || '#555';
    var tName = DATA.threads[tid] ? DATA.threads[tid].n : tid;
    return '<div class="thread-bar-row">' +
      '<span class="thread-bar-label" style="color:' + tColor + '">' + escHtml(tName) + '</span>' +
      '<span class="thread-bar-track"><span class="thread-bar-fill" style="width:' + pct + '%;background:' + tColor + '"></span></span>' +
      '<span class="thread-bar-pct">' + pct + '%</span></div>';
  }).join('');

  // Top topics
  var topTopicsHtml = '';
  if (a.tops && a.tops.length > 0) {
    topTopicsHtml = a.tops.map(function(tid) {
      var topic = DATA.topics[tid];
      if (!topic) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + tid + '])" ' +
        'onmouseenter="highlightTopicInView(' + tid + ')" ' +
        'onmouseleave="restorePinnedHighlight()">' +
        escHtml(topic.t) + '</a> <span style="color:#666;font-size:10px">(' + topic.inf.toFixed(2) + ')</span></div>';
    }).join('');
  }

  // Co-researchers
  var coHtml = '';
  if (a.co && Object.keys(a.co).length > 0) {
    coHtml = Object.entries(a.co).map(function(entry) {
      var coName = entry[0], coCount = entry[1];
      var coColor = authorColorMap[coName] || '#667';
      return '<span style="display:inline-block;font-size:11px;margin:2px 4px 2px 0;padding:1px 6px;' +
        'background:' + coColor + '22;border:1px solid ' + coColor + '44;border-radius:3px;color:' + coColor + ';cursor:pointer" ' +
        'onclick="showAuthorDetail(\'' + escHtml(coName) + '\')">' +
        escHtml(coName) + ' <span style="color:#666;font-size:9px">(' + coCount + ')</span></span>';
    }).join('');
  }

  // Active years
  var yearsHtml = '';
  if (a.yrs && a.yrs.length > 0) {
    yearsHtml = a.yrs.join(', ');
  }

  content.innerHTML =
    '<h2 style="color:' + color + '">' + escHtml(username) + '</h2>' +
    '<div class="meta">Researcher &middot; <a href="https://ethresear.ch/u/' + encodeURIComponent(username) +
    '" target="_blank">View profile &rarr;</a></div>' +
    '<div class="detail-stat"><span class="label">Topics Created</span><span class="value">' + a.tc + '</span></div>' +
    '<div class="detail-stat"><span class="label">Total Posts</span><span class="value">' + a.tp.toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Total Likes</span><span class="value">' + a.lk.toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Influence Score</span><span class="value">' + a.inf.toFixed(3) + '</span></div>' +
    '<div class="detail-stat"><span class="label">Cited by</span><span class="value">' + a.ind + ' topics</span></div>' +
    '<div class="detail-stat"><span class="label">Active Years</span><span class="value">' + yearsHtml + '</span></div>' +
    (threadBarsHtml ?
      '<div style="margin-top:12px"><strong style="font-size:11px;color:#888">Thread Distribution</strong>' +
      '<div style="margin-top:6px">' + threadBarsHtml + '</div></div>' : '') +
    (topTopicsHtml ?
      '<div class="detail-refs" style="margin-top:12px"><h4>Top Topics</h4>' + topTopicsHtml + '</div>' : '') +
    (coHtml ?
      '<div style="margin-top:12px"><strong style="font-size:11px;color:#888">Co-Researchers</strong>' +
      '<div style="margin-top:6px">' + coHtml + '</div></div>' : '');

  panel.classList.add('open');
}

// === LINEAGE TRACING ===
function traceLineage(topicId) {
  if (lineageActive && lineageSet.has(topicId)) {
    // Toggle off
    clearLineage();
    return;
  }

  // BFS upstream (follow incoming refs) and downstream (follow outgoing refs)
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  lineageSet.add(topicId);

  // Upstream: who does this topic cite, and who do THEY cite (2 hops via t.out)
  // Actually incoming refs = topics that cite this one = descendants
  // outgoing refs = topics this one cites = ancestors
  // "upstream" = ancestors = follow outgoing refs
  // "downstream" = descendants = follow incoming refs

  var upQueue = [{id: topicId, depth: 0}];
  var visited = new Set([topicId]);
  while (upQueue.length > 0) {
    var cur = upQueue.shift();
    if (cur.depth >= 2) continue;
    var topic = DATA.topics[cur.id];
    if (!topic) continue;
    (topic.out || []).forEach(function(refId) {
      lineageSet.add(refId);
      lineageEdgeSet.add(cur.id + '-' + refId);
      lineageEdgeSet.add(refId + '-' + cur.id);
      if (!visited.has(refId)) {
        visited.add(refId);
        upQueue.push({id: refId, depth: cur.depth + 1});
      }
    });
  }

  // Downstream: follow incoming refs (topics that cite this one)
  var downQueue = [{id: topicId, depth: 0}];
  visited = new Set([topicId]);
  while (downQueue.length > 0) {
    var cur = downQueue.shift();
    if (cur.depth >= 2) continue;
    var topic = DATA.topics[cur.id];
    if (!topic) continue;
    (topic.inc || []).forEach(function(refId) {
      lineageSet.add(refId);
      lineageEdgeSet.add(cur.id + '-' + refId);
      lineageEdgeSet.add(refId + '-' + cur.id);
      if (!visited.has(refId)) {
        visited.add(refId);
        downQueue.push({id: refId, depth: cur.depth + 1});
      }
    });
  }

  lineageActive = true;
  applyLineageHighlight();
  updateLineageButton(topicId);
}

function clearLineage() {
  lineageActive = false;
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  applyFilters();
  // Update button if detail panel is open
  var btn = document.getElementById('lineage-btn');
  if (btn) {
    btn.textContent = 'Trace Lineage';
    btn.style.borderColor = '#5566aa';
    btn.style.color = '#8899cc';
  }
}

function updateLineageButton(topicId) {
  var btn = document.getElementById('lineage-btn');
  if (btn) {
    btn.textContent = 'Clear Lineage (' + lineageSet.size + ' topics)';
    btn.style.borderColor = '#88aaff';
    btn.style.color = '#88aaff';
  }
}

function applyLineageHighlight() {
  if (!lineageActive) return;
  if (activeView === 'timeline') applyLineageTimeline();
  else if (activeView === 'network') applyLineageNetwork();
}

function applyLineageTimeline() {
  d3.selectAll('.topic-circle')
    .attr('opacity', function(d) { return lineageSet.has(d.id) ? 1 : 0.04; })
    .attr('r', function(d) { return lineageSet.has(d.id) ? tlRScale(d.inf) * 1.2 : tlRScale(d.inf); });

  d3.selectAll('.edge-line')
    .attr('stroke', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? '#88aaff' : '#556';
    })
    .attr('stroke-opacity', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? 0.6 : 0.01;
    })
    .attr('stroke-width', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? 2 : 1;
    })
    .attr('marker-end', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? 'url(#arrow-lineage)' : 'url(#arrow-default)';
    });
}

function applyLineageNetwork() {
  d3.selectAll('.net-node circle').attr('opacity', function(d) {
    return lineageSet.has(d.id) ? 1 : 0.04;
  });

  d3.selectAll('.net-link')
    .attr('stroke', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? '#88aaff' : '#334';
    })
    .attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? 0.7 : 0.02;
    })
    .attr('stroke-width', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? 2.5 : 1;
    })
    .attr('marker-end', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
    });
}

// === DETAIL PANEL ===
function showDetail(t) {
  pinnedTopicId = t.id;
  applyPinnedHighlight();

  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');

  // EIP tags -- distinguish primary (topic is about this EIP) from mentions
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
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + id + '])" ' +
             'onmouseenter="highlightTopicInView(' + id + ')" ' +
             'onmouseleave="restorePinnedHighlight()">' +
             escHtml(ref.t) + '</a></div>';
    }).join('');
  }

  var incRefs = '';
  if (t.inc && t.inc.length > 0) {
    incRefs = t.inc.slice(0, 10).map(function(id) {
      var ref = DATA.topics[id];
      if (!ref) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + id + '])" ' +
             'onmouseenter="highlightTopicInView(' + id + ')" ' +
             'onmouseleave="restorePinnedHighlight()">' +
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
    '<div style="margin:10px 0 6px"><button id="lineage-btn" onclick="traceLineage(' + t.id + ')" ' +
    'style="background:#1a1a2e;border:1px solid ' + (lineageActive && lineageSet.has(t.id) ? '#88aaff' : '#5566aa') +
    ';color:' + (lineageActive && lineageSet.has(t.id) ? '#88aaff' : '#8899cc') +
    ';padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">' +
    (lineageActive && lineageSet.has(t.id) ? 'Clear Lineage (' + lineageSet.size + ' topics)' : 'Trace Lineage') +
    '</button></div>' +
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
  updateHash();
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('open');
  pinnedTopicId = null;
  applyFilters();
  updateHash();
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

// === URL HASH ROUTING ===
function parseHash() {
  var hash = window.location.hash.replace(/^#/, '');
  if (!hash) return {};
  var params = {};
  hash.split('&').forEach(function(part) {
    var kv = part.split('=');
    if (kv.length === 2) params[kv[0]] = decodeURIComponent(kv[1]);
  });
  return params;
}

function buildHash() {
  var parts = [];
  if (activeView && activeView !== 'timeline') parts.push('view=' + activeView);
  if (activeThread) parts.push('thread=' + encodeURIComponent(activeThread));
  if (activeAuthor) parts.push('author=' + encodeURIComponent(activeAuthor));
  if (pinnedTopicId) parts.push('topic=' + pinnedTopicId);
  return parts.length > 0 ? '#' + parts.join('&') : '';
}

function updateHash() {
  var newHash = buildHash();
  var current = window.location.hash || '';
  if (newHash !== current) {
    if (newHash) {
      history.replaceState(null, '', newHash);
    } else {
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }
}

function applyHash() {
  var params = parseHash();
  var changed = false;

  // Switch view if specified
  if (params.view && params.view !== activeView) {
    if (params.view === 'network' || params.view === 'coauthor' || params.view === 'timeline') {
      showView(params.view);
      changed = true;
    }
  }

  // Apply thread filter
  if (params.thread && params.thread !== activeThread) {
    if (DATA.threads[params.thread]) {
      activeThread = params.thread;
      activeAuthor = null;
      document.querySelectorAll('.thread-chip').forEach(function(c) {
        c.classList.toggle('active', c.dataset.thread === activeThread);
      });
      document.querySelectorAll('.author-item').forEach(function(c) { c.classList.remove('active'); });
      applyFilters();
      changed = true;
    }
  }

  // Apply author filter
  if (params.author && params.author !== activeAuthor) {
    if (DATA.authors[params.author]) {
      activeAuthor = params.author;
      activeThread = null;
      document.querySelectorAll('.author-item').forEach(function(c) {
        c.classList.toggle('active', c.dataset.author === activeAuthor);
      });
      document.querySelectorAll('.thread-chip').forEach(function(c) { c.classList.remove('active'); });
      applyFilters();
      changed = true;
    }
  }

  // Open topic detail
  if (params.topic) {
    var topicId = Number(params.topic);
    var t = DATA.topics[topicId];
    if (t) {
      showDetail(t);
      changed = true;
    }
  }
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
