// timeline.js — SVG swim-lane timeline view (production)

import { THREAD_COLORS, THREAD_ORDER, THREAD_NAMES, TIMELINE_ZOOM_EXTENT, EIP_STATUS_COLORS } from './constants.js';
import { getState, on, selectEntity, pinEntity, hoverEntity, setFilters, setLineage } from './state.js';
import { getCore, getCoreIndexes, getEips, getPapers, loadEips, loadPapers, loadGraph, getGraph, getGraphIndexes } from './data.js';

// --- Module state ---
let svg = null;
let initialized = false;
let plotW = 0;
let marginLeft = 0;
let xScaleOrig = null;   // original (unzoomed) time scale
let xScale = null;        // current (zoomed) time scale
let rScale = null;        // influence → radius
let laneIdx = {};         // threadId → lane index
let laneH = 0;            // height per lane
let laneOrder = [];       // ordered list of thread IDs (including '_other')
let topicLaneY0 = 0;      // y offset where topic lanes start
let swimH = 0;            // total swim-lane height
let histH = 24;           // histogram height
let forkLabelH = 18;      // extra row for fork labels
let zoomBehavior = null;
let rootG = null;         // fixed root group (for labels)
let zoomG = null;         // clipped + zoomed group
let edgeG = null;
let circleG = null;
let labelG = null;
let milestoneG = null;
let histG = null;
let xAxisG = null;

// Arrays for zoom updates
let eraRects = [];
let eraTexts = [];
let forkLines = [];
let forkLabels = [];
let forkHoverLines = [];
let liveLine = null;
let liveLabel = null;

// EIP layer state
let eipLayerG = null;
let eipCrossRefG = null;
let eipLayerBuilt = false;

// Paper layer state
let paperCiteG = null;   // citation edge group (behind diamonds)
let paperLayerG = null;
let paperLayerBuilt = false;
let paperLayerMode = null; // track which mode was used to build

const PAPER_LAYER_LIMITS = { focus: 200, context: 400, broad: 651 };

// Magicians layer state
let magLayerG = null;
let magCrossRefG = null;
let magLayerBuilt = false;

// Pin overlay (temporary edges + labels during pin)
let pinOverlayG = null;

// Lookup
let topicMap = {};
let labelSet = new Set();
let defaultInfluenceThreshold = 0;

const TL_MIN_ZOOM = TIMELINE_ZOOM_EXTENT[0];
const TL_MAX_ZOOM = TIMELINE_ZOOM_EXTENT[1];
const TL_EDGE_PAD_FRACTION = 0.05;
const TL_EDGE_PAD_MIN = 40;

// --- Utilities ---

const STOP_WORDS = new Set([
  'the','and','for','with','from','that','this','have','been','will','are',
  'was','were','but','not','all','can','had','its','they','would','what',
  'when','which','their','also','more','some','than','about','into','over',
  'such','after','through','very','much','only','between','how','does',
  'each','where','based','using','towards','toward','ethereum','analysis',
  'approach','method','protocol','system','systems','network','networks',
]);

function extractKeywords(title) {
  if (!title) return new Set();
  return new Set(
    title.toLowerCase()
      .replace(/[^\w\s-]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length >= 4 && !STOP_WORDS.has(w))
  );
}

function keywordOverlap(setA, setB) {
  let count = 0;
  for (const w of setA) { if (setB.has(w)) count++; }
  return count;
}

function hashCode(n) {
  return ((n * 2654435761) >>> 0) % 10000;
}

function diamondPath(cx, cy, r) {
  return 'M' + cx + ',' + (cy - r) +
    'L' + (cx + r) + ',' + cy +
    'L' + cx + ',' + (cy + r) +
    'L' + (cx - r) + ',' + cy + 'Z';
}

function trianglePath(cx, cy, r) {
  const h = r * Math.sqrt(3) / 2;
  return 'M' + cx + ',' + (cy - r) +
    'L' + (cx + h) + ',' + (cy + r / 2) +
    'L' + (cx - h) + ',' + (cy + r / 2) + 'Z';
}

function starPoints(cx, cy, outerR, innerR, nPoints) {
  const pts = [];
  for (let i = 0; i < nPoints * 2; i++) {
    const angle = (i * Math.PI / nPoints) - Math.PI / 2;
    const r = i % 2 === 0 ? outerR : innerR;
    pts.push((cx + r * Math.cos(angle)).toFixed(1) + ',' + (cy + r * Math.sin(angle)).toFixed(1));
  }
  return pts.join(' ');
}

function escHtml(s) {
  const el = document.createElement('span');
  el.textContent = s || '';
  return el.innerHTML;
}

function magiciansThreadFromTopic(mt) {
  if (!mt) return null;
  const counts = {};
  for (const tid of (mt.er || [])) {
    const t = topicMap[tid];
    if (t?.th) counts[t.th] = (counts[t.th] || 0) + 1;
  }
  const graphData = getGraph();
  const eipCat = graphData?.eipCatalog || {};
  for (const eipNum of (mt.eips || [])) {
    const e = eipCat[String(eipNum)];
    if (e?.th) counts[e.th] = (counts[e.th] || 0) + 1;
  }
  let best = null, bestCount = 0;
  for (const [th, count] of Object.entries(counts)) {
    if (count > bestCount) { bestCount = count; best = th; }
  }
  return best;
}

function magiciansEngagementScore(mt) {
  if (!mt) return 0;
  return (mt.lk || 0) * 2 + Math.sqrt(mt.pc || 0) + Math.log1p(mt.vw || 0) * 0.3;
}

function clampTimelineTransform(t) {
  let k = t && isFinite(t.k) ? t.k : 1;
  k = Math.max(TL_MIN_ZOOM, Math.min(TL_MAX_ZOOM, k));

  if (!plotW || plotW <= 0) {
    return d3.zoomIdentity.translate(0, 0).scale(k);
  }

  // Account for detail panel overlay (420px absolute-positioned over timeline)
  const detailPanel = document.getElementById('detail-panel');
  const detailW = (detailPanel && detailPanel.classList.contains('open')) ? detailPanel.offsetWidth : 0;

  const edgePad = Math.max(TL_EDGE_PAD_MIN, plotW * TL_EDGE_PAD_FRACTION);
  const minX = plotW * (1 - k) - edgePad - detailW;
  const maxX = edgePad;
  let x = t && isFinite(t.x) ? t.x : 0;
  if (x < minX) x = minX;
  if (x > maxX) x = maxX;

  return d3.zoomIdentity.translate(x, 0).scale(k);
}

function topicMatchesFilter(t, st) {
  if (st.minInfluence > 0 && (t.inf || 0) < st.minInfluence) return false;
  if (st.activeThread && t.th !== st.activeThread) return false;
  if (st.activeAuthor && t.a !== st.activeAuthor) return false;
  if (st.activeCategory && t.cat !== st.activeCategory) return false;
  if (st.activeTag && !(t.tg || []).includes(st.activeTag)) return false;
  return true;
}

function computeDefaultThreshold(topics) {
  const allInfs = Object.values(topics).map(t => t.inf || 0);
  const nonMinorCount = Object.values(topics).filter(t => !t.mn).length;
  if (nonMinorCount <= 0 || nonMinorCount >= allInfs.length) return 0;
  allInfs.sort((a, b) => b - a);
  return allInfs[nonMinorCount - 1] || 0;
}

// --- Tooltip ---

function showTooltip(ev, t) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const color = THREAD_COLORS[t.th] || '#666';
  const primary = (t.peips && t.peips.length > 0) ? ' [EIP-' + t.peips.join(', EIP-') + ']' : '';
  tip.innerHTML = '<strong>' + escHtml(t.t) + '</strong><br>' +
    escHtml(t.a) + ' \u00b7 ' + (t.d || '').slice(0, 10) + ' \u00b7 inf: ' + (t.inf || 0).toFixed(2) +
    primary;
  tip.style.display = 'block';

  let x = ev.clientX + 14;
  let y = ev.clientY - 10;
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

let hideTooltipTimer = null;
function hideTooltip() {
  clearTimeout(hideTooltipTimer);
  hideTooltipTimer = setTimeout(() => {
    const tip = document.getElementById('tooltip');
    if (tip) tip.style.display = 'none';
  }, 80);
}
function cancelHideTooltip() {
  clearTimeout(hideTooltipTimer);
}

function showHistTooltip(ev, d) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const mn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  tip.innerHTML = mn[d.date.getMonth()] + ' ' + d.date.getFullYear() + ': ' + d.count + ' topic' + (d.count !== 1 ? 's' : '');
  tip.style.display = 'block';
  tip.style.left = (ev.clientX + 10) + 'px';
  tip.style.top = (ev.clientY - 24) + 'px';
}

function showForkTooltip(ev, f) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const eipList = (f.eips || []).map(e => 'EIP-' + e).join(', ');
  const relCount = (f.rt || []).length;
  tip.innerHTML = '<strong>' + escHtml(f.cn || f.n) + '</strong>' +
    (f.d ? '<br><span style="color:#888">' + f.d + '</span>' : '') +
    (f.el ? '<br>EL: ' + escHtml(f.el) : '') +
    (f.cl ? ' &middot; CL: ' + escHtml(f.cl) : '') +
    (eipList ? '<br><span style="color:#88aacc">EIPs: ' + eipList + '</span>' : '') +
    (relCount > 0 ? '<br><span style="color:#666">' + relCount + ' related topics</span>' : '');
  tip.style.display = 'block';
  let x = ev.clientX + 14;
  let y = ev.clientY - 10;
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

// --- Label management ---

function syncLabelsFromOpMap(opMap) {
  if (!labelG) return;
  const st = getState();
  const postsOff = !st.showPosts;
  labelG.selectAll('.topic-label').attr('opacity', function (d) {
    if (postsOff) return 0;
    const cOp = opMap[d.id];
    return (cOp !== undefined && cOp > 0.25) ? Math.min(cOp + 0.05, 0.9) : 0;
  });
  if (milestoneG) {
    milestoneG.selectAll('.milestone-marker').each(function (d) {
      const cOp = opMap[d.id];
      const vis = !postsOff && st.milestonesVisible && (cOp === undefined || cOp > 0.25);
      d3.select(this).style('display', vis ? null : 'none');
    });
  }
}

function syncLabels() {
  const opMap = {};
  if (!circleG) return;
  circleG.selectAll('.topic-circle').each(function (d) {
    opMap[d.id] = parseFloat(d3.select(this).attr('opacity'));
  });
  syncLabelsFromOpMap(opMap);
}

// --- Build ---

export function init() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('timeline-view');
  if (!container) return;

  const core = getCore();
  if (!core) return;

  topicMap = core.topics || {};

  buildTimeline(container, core);

  // Set up default influence threshold
  const defaultThreshold = computeDefaultThreshold(topicMap);
  defaultInfluenceThreshold = defaultThreshold;
  if (defaultThreshold > 0) {
    setFilters({ minInfluence: defaultThreshold });
    // Set the slider DOM element
    const slider = document.getElementById('inf-slider');
    const maxInf = d3.max(Object.values(topicMap), t => t.inf) || 1;
    const pct = Math.round(defaultThreshold / maxInf * 100);
    if (slider) {
      slider.value = pct;
      const label = document.getElementById('inf-slider-label');
      if (label) label.textContent = pct === 0 ? '0%' : pct + '%';
    }
  }

  // Event subscriptions
  on('filters:changed', filterTimeline);
  on('filters:changed', onFiltersChangedPaperMode);
  on('selection:changed', onSelectionChanged);
  on('lineage:changed', onLineageChanged);
  on('milestones:changed', onMilestonesChanged);
  on('content:changed', onContentChanged);
  on('content:changed', ({ key }) => {
    // Skip sync filterTimeline for async layer toggles — their builders call filterTimeline when ready
    if (key === 'showPapers' || key === 'showEips') return;
    filterTimeline();
  });
  on('reset', onReset);
  on('pin:changed', ({ current }) => { if (!current) filterTimeline(); });

  // ResizeObserver (debounced to avoid rapid-fire rebuilds)
  let resizeTimer = null;
  const ro = new ResizeObserver(() => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(rebuildTimeline, 200);
  });
  ro.observe(container);
}

function rebuildTimeline() {
  const container = document.getElementById('timeline-view');
  if (!container) return;
  const core = getCore();
  if (!core) return;
  // Clear everything
  container.innerHTML = '';
  svg = null;
  zoomBehavior = null;
  rootG = null;
  zoomG = null;
  edgeG = null;
  circleG = null;
  labelG = null;
  milestoneG = null;
  histG = null;
  xAxisG = null;
  eraRects = [];
  eraTexts = [];
  forkLines = [];
  forkLabels = [];
  forkHoverLines = [];
  liveLine = null;
  liveLabel = null;
  eipLayerG = null;
  eipCrossRefG = null;
  eipLayerBuilt = false;
  paperLayerG = null;
  paperLayerBuilt = false;
  paperLayerMode = null;
  magLayerG = null;
  magCrossRefG = null;
  magLayerBuilt = false;
  labelSet = new Set();
  buildTimeline(container, core);
}

function buildTimeline(container, core) {
  const width = container.clientWidth || 900;
  const height = container.clientHeight || 700;

  const margin = { top: 50, right: 40, bottom: 30 + histH + forkLabelH, left: 180 };
  plotW = width - margin.left - margin.right;
  marginLeft = margin.left;
  const plotH = height - margin.top - margin.bottom;
  swimH = plotH - histH;
  topicLaneY0 = 0;

  // Group topics by thread for swim lanes
  const threadTopics = {};
  THREAD_ORDER.forEach(tid => { threadTopics[tid] = []; });
  threadTopics['_other'] = [];

  Object.values(topicMap).forEach(t => {
    const th = t.th;
    if (th && threadTopics[th]) threadTopics[th].push(t);
    else threadTopics['_other'].push(t);
  });

  laneOrder = [...THREAD_ORDER.filter(t => (threadTopics[t] || []).length > 0), '_other'];
  laneH = swimH / laneOrder.length;

  // Time scale
  const allDates = Object.values(topicMap).map(t => new Date(t.d)).filter(d => !isNaN(d));
  (core.forks || []).forEach(f => { if (f.d) allDates.push(new Date(f.d)); });
  Object.values(core.eipCatalog || {}).forEach(e => {
    if (e.cr) { const d = new Date(e.cr); if (!isNaN(d)) allDates.push(d); }
  });

  if (allDates.length === 0) return;

  xScaleOrig = d3.scaleTime()
    .domain([d3.min(allDates), d3.max(allDates)])
    .range([0, plotW]);
  xScale = xScaleOrig.copy();

  // Size scale
  const maxInf = d3.max(Object.values(topicMap), t => t.inf) || 1;
  rScale = d3.scaleSqrt().domain([0, maxInf]).range([2.5, 14]);

  // Create SVG
  const wrapper = document.createElement('div');
  wrapper.className = 'timeline-container';
  container.appendChild(wrapper);

  svg = d3.select(wrapper).append('svg')
    .attr('width', width)
    .attr('height', height);

  // Block browser swipe-back on SVG
  const svgNode = svg.node();
  svgNode.addEventListener('wheel', function (ev) {
    ev.preventDefault();
  }, { passive: false });

  // Clip path
  const defs = svg.append('defs');
  defs.append('clipPath').attr('id', 'tl-clip')
    .append('rect').attr('x', 0).attr('y', -margin.top).attr('width', plotW).attr('height', height);

  // Arrow markers
  defs.append('marker').attr('id', 'arrow-default')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4).attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-default').attr('opacity', 0.3);
  defs.append('marker').attr('id', 'arrow-highlight')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4).attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-highlight').attr('opacity', 0.8);
  defs.append('marker').attr('id', 'arrow-lineage')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4).attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-lineage').attr('opacity', 0.9);

  // Root group offset by margins
  const root = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
  rootG = root;

  // Fixed layer for y-axis labels (not affected by zoom)
  const fixedG = root.append('g');

  // Clipped layer for zoomable content
  const clipG = root.append('g').attr('clip-path', 'url(#tl-clip)');
  zoomG = clipG.append('g');

  // Lane index
  laneIdx = {};
  laneOrder.forEach((tid, i) => { laneIdx[tid] = i; });

  // --- Pre-compute fixed y positions for every topic ---
  Object.values(topicMap).forEach(t => {
    const th = (t.th && laneIdx[t.th] !== undefined) ? t.th : '_other';
    const lane = laneIdx[th];
    const yBase = topicLaneY0 + lane * laneH + laneH * 0.12;
    const yRange = laneH * 0.76;
    t._yPos = yBase + (hashCode(t.id) % 100) / 100 * yRange;
    t._date = new Date(t.d);
  });

  // --- Era backgrounds ---
  const eraColors = ['#334', '#343', '#334', '#433', '#343'];
  eraRects = [];
  eraTexts = [];
  (core.eras || []).forEach((era, i) => {
    const x0 = xScaleOrig(new Date(era.start));
    const x1 = xScaleOrig(new Date(era.end));
    eraRects.push(
      zoomG.append('rect').attr('class', 'era-bg')
        .attr('x', x0).attr('y', 0).attr('width', x1 - x0).attr('height', topicLaneY0 + swimH)
        .attr('fill', eraColors[i] || '#333')
        .datum({ start: new Date(era.start), end: new Date(era.end) })
    );
    eraTexts.push(
      zoomG.append('text').attr('x', (x0 + x1) / 2).attr('y', -8)
        .attr('text-anchor', 'middle').attr('fill', '#555').attr('font-size', 10)
        .style('cursor', 'pointer')
        .text(era.name)
        .datum({ start: new Date(era.start), end: new Date(era.end), idx: i })
        .on('click', function (ev, d) { selectEntity({ type: 'era', id: d.idx }); })
        .on('mouseover', function () { d3.select(this).attr('fill', '#999'); })
        .on('mouseout', function () { d3.select(this).attr('fill', '#555'); })
    );
  });

  // --- Fork lines + labels + hover areas ---
  forkLines = [];
  forkLabels = [];
  forkHoverLines = [];
  (core.forks || []).forEach(f => {
    if (!f.d) return;
    const fd = new Date(f.d);
    const fx = xScaleOrig(fd);
    forkLines.push(
      zoomG.append('line').attr('class', 'fork-line')
        .attr('x1', fx).attr('x2', fx)
        .attr('y1', -5).attr('y2', topicLaneY0 + swimH + histH)
        .datum(fd)
    );
    forkLabels.push(
      zoomG.append('text').attr('class', 'fork-label')
        .attr('x', fx).attr('y', topicLaneY0 + swimH + histH + 15)
        .attr('text-anchor', 'middle')
        .attr('paint-order', 'stroke').attr('stroke', '#0a0a0f').attr('stroke-width', 3)
        .text(f.cn || f.n)
        .datum(fd)
    );
    forkHoverLines.push(
      zoomG.append('line').attr('class', 'fork-hover-line')
        .attr('x1', fx).attr('x2', fx)
        .attr('y1', -5).attr('y2', topicLaneY0 + swimH + histH)
        .datum({ date: fd, fork: f })
        .on('mouseover', function (ev, d) { showForkTooltip(ev, d.fork); })
        .on('mouseout', function () { hideTooltip(); })
        .on('click', function (ev, d) { ev.stopPropagation(); selectEntity({ type: 'fork', id: d.fork.n }); })
    );
  });

  // --- "ethresear.ch live" annotation ---
  const ethresearchLiveDate = new Date('2017-08-17');
  const liveX = xScaleOrig(ethresearchLiveDate);
  const liveLineData = { date: ethresearchLiveDate };
  liveLine = zoomG.append('line')
    .attr('class', 'ethresearch-live-line')
    .attr('x1', liveX).attr('x2', liveX)
    .attr('y1', -5).attr('y2', topicLaneY0 + swimH + histH)
    .attr('stroke', '#5a8a5a').attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '6 3').attr('opacity', 0.6)
    .datum(liveLineData);
  liveLabel = zoomG.append('text')
    .attr('class', 'ethresearch-live-label')
    .attr('x', liveX).attr('y', -12)
    .attr('text-anchor', 'middle').attr('fill', '#6aaa6a')
    .attr('font-size', 10).attr('font-weight', 600)
    .attr('paint-order', 'stroke').attr('stroke', '#0a0a0f').attr('stroke-width', 3)
    .text('ethresear.ch live')
    .datum(liveLineData);

  // --- Swim lane labels + separators ---
  laneOrder.forEach((tid, i) => {
    const y = topicLaneY0 + i * laneH + laneH / 2;
    const name = tid === '_other' ? 'Other' : (THREAD_NAMES[tid] || tid);
    const color = tid === '_other' ? '#555' : (THREAD_COLORS[tid] || '#555');
    fixedG.append('text').attr('x', -10).attr('y', y)
      .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
      .attr('fill', color).attr('font-size', 11).attr('font-weight', 500)
      .text(name.length > 22 ? name.slice(0, 20) + '\u2026' : name);
    if (i > 0) {
      fixedG.append('line').attr('x1', 0).attr('x2', plotW)
        .attr('y1', topicLaneY0 + i * laneH).attr('y2', topicLaneY0 + i * laneH)
        .attr('stroke', '#1a1a2a').attr('stroke-width', 0.5);
    }
  });

  // --- Citation edges ---
  edgeG = zoomG.append('g');
  const graphEdges = core.graph?.edges || [];
  graphEdges.forEach(e => {
    const sT = topicMap[e.source];
    const tT = topicMap[e.target];
    if (sT && tT && sT._yPos !== undefined && tT._yPos !== undefined) {
      edgeG.append('line').attr('class', 'edge-line')
        .attr('x1', xScaleOrig(sT._date)).attr('y1', sT._yPos)
        .attr('x2', xScaleOrig(tT._date)).attr('y2', tT._yPos)
        .attr('stroke-opacity', 0.06)
        .attr('marker-end', 'url(#arrow-default)')
        .datum({ source: e.source, target: e.target, sd: sT._date, td: tT._date, sy: sT._yPos, ty: tT._yPos });
    }
  });

  // --- Topic circles ---
  circleG = zoomG.append('g');
  Object.values(topicMap).forEach(t => {
    if (t._yPos === undefined) return;
    const color = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';
    let clickTimer = null;

    const circle = circleG.append('circle')
      .attr('class', 'topic-circle')
      .attr('cx', xScaleOrig(t._date)).attr('cy', t._yPos)
      .attr('r', rScale(t.inf))
      .attr('fill', color)
      .attr('stroke', color)
      .attr('stroke-width', t.mn ? 1 : 0.5)
      .attr('opacity', 0.65)
      .datum(t)
      .on('click', function (ev, d) {
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
          // Double-click: open detail panel
          selectEntity({ type: 'topic', id: d.id });
          return;
        }
        clickTimer = setTimeout(function () {
          clickTimer = null;
          // Single-click: pin highlight (no detail panel)
          pinEntity({ type: 'topic', id: d.id });
          applyPinnedHighlight();
        }, 220);
      })
      .on('mouseover', function (ev, d) { onTopicHover(ev, d, true); })
      .on('mouseout', function (ev, d) { onTopicHover(ev, d, false); });

    if (t.mn) circle.attr('stroke-dasharray', '3 2');
  });

  // --- Topic labels (top 30 by influence) ---
  labelG = zoomG.append('g');
  const topByInf = Object.values(topicMap)
    .filter(t => t._yPos !== undefined)
    .sort((a, b) => b.inf - a.inf)
    .slice(0, 30);
  labelSet = new Set(topByInf.map(t => t.id));

  topByInf.forEach(t => {
    const maxChars = 28;
    const txt = t.t.length > maxChars ? t.t.slice(0, maxChars - 1) + '\u2026' : t.t;
    labelG.append('text').attr('class', 'topic-label')
      .attr('x', xScaleOrig(t._date) + rScale(t.inf) + 3)
      .attr('y', t._yPos + 3)
      .attr('opacity', 0.75)
      .datum(t)
      .text(txt);
  });

  // --- Milestone markers (star-shaped) ---
  milestoneG = zoomG.append('g');
  const milestoneData = [];
  const threads = core.threads || {};
  THREAD_ORDER.forEach(tid => {
    const th = threads[tid];
    if (!th || !th.ms) return;
    th.ms.forEach(ms => {
      const topic = topicMap[ms.id];
      if (topic && topic._yPos !== undefined) {
        milestoneData.push({ topic: topic, note: ms.n, threadId: tid });
      }
    });
  });
  const st = getState();
  milestoneData.forEach(md => {
    const r = rScale(md.topic.inf) + 4;
    milestoneG.append('polygon')
      .attr('class', 'milestone-marker')
      .attr('points', starPoints(xScaleOrig(md.topic._date), md.topic._yPos, r, r * 0.5, 4))
      .datum(md.topic)
      .on('click', function (ev, d) { selectEntity({ type: 'topic', id: d.id }); })
      .on('mouseover', function (ev, d) { showTooltip(ev, d); })
      .on('mouseout', function () { hideTooltip(); })
      .style('display', st.milestonesVisible ? null : 'none');
  });

  // --- Monthly activity histogram ---
  const monthBins = {};
  Object.values(topicMap).forEach(t => {
    const d = t._date;
    if (!d || isNaN(d)) return;
    const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
    if (!monthBins[key]) monthBins[key] = { date: new Date(d.getFullYear(), d.getMonth(), 1), count: 0 };
    monthBins[key].count++;
  });
  const histData = Object.values(monthBins).sort((a, b) => a.date - b.date);
  const maxCount = d3.max(histData, d => d.count) || 1;
  const histYScale = d3.scaleLinear().domain([0, maxCount]).range([0, histH - 2]);
  const barWidthBase = Math.max(1, xScaleOrig(new Date(2020, 1, 1)) - xScaleOrig(new Date(2020, 0, 1)));

  histG = zoomG.append('g').attr('class', 'histogram-g')
    .attr('transform', 'translate(0,' + (topicLaneY0 + swimH) + ')');

  histG.selectAll('.histogram-bar')
    .data(histData)
    .join('rect')
    .attr('class', 'histogram-bar')
    .attr('x', d => xScaleOrig(d.date))
    .attr('y', d => histH - histYScale(d.count))
    .attr('width', Math.max(1, barWidthBase * 0.85))
    .attr('height', d => histYScale(d.count))
    .attr('rx', 1)
    .on('mouseover', function (ev, d) { showHistTooltip(ev, d); })
    .on('mouseout', function () { hideTooltip(); });

  // --- X axis ---
  xAxisG = root.append('g')
    .attr('class', 'x-axis')
    .attr('transform', 'translate(0,' + (topicLaneY0 + swimH + histH + forkLabelH) + ')');
  const xAxisFn = d3.axisBottom(xScaleOrig).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
  xAxisG.call(xAxisFn);
  xAxisG.selectAll('text').attr('fill', '#666').attr('font-size', 12);
  xAxisG.selectAll('.domain, .tick line').attr('stroke', '#333');

  // --- Zoom (horizontal only) ---
  zoomBehavior = d3.zoom()
    .scaleExtent([TL_MIN_ZOOM, TL_MAX_ZOOM])
    .translateExtent([[0, 0], [plotW, height]])
    .extent([[0, 0], [plotW, height]])
    .constrain(function (transform) {
      return clampTimelineTransform(transform);
    })
    .filter(function (ev) {
      if (ev.type === 'wheel') return true;
      if (ev.type === 'dblclick') return false;
      return !ev.button;
    })
    .on('zoom', onZoom);

  svg.call(zoomBehavior);

  // Click on empty canvas clears selection
  svg.on('click.clearFocus', function (ev) {
    if (ev.defaultPrevented) return;
    const target = ev.target;
    // Only block unpin for actual interactive entity nodes (which also call stopPropagation).
    // Everything else (era-bg, fork lines, histogram bars, etc.) is "background".
    if (target && target.closest &&
      target.closest('.topic-circle,.eip-square,.paper-diamond,.paper-hit,.magicians-triangle')) return;
    const st = getState();
    if (st.pinnedEntity || st.selectedEntity) {
      pinEntity(null);
      selectEntity(null);
      filterTimeline();
    }
  });

  // Double-click resets zoom on empty canvas
  svg.on('dblclick.zoom', function (ev) {
    const target = ev.target;
    if (target && target.closest &&
      target.closest('.topic-circle,.milestone-marker,.fork-hover-line,.histogram-bar')) return;
    svg.transition().duration(500).call(zoomBehavior.transform, d3.zoomIdentity);
  });

  // Apply initial filter state
  filterTimeline();
}

// --- Zoom handler ---

function onZoom(ev) {
  const t = ev.transform;
  const newX = t.rescaleX(xScaleOrig);
  xScale = newX;

  // Topic circles
  d3.selectAll('.topic-circle').attr('cx', d => newX(d._date));

  // Topic labels
  d3.selectAll('.topic-label').attr('x', d => newX(d._date) + rScale(d.inf) + 3);

  // Milestone markers
  d3.selectAll('.milestone-marker').attr('points', d => {
    const r = rScale(d.inf) + 4;
    return starPoints(newX(d._date), d._yPos, r, r * 0.5, 4);
  });

  // Edges
  d3.selectAll('.edge-line')
    .attr('x1', d => newX(d.sd))
    .attr('x2', d => newX(d.td));

  // Era backgrounds + labels
  eraRects.forEach(r => {
    const d = r.datum();
    r.attr('x', newX(d.start)).attr('width', Math.max(0, newX(d.end) - newX(d.start)));
  });
  eraTexts.forEach(txt => {
    const d = txt.datum();
    txt.attr('x', (newX(d.start) + newX(d.end)) / 2);
  });

  // Fork lines + labels + hover areas
  forkLines.forEach(l => { const d = l.datum(); l.attr('x1', newX(d)).attr('x2', newX(d)); });
  forkLabels.forEach(l => { const d = l.datum(); l.attr('x', newX(d)); });
  forkHoverLines.forEach(l => { const d = l.datum(); l.attr('x1', newX(d.date)).attr('x2', newX(d.date)); });

  // ethresear.ch live marker
  if (liveLine && liveLabel) {
    const lx = newX(liveLine.datum().date);
    liveLine.attr('x1', lx).attr('x2', lx);
    liveLabel.attr('x', lx);
  }

  // Histogram bars
  const zoomedBarW = Math.max(1, (newX(new Date(2020, 1, 1)) - newX(new Date(2020, 0, 1))) * 0.85);
  d3.selectAll('.histogram-bar')
    .attr('x', d => newX(d.date))
    .attr('width', zoomedBarW);

  // X-axis with adaptive tick density
  let axisFn;
  if (t.k > 4) {
    axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(1)).tickFormat(d3.timeFormat('%b %Y'));
  } else if (t.k > 2) {
    axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat('%b %Y'));
  } else {
    axisFn = d3.axisBottom(newX).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
  }
  if (xAxisG) {
    xAxisG.call(axisFn);
    xAxisG.selectAll('text').attr('fill', '#666').attr('font-size', 12);
    xAxisG.selectAll('.domain, .tick line').attr('stroke', '#333');
  }

  // EIP layer zoom update
  updateEipLayerZoom(newX);

  // Paper layer zoom update
  updatePaperLayerZoom(newX);

  // Magicians layer zoom update
  updateMagiciansLayerZoom(newX);

  // Pin overlay zoom update
  updatePinOverlayZoom(newX);

  // Adaptive labels: show more labels when zoomed in
  updateLabelsForZoom(t.k);
}

function updateLabelsForZoom(zoomK) {
  if (!labelG || !rScale) return;

  // At base zoom show top 30; at max zoom show top ~120
  const baseCount = 30;
  const targetCount = Math.min(200, Math.round(baseCount + (zoomK - 1) * 15));

  const sorted = Object.values(topicMap)
    .filter(t => t._yPos !== undefined && t.inf > 0)
    .sort((a, b) => b.inf - a.inf);

  const newLabelTopics = sorted.slice(0, targetCount);
  const newLabelIds = new Set(newLabelTopics.map(t => t.id));

  // Add any missing labels
  newLabelTopics.forEach(t => {
    if (labelSet.has(t.id)) return;
    labelSet.add(t.id);
    const maxChars = 28;
    const txt = t.t.length > maxChars ? t.t.slice(0, maxChars - 1) + '\u2026' : t.t;
    labelG.append('text').attr('class', 'topic-label')
      .attr('x', xScale(t._date) + rScale(t.inf) + 3)
      .attr('y', t._yPos + 3)
      .attr('opacity', 0.75)
      .datum(t)
      .text(txt);
  });

  // Hide labels that are below the new threshold
  labelG.selectAll('.topic-label').style('display', function (d) {
    return newLabelIds.has(d.id) ? null : 'none';
  });
}

// --- Hover ---

function onTopicHover(ev, d, entering) {
  if (entering) {
    const circleEl = d3.select(ev.currentTarget);
    if (circleEl.style('pointer-events') === 'none') return;
    showTooltip(ev, d);
    hoverEntity({ type: 'topic', id: d.id });

    // If pinned, don't override the pinned highlight — only show tooltip
    if (getState().pinnedEntity) return;

    // Highlight this topic and its direct connections
    const indexes = getCoreIndexes();
    const connected = indexes?.topicEdgeIndex?.[String(d.id)] || new Set();

    const st = getState();
    const hasActiveFilter = st.activeThread || st.activeAuthor || st.activeCategory || st.activeTag;

    const targetOp = {};
    circleG.selectAll('.topic-circle').each(function (t) {
      if (t.id === d.id) { targetOp[t.id] = 1; return; }
      if (connected.has(t.id)) { targetOp[t.id] = 0.8; return; }
      const belowThreshold = st.minInfluence > 0 && (t.inf || 0) < st.minInfluence;
      if (belowThreshold) { targetOp[t.id] = 0.02; return; }
      if (hasActiveFilter && !topicMatchesFilter(t, st)) { targetOp[t.id] = 0.03; return; }
      targetOp[t.id] = 0.12;
    });
    circleG.selectAll('.topic-circle').attr('opacity', d => targetOp[d.id]);

    edgeG.selectAll('.edge-line')
      .attr('stroke-opacity', e => {
        if (e.source === d.id || e.target === d.id) return 0.5;
        return 0.01;
      })
      .attr('stroke-width', e => {
        if (e.source === d.id || e.target === d.id) return 2;
        return 1;
      })
      .attr('stroke', e => {
        if (e.source === d.id || e.target === d.id) return '#88aaff';
        return '#556';
      })
      .attr('marker-end', e => {
        if (e.source === d.id || e.target === d.id) return 'url(#arrow-highlight)';
        return 'url(#arrow-default)';
      });

    syncLabelsFromOpMap(targetOp);

    // Highlight connected cross-entity items, dim the rest (v1-aligned)
    const hoverConns = buildPinnedConnections({ type: 'topic', id: d.id });

    if (eipLayerG && eipLayerBuilt) {
      eipLayerG.selectAll('.eip-square').each(function (ed) {
        const isConn = hoverConns.connectedEips.has(Number(ed.num));
        d3.select(this)
          .attr('fill-opacity', isConn ? 0.5 : 0.06)
          .attr('stroke-opacity', isConn ? 0.6 : 0.06)
          .style('pointer-events', isConn ? 'all' : 'none');
      });
      if (eipCrossRefG) {
        eipCrossRefG.selectAll('.cross-ref-edge').each(function (ed) {
          const show = hoverConns.connectedEips.has(Number(ed.eipNum)) && (ed.topicId === d.id || connected.has(Number(ed.topicId)));
          d3.select(this).attr('stroke-opacity', show ? 0.5 : 0.01);
        });
      }
    }
    if (paperLayerG && paperLayerBuilt) {
      const curX = xScale || xScaleOrig;
      paperLayerG.selectAll('.paper-diamond').each(function (pd) {
        const isConn = hoverConns.connectedPapers.has(pd.paper.id);
        const el = d3.select(this);
        el.attr('fill-opacity', isConn ? 0.8 : 0.04)
          .attr('stroke-opacity', isConn ? 0.9 : 0.04);
        if (isConn) {
          const boosted = Math.max(7, pd.r * 1.6);
          el.attr('d', diamondPath(curX(pd.date), pd.y, boosted))
            .attr('stroke-width', 1.5).attr('stroke', '#fff');
        }
      });
      paperLayerG.selectAll('.paper-hit').each(function (pd) {
        d3.select(this).style('pointer-events', hoverConns.connectedPapers.has(pd.paper.id) ? 'all' : 'none');
      });
      if (paperCiteG) paperCiteG.selectAll('.paper-cite-edge').attr('stroke-opacity', 0.008);
      // Draw hover edges from topic to connected papers
      clearPinOverlay();
      if (!pinOverlayG) pinOverlayG = zoomG.append('g').attr('class', 'pin-overlay');
      pinOverlayG.raise();
      const topicX = curX(d._date), topicY = d._yPos;
      paperLayerG.selectAll('.paper-diamond').each(function (pd) {
        if (!hoverConns.connectedPapers.has(pd.paper.id)) return;
        pinOverlayG.append('line').attr('class', 'pin-edge')
          .attr('x1', topicX).attr('y1', topicY)
          .attr('x2', curX(pd.date)).attr('y2', pd.y)
          .attr('stroke', '#8eb8ff').attr('stroke-opacity', 0.44)
          .attr('stroke-width', 1.2).attr('stroke-dasharray', '4 2')
          .datum({ x1Date: d._date, y1: topicY, x2Date: pd.date, y2: pd.y });
      });
    }
    if (magLayerG && magLayerBuilt) {
      magLayerG.selectAll('.magicians-triangle').each(function (md) {
        const isConn = hoverConns.connectedMagicians.has(md.mtid);
        d3.select(this)
          .attr('opacity', isConn ? 0.7 : 0.06)
          .style('pointer-events', isConn ? 'all' : 'none');
      });
      if (magCrossRefG) {
        magCrossRefG.selectAll('.magicians-ref-edge').each(function (md) {
          const show = hoverConns.connectedMagicians.has(md.mtid) && (md.topicId == d.id || connected.has(Number(md.topicId)));
          d3.select(this).attr('stroke-opacity', show ? 0.5 : 0.01);
        });
      }
    }
  } else {
    hideTooltip();
    hoverEntity(null);

    // If pinned, don't touch the display — it stays locked
    if (getState().pinnedEntity) return;

    filterTimeline();
  }
}

// --- Filtering ---

function filterTimeline() {
  if (!circleG) return;

  // If an entity is pinned, re-apply pinned highlight instead of normal filtering
  const pinSt = getState();
  if (pinSt.pinnedEntity) {
    applyPinnedHighlight();
    return;
  }

  clearPinOverlay();

  const st = getState();

  // If lineage is active, defer to lineage display
  if (st.lineageActive && st.lineageSet.size > 0) {
    applyLineageTimeline();
    return;
  }

  const hasActiveFilter = st.activeThread || st.activeAuthor || st.activeCategory || st.activeTag;

  // Pre-compute academic name aliases for author filter (ethresearch username → paper/EIP names)
  let authorAcademicNames = null;
  if (st.activeAuthor) {
    const eipInfo = getEips();
    const ethToEip = eipInfo?.authorLinks?.ethToEip || {};
    authorAcademicNames = (ethToEip[st.activeAuthor] || []).map(n => n.toLowerCase());
  }

  // Compute target opacities — influence slider fades minor topics, thread/author filters dim non-matching
  const targetOp = {};
  circleG.selectAll('.topic-circle').each(function (d) {
    const belowThreshold = st.minInfluence > 0 && (d.inf || 0) < st.minInfluence;
    if (belowThreshold && hasActiveFilter) {
      // Below threshold + active filter: fully hidden
      targetOp[d.id] = 0.03;
    } else if (belowThreshold) {
      // Below threshold only: lightly faded (visible but subtle, matches V1 minor topics)
      targetOp[d.id] = d.mn ? 0.25 : 0.35;
    } else if (hasActiveFilter) {
      const passesFilter = (!st.activeThread || d.th === st.activeThread) &&
        (!st.activeAuthor || d.a === st.activeAuthor) &&
        (!st.activeCategory || d.cat === st.activeCategory) &&
        (!st.activeTag || (d.tg || []).includes(st.activeTag));
      targetOp[d.id] = passesFilter ? 0.85 : 0.08;
    } else {
      targetOp[d.id] = d.mn ? 0.45 : 0.7;
    }
  });

  circleG.selectAll('.topic-circle')
    .style('pointer-events', d => targetOp[d.id] > 0.15 ? 'all' : 'none')
    .transition().duration(200)
    .attr('opacity', d => targetOp[d.id])
    .attr('r', d => rScale(d.inf));

  if (edgeG) {
    edgeG.selectAll('.edge-line')
      .attr('stroke', '#556')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', e => {
        const sT = topicMap[e.source];
        const tT = topicMap[e.target];
        if (!hasActiveFilter) {
          // No filter active: show all edges at default opacity
          // Slightly fade edges involving below-threshold topics
          const sBelowThresh = st.minInfluence > 0 && (sT?.inf || 0) < st.minInfluence;
          const tBelowThresh = st.minInfluence > 0 && (tT?.inf || 0) < st.minInfluence;
          return (sBelowThresh || tBelowThresh) ? 0.02 : 0.06;
        }
        // Active filter: highlight matching edges
        if (sT && tT && topicMatchesFilter(sT, st) && topicMatchesFilter(tT, st)) return 0.25;
        return 0.01;
      })
      .attr('marker-end', 'url(#arrow-default)');
  }

  syncLabelsFromOpMap(targetOp);

  // --- Filter EIP squares ---
  if (eipLayerG && eipLayerBuilt) {
    eipLayerG.selectAll('.eip-square').each(function (d) {
      const eip = d.eip;
      let show = true;
      // Influence slider
      if (st.minInfluence > 0 && (eip.inf || 0) < st.minInfluence) show = false;
      if (hasActiveFilter && show) {
        if (st.activeThread && eip.th !== st.activeThread) show = false;
        // Author filter: resolve ethresearch username → academic names via authorLinks
        if (st.activeAuthor && show) {
          if (authorAcademicNames && authorAcademicNames.length > 0) {
            const eipAuthors = (eip.au || []).map(a => (a || '').toLowerCase());
            if (!authorAcademicNames.some(name => eipAuthors.some(ea => ea === name))) show = false;
          } else {
            show = false;
          }
        }
      }
      d3.select(this)
        .attr('fill-opacity', show ? 0.5 : 0.05)
        .attr('stroke-opacity', show ? 0.8 : 0.05)
        .style('pointer-events', show ? 'all' : 'none');
    });
    if (eipCrossRefG) {
      eipCrossRefG.selectAll('.cross-ref-edge')
        .attr('stroke-opacity', hasActiveFilter ? 0.03 : 0.12);
    }
  }

  // --- Filter paper diamonds + citation edges ---
  // Like v1: first check filter criteria, then take top N by influence from passing papers
  if (paperLayerG && paperLayerBuilt) {
    const mode = st.paperLayerMode || 'focus';
    const limit = PAPER_LAYER_LIMITS[mode] || 200;

    // Phase 1: collect papers that pass all filters
    const passing = [];
    paperLayerG.selectAll('.paper-diamond').each(function (d) {
      const p = d.paper;
      let pass = true;
      if (st.minInfluence > 0 && (p.inf || 0) < st.minInfluence) pass = false;
      if (hasActiveFilter && pass) {
        if (st.activeThread && p.th !== st.activeThread) pass = false;
        if (st.activeAuthor && pass) {
          if (authorAcademicNames && authorAcademicNames.length > 0) {
            const paperAuthors = (p.a || []).map(a => (a || '').toLowerCase());
            if (!authorAcademicNames.some(name => paperAuthors.some(pa => pa === name || pa.includes(name) || name.includes(pa)))) pass = false;
          } else {
            pass = false;
          }
        }
      }
      if (pass) passing.push({ el: this, p });
    });

    // Phase 2: sort by influence, take top N → visible set
    passing.sort((a, b) => (b.p.inf || 0) - (a.p.inf || 0));
    const visiblePaperIds = new Set(passing.slice(0, limit).map(x => x.p.id));

    // Phase 3: apply visibility
    const curX = xScale || xScaleOrig;
    paperLayerG.selectAll('.paper-diamond').each(function (d) {
      const show = visiblePaperIds.has(d.paper.id);
      d3.select(this)
        .attr('fill-opacity', show ? 0.35 : 0.02)
        .attr('stroke-opacity', show ? 0.5 : 0.02)
        .attr('d', diamondPath(curX(d.date), d.y, d.r))
        .attr('stroke-width', 0.5)
        .attr('stroke', d.color || '#555');
    });
    paperLayerG.selectAll('.paper-hit').each(function (d) {
      const show = visiblePaperIds.has(d.paper.id);
      d3.select(this).style('pointer-events', show ? 'all' : 'none');
    });

    // Filter citation edges: both endpoints must be visible
    if (paperCiteG) {
      paperCiteG.selectAll('.paper-cite-edge').each(function (d) {
        const show = visiblePaperIds.has(d.srcId) && visiblePaperIds.has(d.tgtId);
        d3.select(this)
          .attr('stroke-opacity', show ? 0.12 : 0.008)
          .attr('stroke-width', show ? 0.6 : 0.3);
      });
    }
  }

  // --- Filter magicians triangles ---
  if (magLayerG && magLayerBuilt) {
    filterMagiciansLayer();
  }
}

// --- Pinned highlight ---
// When a node is single-clicked, dim everything except the pinned entity and its connections.

function buildPinnedConnections(pinned) {
  const connectedTopics = new Set();
  const connectedEips = new Set();
  const connectedPapers = new Set();
  const connectedMagicians = new Set();

  const indexes = getCoreIndexes();
  const core = getCore();
  const paperData = getPapers();
  const graphData = getGraph();
  const graphIdx = getGraphIndexes();

  if (pinned.type === 'topic') {
    connectedTopics.add(pinned.id);
    // Adjacent topics via citation edges
    const adj = indexes?.topicEdgeIndex?.[String(pinned.id)];
    if (adj) adj.forEach(id => connectedTopics.add(id));
    // EIPs mentioned by this topic (union of eips + primary eips)
    const topic = core?.topics?.[pinned.id];
    if (topic) {
      for (const eNum of (topic.eips || []).concat(topic.peips || [])) connectedEips.add(Number(eNum));
    }
    // Magicians linked to this topic or its EIPs
    if (graphIdx?.topicToMagiciansRefs?.[String(pinned.id)]) {
      graphIdx.topicToMagiciansRefs[String(pinned.id)].forEach(mid => connectedMagicians.add(mid));
    }
    for (const eNum of connectedEips) {
      if (graphIdx?.eipToMagiciansRefs?.[String(eNum)]) {
        graphIdx.eipToMagiciansRefs[String(eNum)].forEach(mid => connectedMagicians.add(mid));
      }
    }
    // Papers: EIP overlap + title keyword + thread matching (v1-aligned scoring)
    if (paperData?.papers) {
      const topicKW = extractKeywords(topic?.t);
      const topicThread = topic?.th;
      const scored = [];
      for (const [pid, p] of Object.entries(paperData.papers)) {
        let score = 0;
        // EIP overlap (strongest signal)
        for (const peip of (p.eq || [])) {
          if (connectedEips.has(Number(peip))) { score += 3.0; break; }
        }
        // Title keyword overlap (+0.65 per shared keyword)
        if (topicKW.size > 0) {
          const paperKW = extractKeywords(p.t);
          const overlap = keywordOverlap(topicKW, paperKW);
          if (overlap > 0) score += overlap * 0.65;
        }
        // Thread match (+1.0)
        if (topicThread && p.th === topicThread) score += 1.0;
        if (score >= 1.0) scored.push({ id: pid, score, inf: p.inf || 0 });
      }
      scored.sort((a, b) => b.score - a.score || b.inf - a.inf);
      for (const s of scored.slice(0, 12)) connectedPapers.add(s.id);
    }

  } else if (pinned.type === 'eip') {
    connectedEips.add(Number(pinned.id));
    // Topics mentioning this EIP
    const eipTopics = indexes?.eipToTopics?.[String(pinned.id)];
    if (eipTopics) eipTopics.forEach(tid => connectedTopics.add(tid));
    // Magicians linked to this EIP
    if (graphIdx?.eipToMagiciansRefs?.[String(pinned.id)]) {
      graphIdx.eipToMagiciansRefs[String(pinned.id)].forEach(mid => connectedMagicians.add(mid));
    }
    if (graphData?.magiciansTopics) {
      for (const [mtid, mt] of Object.entries(graphData.magiciansTopics)) {
        if ((mt.eips || []).includes(Number(pinned.id)) || (mt.eips || []).includes(String(pinned.id))) {
          connectedMagicians.add(Number(mtid));
        }
      }
    }
    // EIPs connected via requires edges
    const eipData = getEips();
    if (eipData?.eipCatalog) {
      const cat = eipData.eipCatalog[String(pinned.id)];
      if (cat?.req) for (const r of cat.req) connectedEips.add(Number(r));
      // EIPs that require this one
      for (const [eNum, e] of Object.entries(eipData.eipCatalog)) {
        if ((e.req || []).includes(Number(pinned.id)) || (e.req || []).includes(String(pinned.id))) {
          connectedEips.add(Number(eNum));
        }
      }
    }
    // Papers: EIP match + title keyword + thread matching (v1-aligned scoring)
    if (paperData?.papers) {
      const eipData2 = getEips();
      const eipTitle = eipData2?.eipCatalog?.[String(pinned.id)]?.t || '';
      const eipKW = extractKeywords(eipTitle);
      const eipThread = eipData2?.eipCatalog?.[String(pinned.id)]?.th;
      const scored = [];
      for (const [pid, p] of Object.entries(paperData.papers)) {
        let score = 0;
        for (const peip of (p.eq || [])) {
          if (Number(peip) === Number(pinned.id)) { score += 5.0; break; }
        }
        if (eipKW.size > 0) {
          const paperKW = extractKeywords(p.t);
          const overlap = keywordOverlap(eipKW, paperKW);
          if (overlap > 0) score += overlap * 0.65;
        }
        if (eipThread && p.th === eipThread) score += 1.0;
        if (score >= 1.0) scored.push({ id: pid, score, inf: p.inf || 0 });
      }
      scored.sort((a, b) => b.score - a.score || b.inf - a.inf);
      for (const s of scored.slice(0, 12)) connectedPapers.add(s.id);
    }

  } else if (pinned.type === 'paper') {
    connectedPapers.add(pinned.id);
    // Citation neighbors via paperGraph
    if (paperData?.paperGraph?.edges) {
      for (const edge of paperData.paperGraph.edges) {
        if (edge.source === pinned.id) connectedPapers.add(edge.target);
        else if (edge.target === pinned.id) connectedPapers.add(edge.source);
      }
    }
    // EIPs from paper's eq field
    const paper = paperData?.papers?.[pinned.id];
    if (paper) {
      for (const eNum of (paper.eq || [])) connectedEips.add(Number(eNum));
    }
    // Topics: EIP-based + keyword matching
    for (const eNum of connectedEips) {
      const eipTopics = indexes?.eipToTopics?.[String(eNum)];
      if (eipTopics) eipTopics.forEach(tid => connectedTopics.add(tid));
    }
    // Keyword-match topics to paper title (v1-aligned scoring)
    const paper2 = paperData?.papers?.[pinned.id];
    if (paper2 && core?.topics) {
      const paperKW = extractKeywords(paper2.t);
      if (paperKW.size > 0) {
        const scored = [];
        for (const [tid, t] of Object.entries(core.topics)) {
          if (connectedTopics.has(Number(tid))) continue;
          const topicKW = extractKeywords(t.t);
          const overlap = keywordOverlap(paperKW, topicKW);
          let score = 0;
          if (overlap > 0) score += overlap * 0.65;
          if (paper2.th && t.th === paper2.th) score += 1.0;
          if (score >= 1.0) scored.push({ id: Number(tid), score, inf: t.inf || 0 });
        }
        scored.sort((a, b) => b.score - a.score || b.inf - a.inf);
        for (const s of scored.slice(0, 12)) connectedTopics.add(s.id);
      }
    }
    // Magicians linked to connected EIPs
    for (const eNum of connectedEips) {
      if (graphIdx?.eipToMagiciansRefs?.[String(eNum)]) {
        graphIdx.eipToMagiciansRefs[String(eNum)].forEach(mid => connectedMagicians.add(mid));
      }
    }

  } else if (pinned.type === 'magicians') {
    connectedMagicians.add(pinned.id);
    // Connected ethresearch topics via mt.er
    const mt = graphData?.magiciansTopics?.[String(pinned.id)];
    if (mt) {
      for (const tid of (mt.er || [])) connectedTopics.add(Number(tid));
      // EIPs from magicians topic
      for (const eNum of (mt.eips || [])) connectedEips.add(Number(eNum));
    }
    // EIPs via magiciansToEips index
    if (graphIdx?.magiciansToEips?.[String(pinned.id)]) {
      for (const eNum of graphIdx.magiciansToEips[String(pinned.id)]) {
        connectedEips.add(Number(eNum));
      }
    }
    // Topics mentioning connected EIPs
    for (const eNum of connectedEips) {
      const eipTopics = indexes?.eipToTopics?.[String(eNum)];
      if (eipTopics) eipTopics.forEach(tid => connectedTopics.add(tid));
    }
    // Papers mentioning connected EIPs
    if (paperData?.papers && connectedEips.size > 0) {
      for (const [pid, p] of Object.entries(paperData.papers)) {
        for (const peip of (p.eq || [])) {
          if (connectedEips.has(Number(peip))) { connectedPapers.add(pid); break; }
        }
      }
    }
  }

  return { connectedTopics, connectedEips, connectedPapers, connectedMagicians };
}

function applyPinnedHighlight() {
  const st = getState();
  const pinned = st.pinnedEntity;
  if (!pinned) { clearPinOverlay(); filterTimeline(); return; }

  const { connectedTopics, connectedEips, connectedPapers, connectedMagicians } = buildPinnedConnections(pinned);

  // Dim topic circles
  if (circleG) {
    circleG.selectAll('.topic-circle').each(function (d) {
      const isPinned = pinned.type === 'topic' && d.id === pinned.id;
      const isConnected = connectedTopics.has(d.id);
      const op = isPinned ? 1.0 : isConnected ? 0.8 : 0.06;
      d3.select(this).attr('opacity', op).style('pointer-events', op > 0.05 ? 'all' : 'none');
    });
  }

  // Dim edges
  if (edgeG) {
    edgeG.selectAll('.edge-line').each(function (e) {
      const touching = connectedTopics.has(e.source) && connectedTopics.has(e.target);
      const direct = (pinned.type === 'topic') && (e.source === pinned.id || e.target === pinned.id);
      d3.select(this)
        .attr('stroke-opacity', direct ? 0.6 : touching ? 0.08 : 0.01)
        .attr('stroke-width', direct ? 2 : 1)
        .attr('stroke', direct ? '#88aaff' : '#556')
        .attr('marker-end', direct ? 'url(#arrow-highlight)' : 'url(#arrow-default)');
    });
  }

  // Dim labels
  if (labelG) {
    labelG.selectAll('.topic-label').each(function (d) {
      const op = connectedTopics.has(d.id) ? 0.9 : 0.04;
      d3.select(this).attr('opacity', op);
    });
  }

  // Dim EIP squares
  if (eipLayerG && eipLayerBuilt) {
    eipLayerG.selectAll('.eip-square').each(function (d) {
      const isPinned = pinned.type === 'eip' && Number(d.num) === Number(pinned.id);
      const isConnected = connectedEips.has(Number(d.num));
      d3.select(this)
        .attr('fill-opacity', isPinned ? 0.8 : isConnected ? 0.5 : 0.06)
        .attr('stroke-opacity', isPinned ? 1 : isConnected ? 0.6 : 0.06)
        .style('pointer-events', (isPinned || isConnected) ? 'all' : 'none');
    });
    // Show cross-ref edges touching connected entities
    if (eipCrossRefG) {
      eipCrossRefG.selectAll('.cross-ref-edge').each(function (d) {
        const eipNum = d?.eipNum;
        const topicId = d?.topicId;
        const show = connectedEips.has(Number(eipNum)) && connectedTopics.has(Number(topicId));
        d3.select(this).attr('stroke-opacity', show ? 0.5 : 0.02);
      });
    }
  }

  // Dim paper diamonds — connected papers get boosted size + opacity
  if (paperLayerG && paperLayerBuilt) {
    const curX = xScale || xScaleOrig;
    paperLayerG.selectAll('.paper-diamond').each(function (d) {
      const isPinned = pinned.type === 'paper' && d.paper.id === pinned.id;
      const isConnected = connectedPapers.has(d.paper.id);
      const el = d3.select(this);
      el.attr('fill-opacity', isPinned ? 0.85 : isConnected ? 0.8 : 0.04)
        .attr('stroke-opacity', isPinned ? 1 : isConnected ? 0.9 : 0.04);
      // Boost size for connected papers (min 7px, scale up by 1.6x)
      if (isPinned || isConnected) {
        const boosted = Math.max(7, d.r * 1.6);
        el.attr('d', diamondPath(curX(d.date), d.y, boosted))
          .attr('stroke-width', 1.5)
          .attr('stroke', '#fff');
      } else {
        el.attr('d', diamondPath(curX(d.date), d.y, d.r))
          .attr('stroke-width', 0.5)
          .attr('stroke', d.color || '#555');
      }
    });
    paperLayerG.selectAll('.paper-hit').each(function (d) {
      const isPinned = pinned.type === 'paper' && d.paper.id === pinned.id;
      const isConnected = connectedPapers.has(d.paper.id);
      d3.select(this).style('pointer-events', (isPinned || isConnected) ? 'all' : 'none');
    });
    // Show citation edges where both endpoints are connected
    if (paperCiteG) {
      paperCiteG.selectAll('.paper-cite-edge').each(function (d) {
        const direct = (pinned.type === 'paper') && (d.srcId === pinned.id || d.tgtId === pinned.id);
        const both = connectedPapers.has(d.srcId) && connectedPapers.has(d.tgtId);
        d3.select(this).attr('stroke-opacity', direct ? 0.5 : both ? 0.15 : 0.01);
      });
    }
  }

  // Dim magicians triangles
  if (magLayerG && magLayerBuilt) {
    magLayerG.selectAll('.magicians-triangle').each(function (d) {
      const isPinned = pinned.type === 'magicians' && d.mtid === pinned.id;
      const isConnected = connectedMagicians.has(d.mtid);
      d3.select(this)
        .attr('opacity', isPinned ? 1.0 : isConnected ? 0.7 : 0.08)
        .style('pointer-events', (isPinned || isConnected) ? 'all' : 'none');
    });
    // Show magicians cross-ref edges touching connected entities
    if (magCrossRefG) {
      magCrossRefG.selectAll('.magicians-ref-edge').each(function (d) {
        const show = connectedMagicians.has(d.mtid) && connectedTopics.has(Number(d.topicId));
        d3.select(this).attr('stroke-opacity', show ? 0.5 : 0.02);
      });
    }
  }

  // Draw cross-entity edges and labels
  drawPinOverlay(pinned, connectedTopics, connectedEips, connectedPapers, connectedMagicians);
}

function clearPinOverlay() {
  if (pinOverlayG) pinOverlayG.selectAll('*').remove();
}

function drawPinOverlay(pinned, topics, eips, papers, magicians) {
  clearPinOverlay();
  if (!zoomG) return;
  if (!pinOverlayG) pinOverlayG = zoomG.append('g').attr('class', 'pin-overlay');
  // Ensure overlay is on top
  pinOverlayG.raise();

  const curX = xScale || xScaleOrig;

  // Collect positions of all connected entities
  const positions = {}; // key → { x, y, title, type }

  // Pinned entity position
  let pinnedPos = null;
  if (pinned.type === 'topic') {
    const t = topicMap[pinned.id];
    if (t) pinnedPos = { x: curX(t._date), y: t._yPos, title: t.t, date: t._date, r: rScale(t.inf) };
  } else if (pinned.type === 'eip' && eipLayerG) {
    eipLayerG.selectAll('.eip-square').each(function (d) {
      if (Number(d.num) === Number(pinned.id)) {
        pinnedPos = { x: curX(d.date), y: d.y, title: 'EIP-' + d.num + ': ' + (d.title || ''), date: d.date, r: d.size / 2 };
      }
    });
  } else if (pinned.type === 'paper' && paperLayerG) {
    paperLayerG.selectAll('.paper-diamond').each(function (d) {
      if (d.paper.id === pinned.id) {
        pinnedPos = { x: curX(d.date), y: d.y, title: d.paper.t || '', date: d.date, r: d.r };
      }
    });
  } else if (pinned.type === 'magicians' && magLayerG) {
    magLayerG.selectAll('.magicians-triangle').each(function (d) {
      if (d.mtid === pinned.id) {
        pinnedPos = { x: curX(d.date), y: d.y, title: d.mt.t || '', date: d.date, r: d.r };
      }
    });
  }
  if (!pinnedPos) return;

  // --- Draw cross-entity edges ---
  // Topic ↔ Paper edges
  if (paperLayerBuilt && papers.size > 0 && pinned.type !== 'paper') {
    paperLayerG.selectAll('.paper-diamond').each(function (d) {
      if (!papers.has(d.paper.id)) return;
      pinOverlayG.append('line')
        .attr('class', 'pin-edge')
        .attr('x1', pinnedPos.x).attr('y1', pinnedPos.y)
        .attr('x2', curX(d.date)).attr('y2', d.y)
        .attr('stroke', '#8eb8ff').attr('stroke-opacity', 0.5)
        .attr('stroke-width', 1.2).attr('stroke-dasharray', '4 2')
        .datum({ x1Date: pinnedPos.date, y1: pinnedPos.y, x2Date: d.date, y2: d.y });
    });
  }
  if (pinned.type === 'paper') {
    // Paper → Topic edges
    if (circleG && topics.size > 0) {
      circleG.selectAll('.topic-circle').each(function (d) {
        if (!topics.has(d.id)) return;
        pinOverlayG.append('line')
          .attr('class', 'pin-edge')
          .attr('x1', pinnedPos.x).attr('y1', pinnedPos.y)
          .attr('x2', curX(d._date)).attr('y2', d._yPos)
          .attr('stroke', '#8eb8ff').attr('stroke-opacity', 0.5)
          .attr('stroke-width', 1.2).attr('stroke-dasharray', '4 2')
          .datum({ x1Date: pinnedPos.date, y1: pinnedPos.y, x2Date: d._date, y2: d._yPos });
      });
    }
    // Paper → EIP edges
    if (eipLayerBuilt && eips.size > 0) {
      eipLayerG.selectAll('.eip-square').each(function (d) {
        if (!eips.has(Number(d.num))) return;
        pinOverlayG.append('line')
          .attr('class', 'pin-edge')
          .attr('x1', pinnedPos.x).attr('y1', pinnedPos.y)
          .attr('x2', curX(d.date)).attr('y2', d.y)
          .attr('stroke', '#94c3ff').attr('stroke-opacity', 0.5)
          .attr('stroke-width', 1.2).attr('stroke-dasharray', '4 2')
          .datum({ x1Date: pinnedPos.date, y1: pinnedPos.y, x2Date: d.date, y2: d.y });
      });
    }
  }

  // --- Draw labels on pinned entity + neighbors ---
  const labelEntries = []; // { x, y, title, isPinned }

  // Pinned entity label
  labelEntries.push({ x: pinnedPos.x, y: pinnedPos.y, r: pinnedPos.r || 5, title: pinnedPos.title, isPinned: true });

  // Connected topic labels (top 12 by influence)
  const topicLabels = [];
  if (circleG) {
    circleG.selectAll('.topic-circle').each(function (d) {
      if (!topics.has(d.id)) return;
      if (pinned.type === 'topic' && d.id === pinned.id) return; // skip pinned itself
      topicLabels.push({ x: curX(d._date), y: d._yPos, r: rScale(d.inf), title: d.t, inf: d.inf, date: d._date });
    });
  }
  topicLabels.sort((a, b) => b.inf - a.inf);
  for (const tl of topicLabels.slice(0, 12)) labelEntries.push({ ...tl, isPinned: false });

  // Connected EIP labels (top 8)
  const eipLabels = [];
  if (eipLayerBuilt && eipLayerG) {
    eipLayerG.selectAll('.eip-square').each(function (d) {
      if (!eips.has(Number(d.num))) return;
      if (pinned.type === 'eip' && Number(d.num) === Number(pinned.id)) return;
      eipLabels.push({ x: curX(d.date), y: d.y, r: d.size / 2, title: 'EIP-' + d.num, inf: d.inf || 0, date: d.date });
    });
  }
  eipLabels.sort((a, b) => b.inf - a.inf);
  for (const el of eipLabels.slice(0, 8)) labelEntries.push({ ...el, isPinned: false });

  // Connected paper labels (top 6)
  const paperLabels = [];
  if (paperLayerBuilt && paperLayerG) {
    paperLayerG.selectAll('.paper-diamond').each(function (d) {
      if (!papers.has(d.paper.id)) return;
      if (pinned.type === 'paper' && d.paper.id === pinned.id) return;
      paperLabels.push({ x: curX(d.date), y: d.y, r: d.r, title: d.paper.t || '', inf: d.paper.inf || 0, date: d.date });
    });
  }
  paperLabels.sort((a, b) => b.inf - a.inf);
  for (const pl of paperLabels.slice(0, 6)) labelEntries.push({ ...pl, isPinned: false });

  // Collision avoidance: remove labels too close to others
  const placed = [];
  const MIN_DIST_SQ = 35 * 35; // 35px minimum between labels
  for (const entry of labelEntries) {
    const tooClose = placed.some(p => {
      const dx = entry.x - p.x, dy = entry.y - p.y;
      return dx * dx + dy * dy < MIN_DIST_SQ;
    });
    if (tooClose && !entry.isPinned) continue;
    placed.push(entry);

    const txt = entry.title.length > 35 ? entry.title.slice(0, 34) + '\u2026' : entry.title;
    pinOverlayG.append('text')
      .attr('class', 'pin-label')
      .attr('x', entry.x + (entry.r || 5) + 4)
      .attr('y', entry.y + 3)
      .attr('fill', entry.isPinned ? '#fff' : '#ccc')
      .attr('font-size', entry.isPinned ? 11 : 9)
      .attr('font-weight', entry.isPinned ? 'bold' : 'normal')
      .attr('pointer-events', 'none')
      .attr('opacity', entry.isPinned ? 1.0 : 0.85)
      .text(txt)
      .datum({ date: entry.date || pinnedPos.date, y: entry.y, r: entry.r || 5 });
  }
}

function updatePinOverlayZoom(newX) {
  if (!pinOverlayG) return;
  pinOverlayG.selectAll('.pin-edge').each(function (d) {
    d3.select(this)
      .attr('x1', newX(d.x1Date)).attr('x2', newX(d.x2Date));
  });
  pinOverlayG.selectAll('.pin-label').each(function (d) {
    d3.select(this).attr('x', newX(d.date) + (d.r || 5) + 4);
  });
}

// --- Selection ---

function onSelectionChanged({ current }) {
  if (!circleG) return;
  // When detail opens via double-click, also apply the pinned highlight
  if (current) {
    applyPinnedHighlight();
  }
  circleG.selectAll('.topic-circle')
    .attr('stroke-width', function (d) {
      return current?.type === 'topic' && current?.id === d.id ? 3 : (d.mn ? 1 : 0.5);
    });
}

// --- Lineage ---

function onLineageChanged({ active, nodeSet, edgeSet }) {
  if (active && nodeSet.size > 0) {
    applyLineageTimeline();
  } else {
    filterTimeline();
  }
}

function applyLineageTimeline() {
  const st = getState();
  const lineageSet = st.lineageSet;
  const lineageEdgeSet = st.lineageEdgeSet;

  if (!circleG || !edgeG) return;

  circleG.selectAll('.topic-circle')
    .attr('opacity', d => lineageSet.has(d.id) ? 1 : 0.04)
    .style('pointer-events', d => lineageSet.has(d.id) ? 'all' : 'none')
    .attr('r', d => lineageSet.has(d.id) ? rScale(d.inf) * 1.2 : rScale(d.inf));

  edgeG.selectAll('.edge-line')
    .attr('stroke', e => {
      const key = e.source + '->' + e.target;
      const keyR = e.target + '->' + e.source;
      return (lineageEdgeSet.has(key) || lineageEdgeSet.has(keyR)) ? '#88aaff' : '#556';
    })
    .attr('stroke-opacity', e => {
      const key = e.source + '->' + e.target;
      const keyR = e.target + '->' + e.source;
      return (lineageEdgeSet.has(key) || lineageEdgeSet.has(keyR)) ? 0.6 : 0.01;
    })
    .attr('stroke-width', e => {
      const key = e.source + '->' + e.target;
      const keyR = e.target + '->' + e.source;
      return (lineageEdgeSet.has(key) || lineageEdgeSet.has(keyR)) ? 2 : 1;
    })
    .attr('marker-end', e => {
      const key = e.source + '->' + e.target;
      const keyR = e.target + '->' + e.source;
      return (lineageEdgeSet.has(key) || lineageEdgeSet.has(keyR)) ? 'url(#arrow-lineage)' : 'url(#arrow-default)';
    });

  syncLabels();
}

// --- Milestones ---

function onMilestonesChanged({ visible }) {
  if (!milestoneG) return;
  milestoneG.selectAll('.milestone-marker')
    .style('display', visible ? null : 'none');
}

// --- Reset ---

function onReset() {
  if (svg && zoomBehavior) {
    svg.transition().duration(300).call(zoomBehavior.transform, d3.zoomIdentity);
  }
  // Remove EIP layer on reset
  if (eipLayerG) { eipLayerG.selectAll('*').remove(); eipLayerBuilt = false; }
  if (eipCrossRefG) eipCrossRefG.selectAll('*').remove();
  // Remove paper layer on reset
  if (paperCiteG) paperCiteG.selectAll('*').remove();
  if (paperLayerG) { paperLayerG.selectAll('*').remove(); paperLayerBuilt = false; paperLayerMode = null; }
  // Remove magicians layer on reset
  if (magLayerG) { magLayerG.selectAll('*').remove(); magLayerBuilt = false; }
  if (magCrossRefG) { magCrossRefG.selectAll('*').remove(); }
  // Remove pin overlay on reset
  clearPinOverlay();
  // Restore default influence threshold and sync slider
  if (defaultInfluenceThreshold > 0) {
    setFilters({ minInfluence: defaultInfluenceThreshold });
    const slider = document.getElementById('inf-slider');
    const maxInf = d3.max(Object.values(topicMap), t => t.inf) || 1;
    const pct = Math.round(defaultInfluenceThreshold / maxInf * 100);
    if (slider) {
      slider.value = pct;
      const label = document.getElementById('inf-slider-label');
      if (label) label.textContent = pct === 0 ? '0%' : pct + '%';
    }
  }
  filterTimeline();
}

// --- EIP layer on timeline ---

async function onContentChanged({ key }) {
  if (key === 'showPosts') {
    const st = getState();
    const show = st.showPosts;
    if (circleG) {
      circleG.selectAll('.topic-circle')
        .style('display', show ? null : 'none')
        .style('pointer-events', show ? null : 'none');
    }
    if (labelG) {
      labelG.selectAll('.topic-label')
        .style('display', show ? null : 'none');
    }
    if (edgeG) {
      edgeG.selectAll('.edge-line')
        .style('display', show ? null : 'none');
    }
    if (milestoneG) {
      milestoneG.selectAll('.milestone-marker')
        .style('display', (show && st.milestonesVisible) ? null : 'none');
    }
    // Also hide/show magicians cross-ref edges (they connect to topics)
    if (magCrossRefG) {
      magCrossRefG.selectAll('.magicians-ref-edge')
        .style('display', show ? null : 'none');
    }
  }
  if (key === 'showEips') {
    const st = getState();
    if (st.showEips) {
      await loadEips();
      if (getState().showEips) buildEipLayer();
    } else {
      removeEipLayer();
    }
  }
  if (key === 'showMagicians') {
    const st = getState();
    if (st.showMagicians) {
      await loadGraph();
      if (getState().showMagicians) buildMagiciansLayer();
    } else {
      removeMagiciansLayer();
    }
  }
  if (key === 'showPapers') {
    const st = getState();
    if (st.showPapers) {
      await loadPapers();
      await loadEips(); // Ensure authorLinks available for author filtering
      if (getState().showPapers) buildPaperLayer();
    } else {
      removePaperLayer();
    }
  }
}

function buildEipLayer() {
  if (!zoomG || !xScaleOrig || eipLayerBuilt) return;
  const eipData = getEips();
  if (!eipData?.eipCatalog) return;

  // Build connected EIP set from eipGraph (in eips.json, no need for graph.json)
  const connectedEips = new Set();
  const eipToTopicMap = {};
  for (const edge of (eipData.eipGraph?.edges || [])) {
    if (edge.type === 'eip_topic') {
      const eipNum = String(edge.source).replace('eip_', '');
      connectedEips.add(eipNum);
      if (!eipToTopicMap[eipNum]) eipToTopicMap[eipNum] = [];
      eipToTopicMap[eipNum].push(edge.target);
    }
  }

  // Create groups if needed
  if (!eipLayerG) eipLayerG = zoomG.append('g').attr('class', 'eip-layer');
  if (!eipCrossRefG) eipCrossRefG = zoomG.append('g').attr('class', 'eip-crossref-layer');

  const st = getState();
  const showAll = st.eipVisibilityMode === 'all';

  // Position EIPs in the lane of their thread (above center of the lane)
  const catalog = eipData.eipCatalog;
  const eipEntries = [];
  for (const [num, eip] of Object.entries(catalog)) {
    if (!eip.cr) continue;
    // Filter by connected/all mode
    if (!showAll && !connectedEips.has(num)) continue;
    const date = new Date(eip.cr);
    if (isNaN(date)) continue;
    eipEntries.push({ num, eip, date });
  }

  // Draw EIP squares
  eipEntries.forEach(({ num, eip, date }) => {
    const th = eip.th;
    const lane = (th && laneIdx[th] !== undefined) ? laneIdx[th] : laneIdx['_other'] ?? laneOrder.length - 1;
    const yBase = topicLaneY0 + lane * laneH + laneH * 0.08;
    const y = yBase + (hashCode(Number(num)) % 100) / 100 * (laneH * 0.3);
    const size = 8 + Math.min(8, (eip.inf || 0) * 12);
    const statusColor = EIP_STATUS_COLORS[eip.s] || '#555';

    const sq = eipLayerG.append('rect')
      .attr('class', 'eip-square')
      .attr('x', xScaleOrig(date) - size / 2)
      .attr('y', y - size / 2)
      .attr('width', size)
      .attr('height', size)
      .attr('rx', 3)
      .attr('fill', statusColor)
      .attr('fill-opacity', 0.5)
      .attr('stroke', statusColor)
      .attr('stroke-opacity', 0.8)
      .attr('stroke-width', 0.8)
      .datum({ num, eip, date, y, size, type: 'eip' });
    let eipClickTimer = null;
    sq.on('click', function (ev, d) {
        ev.stopPropagation();
        if (eipClickTimer) {
          clearTimeout(eipClickTimer); eipClickTimer = null;
          selectEntity({ type: 'eip', id: d.num });
          return;
        }
        eipClickTimer = setTimeout(() => {
          eipClickTimer = null;
          pinEntity({ type: 'eip', id: d.num });
          applyPinnedHighlight();
        }, 220);
      })
      .on('mouseover', function (ev, d) {
        showEipTooltip(ev, d);
      })
      .on('mouseout', function () { hideTooltip(); });
  });

  // Draw cross-reference edges (dashed) between EIP squares and their related topic circles
  eipLayerG.selectAll('.eip-square').each(function (d) {
    const topicIds = eipToTopicMap[d.num] || [];
    for (const tid of topicIds) {
      const topic = topicMap[tid];
      if (!topic || topic._yPos === undefined) continue;
      eipCrossRefG.append('line')
        .attr('class', 'cross-ref-edge')
        .attr('x1', xScaleOrig(d.date))
        .attr('y1', d.y)
        .attr('x2', xScaleOrig(topic._date))
        .attr('y2', topic._yPos)
        .attr('stroke', '#7788cc')
        .attr('stroke-opacity', 0.12)
        .attr('stroke-width', 0.5)
        .datum({ eipNum: d.num, topicId: tid, eipDate: d.date, topicDate: topic._date, eipY: d.y, topicY: topic._yPos });
    }
  });

  eipLayerBuilt = true;
  // Apply current zoom
  if (xScale !== xScaleOrig) {
    updateEipLayerZoom(xScale);
  }
  // Apply current filters to newly built layer
  filterTimeline();
}

function removeEipLayer() {
  if (eipLayerG) eipLayerG.selectAll('*').remove();
  if (eipCrossRefG) eipCrossRefG.selectAll('*').remove();
  eipLayerBuilt = false;
}

function updateEipLayerZoom(newX) {
  if (!eipLayerG) return;
  eipLayerG.selectAll('.eip-square')
    .attr('x', d => newX(d.date) - d.size / 2);
  if (eipCrossRefG) {
    eipCrossRefG.selectAll('.cross-ref-edge')
      .attr('x1', d => newX(d.eipDate))
      .attr('x2', d => newX(d.topicDate));
  }
}

function showEipTooltip(ev, d) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const statusColor = EIP_STATUS_COLORS[d.eip.s] || '#555';
  tip.innerHTML = '<strong style="color:' + statusColor + '">EIP-' + d.num + ': ' + escHtml(d.eip.t || '') + '</strong><br>' +
    (d.eip.s || '') + (d.eip.fk ? ' \u00b7 ' + d.eip.fk : '') +
    ' \u00b7 inf: ' + (d.eip.inf || 0).toFixed(2);
  tip.style.display = 'block';
  let x = ev.clientX + 14;
  let y = ev.clientY - 10;
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

// --- Paper layer on timeline ---

function onFiltersChangedPaperMode(changed) {
  if (changed.paperLayerMode) {
    const st = getState();
    if (st.showPapers && paperLayerBuilt) {
      // Mode changed — just re-filter (all papers already built)
      paperLayerMode = st.paperLayerMode || 'focus';
      filterTimeline();
    }
  }
  if (changed.eipVisibilityMode) {
    const st = getState();
    if (st.showEips && eipLayerBuilt) {
      // EIP mode changed — rebuild
      removeEipLayer();
      buildEipLayer();
    }
  }
  if (changed.activeAuthor) {
    // Author filter changed — re-filter is enough since all papers are built
    filterTimeline();
  }
}

function buildPaperLayer() {
  if (!zoomG || !xScaleOrig) return;
  const paperData = getPapers();
  if (!paperData?.papers) return;

  // Build ALL papers as DOM elements (like v1). Visibility controlled by filterTimeline()
  // via PAPER_LAYER_LIMITS — top N by influence from the filtered set are shown.
  const allPapers = Object.values(paperData.papers);

  // Create edge group first (behind diamonds), then diamond group on top
  if (!paperCiteG) paperCiteG = zoomG.append('g').attr('class', 'paper-cite-layer');
  if (!paperLayerG) paperLayerG = zoomG.append('g').attr('class', 'paper-layer');

  // Build position lookup for ALL papers
  const paperPos = {};  // paperId → { date, y, r }
  allPapers.forEach(p => {
    if (!p.y) return;
    const idHash = hashCode(p.id ? p.id.length * 31 + p.id.charCodeAt(0) : 0);
    const dayOffset = idHash % 365;
    const date = new Date(p.y, 0, 1 + dayOffset);
    if (isNaN(date)) return;

    const th = p.th;
    const lane = (th && laneIdx[th] !== undefined) ? laneIdx[th] : laneIdx['_other'] ?? laneOrder.length - 1;
    const yBase = topicLaneY0 + lane * laneH + laneH * 0.6;
    const yRange = laneH * 0.35;
    const y = yBase + (idHash % 100) / 100 * yRange;

    const r = 2 + Math.min(5, (p.inf || 0) * 6);
    paperPos[p.id] = { date, y, r };
  });

  // Draw citation edges from paperGraph
  const pgEdges = paperData.paperGraph?.edges || [];
  for (const edge of pgEdges) {
    const src = paperPos[edge.source];
    const tgt = paperPos[edge.target];
    if (!src || !tgt) continue;
    paperCiteG.append('line')
      .attr('class', 'paper-cite-edge')
      .attr('x1', xScaleOrig(src.date)).attr('y1', src.y)
      .attr('x2', xScaleOrig(tgt.date)).attr('y2', tgt.y)
      .attr('stroke', '#8fb7ef')
      .attr('stroke-opacity', 0.12)
      .attr('stroke-width', 0.6)
      .datum({ srcId: edge.source, tgtId: edge.target, srcDate: src.date, srcY: src.y, tgtDate: tgt.date, tgtY: tgt.y });
  }

  // Draw paper diamonds with invisible hit areas for reliable hover
  for (const [pid, pos] of Object.entries(paperPos)) {
    const p = paperData.papers[pid];
    if (!p) continue;
    const color = p.th ? (THREAD_COLORS[p.th] || '#2f4f77') : '#2f4f77';
    const datum = { paper: p, date: pos.date, y: pos.y, r: pos.r, color, type: 'paper' };

    // Visible diamond
    paperLayerG.append('path')
      .attr('class', 'paper-diamond')
      .attr('d', diamondPath(xScaleOrig(pos.date), pos.y, pos.r))
      .attr('fill', color)
      .attr('fill-opacity', 0.4)
      .attr('stroke', color)
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 0.6)
      .attr('pointer-events', 'none')
      .datum(datum);

    // Invisible hit area on top (min 8px radius for reliable hover)
    const hitR = Math.max(8, pos.r + 3);
    let pClickTimer = null;
    paperLayerG.append('path')
      .attr('class', 'paper-hit')
      .attr('d', diamondPath(xScaleOrig(pos.date), pos.y, hitR))
      .attr('fill', 'transparent')
      .attr('stroke', 'none')
      .attr('pointer-events', 'all')
      .datum(datum)
      .on('click', function (ev, d) {
        ev.stopPropagation();
        if (pClickTimer) {
          clearTimeout(pClickTimer); pClickTimer = null;
          selectEntity({ type: 'paper', id: d.paper.id });
          return;
        }
        pClickTimer = setTimeout(() => {
          pClickTimer = null;
          pinEntity({ type: 'paper', id: d.paper.id });
          applyPinnedHighlight();
        }, 220);
      })
      .on('mouseover', function (ev, d) { showPaperTooltip(ev, d); })
      .on('mouseout', function () { hideTooltip(); });
  }

  paperLayerBuilt = true;
  paperLayerMode = getState().paperLayerMode || 'focus';

  // Apply current zoom
  if (xScale !== xScaleOrig) {
    updatePaperLayerZoom(xScale);
  }
  // Apply current filters to newly built layer
  filterTimeline();
}

function removePaperLayer() {
  if (paperCiteG) paperCiteG.selectAll('*').remove();
  if (paperLayerG) paperLayerG.selectAll('*').remove();
  paperLayerBuilt = false;
  paperLayerMode = null;
}

function updatePaperLayerZoom(newX) {
  if (paperLayerG) {
    paperLayerG.selectAll('.paper-diamond').each(function (d) {
      d3.select(this).attr('d', diamondPath(newX(d.date), d.y, d.r));
    });
    paperLayerG.selectAll('.paper-hit').each(function (d) {
      const hitR = Math.max(8, d.r + 3);
      d3.select(this).attr('d', diamondPath(newX(d.date), d.y, hitR));
    });
  }
  if (paperCiteG) {
    paperCiteG.selectAll('.paper-cite-edge').each(function (d) {
      d3.select(this)
        .attr('x1', newX(d.srcDate)).attr('x2', newX(d.tgtDate));
    });
  }
}

function showPaperTooltip(ev, d) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const p = d.paper;
  const color = THREAD_COLORS[p.th] || '#2f4f77';
  tip.innerHTML = '<strong style="color:' + color + '">' + escHtml(p.t || '') + '</strong><br>' +
    (p.y || '') + (p.cb ? ' \u00b7 ' + p.cb + ' citations' : '') +
    ' \u00b7 inf: ' + (p.inf || 0).toFixed(2) +
    (p.a && p.a.length > 0 ? '<br><span style="color:#888">' + escHtml(p.a.slice(0, 3).join(', ')) + (p.a.length > 3 ? ' et al.' : '') + '</span>' : '');
  tip.style.display = 'block';
  let x = ev.clientX + 14;
  let y = ev.clientY - 10;
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

// --- Magicians layer on timeline ---

function buildMagiciansLayer() {
  if (!zoomG || !xScaleOrig || magLayerBuilt) return;
  const graphData = getGraph();
  if (!graphData?.magiciansTopics) return;

  const magTopics = graphData.magiciansTopics;

  // Compute engagement scores for radius scaling
  let maxMagInf = 0;
  const magEntries = [];
  for (const [mtid, mt] of Object.entries(magTopics)) {
    if (!mt.d) continue;
    const date = new Date(mt.d);
    if (isNaN(date)) continue;
    const inf = mt.inf || magiciansEngagementScore(mt);
    if (inf > maxMagInf) maxMagInf = inf;
    const thread = magiciansThreadFromTopic(mt);
    const lane = (thread && laneIdx[thread] !== undefined) ? laneIdx[thread] : laneIdx['_other'] ?? laneOrder.length - 1;
    const yBase = topicLaneY0 + lane * laneH + laneH * 0.15;
    const yRange = laneH * 0.7;
    const y = yBase + (hashCode(Number(mtid)) % 100) / 100 * yRange;
    magEntries.push({ mtid: Number(mtid), mt, date, inf, thread, y });
  }

  const magRScale = d3.scaleSqrt().domain([0, maxMagInf || 1]).range([3, 11]);

  if (!magCrossRefG) magCrossRefG = zoomG.append('g').attr('class', 'magicians-crossref-layer');
  if (!magLayerG) magLayerG = zoomG.append('g').attr('class', 'magicians-layer');

  // Cross-reference edges to ethresearch topics
  magEntries.forEach(({ mtid, mt, date, y }) => {
    for (const tid of (mt.er || [])) {
      const topic = topicMap[tid];
      if (!topic || topic._yPos === undefined) continue;
      magCrossRefG.append('line')
        .attr('class', 'magicians-ref-edge')
        .attr('x1', xScaleOrig(date)).attr('y1', y)
        .attr('x2', xScaleOrig(topic._date)).attr('y2', topic._yPos)
        .attr('stroke', '#9b72c2').attr('stroke-opacity', 0.14)
        .attr('stroke-width', 0.9).attr('stroke-dasharray', '3 3')
        .datum({ mtid, topicId: tid, magDate: date, topicDate: topic._date, magY: y, topicY: topic._yPos });
    }
  });

  // Triangle nodes
  magEntries.forEach(({ mtid, mt, date, inf, thread, y }) => {
    const r = magRScale(inf);
    const color = (thread && THREAD_COLORS[thread]) ? THREAD_COLORS[thread] : '#bb88cc';
    let clickTimer = null;

    magLayerG.append('path')
      .attr('class', 'magicians-triangle')
      .attr('d', trianglePath(xScaleOrig(date), y, r))
      .attr('fill', color).attr('stroke', color)
      .attr('stroke-width', 0.5).attr('opacity', 0.7)
      .datum({ mtid, mt, date, inf, thread, y, r, type: 'magicians' })
      .on('click', function (ev, d) {
        ev.stopPropagation();
        if (clickTimer) {
          clearTimeout(clickTimer); clickTimer = null;
          selectEntity({ type: 'magicians', id: d.mtid });
          return;
        }
        clickTimer = setTimeout(() => {
          clickTimer = null;
          pinEntity({ type: 'magicians', id: d.mtid });
          applyPinnedHighlight();
        }, 220);
      })
      .on('mouseover', function (ev, d) { showMagiciansTooltip(ev, d); })
      .on('mouseout', function () { hideTooltip(); });
  });

  // Labels for top 12 by engagement
  const topMag = magEntries.slice().sort((a, b) => b.inf - a.inf).slice(0, 12);
  topMag.forEach(({ mt, date, inf, y }) => {
    const r = magRScale(inf);
    const title = mt.t || '';
    const txt = title.length > 28 ? title.slice(0, 27) + '\u2026' : title;
    magLayerG.append('text')
      .attr('class', 'magicians-label')
      .attr('x', xScaleOrig(date) + r + 3).attr('y', y + 3)
      .attr('fill', '#c8b5db').attr('font-size', 8).attr('pointer-events', 'none')
      .text(txt)
      .datum({ date });
  });

  magLayerBuilt = true;
  if (xScale !== xScaleOrig) updateMagiciansLayerZoom(xScale);
  filterMagiciansLayer();
}

function removeMagiciansLayer() {
  if (magLayerG) magLayerG.selectAll('*').remove();
  if (magCrossRefG) magCrossRefG.selectAll('*').remove();
  magLayerBuilt = false;
}

function updateMagiciansLayerZoom(newX) {
  if (!magLayerG) return;
  magLayerG.selectAll('.magicians-triangle').each(function (d) {
    d3.select(this).attr('d', trianglePath(newX(d.date), d.y, d.r));
  });
  magLayerG.selectAll('.magicians-label').attr('x', function (d) {
    return newX(d.date) + 6;
  });
  if (magCrossRefG) {
    magCrossRefG.selectAll('.magicians-ref-edge')
      .attr('x1', d => newX(d.magDate))
      .attr('x2', d => newX(d.topicDate));
  }
}

function filterMagiciansLayer() {
  if (!magLayerG || !magLayerBuilt) return;
  const st = getState();
  const hasActiveFilter = st.activeThread || st.activeAuthor || st.activeCategory || st.activeTag;

  magLayerG.selectAll('.magicians-triangle').each(function (d) {
    let show = true;
    // Influence slider
    if (st.minInfluence > 0 && (d.inf || 0) < st.minInfluence) show = false;
    if (hasActiveFilter && show) {
      if (st.activeThread && d.thread !== st.activeThread) show = false;
      if (st.activeAuthor && d.mt.a !== st.activeAuthor) show = false;
    }
    d3.select(this)
      .style('display', show ? null : 'none')
      .style('pointer-events', show ? 'all' : 'none');
  });

  magLayerG.selectAll('.magicians-label')
    .style('display', hasActiveFilter ? 'none' : null);

  if (magCrossRefG) {
    magCrossRefG.selectAll('.magicians-ref-edge')
      .style('display', (st.showPosts && !hasActiveFilter) ? null : 'none');
  }
}

function showMagiciansTooltip(ev, d) {
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const mt = d.mt;
  const color = (d.thread && THREAD_COLORS[d.thread]) ? THREAD_COLORS[d.thread] : '#bb88cc';
  tip.innerHTML = '<strong style="color:' + color + '">\u25B3 ' + escHtml(mt.t || '') + '</strong><br>' +
    '<span style="color:#888">' + escHtml(mt.a || '') + ' \u00b7 ' + (mt.d || '').slice(0, 10) + '</span>' +
    (mt.eips?.length > 0 ? '<br><span style="color:#88aacc">EIPs: ' + mt.eips.map(e => 'EIP-' + e).join(', ') + '</span>' : '') +
    '<br><span style="color:#666">' + (mt.vw || 0) + ' views \u00b7 ' + (mt.lk || 0) + ' likes \u00b7 ' + (mt.pc || 0) + ' posts</span>';
  tip.style.display = 'block';
  let x = ev.clientX + 14;
  let y = ev.clientY - 10;
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

export function onActivate() {
  // Called when timeline view becomes active (after switching from another view)
  filterTimeline();
}
