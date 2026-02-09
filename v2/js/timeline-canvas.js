// timeline-canvas.js — Canvas swim-lane timeline view (replaces SVG timeline.js)
// Uses 2 canvases (base + HUD) + DOM overlay for axis/lane labels.

import { THREAD_COLORS, THREAD_ORDER, THREAD_NAMES, TIMELINE_ZOOM_EXTENT, EIP_STATUS_COLORS, PAPER_LAYER_LIMITS } from './constants.js';
import { getState, on, selectEntity, pinEntity, hoverEntity, setFilters } from './state.js';
import { getCore, getCoreIndexes, getEips, getPapers, loadEips, loadPapers, loadGraph, getGraph, getGraphIndexes } from './data.js';
import { setupCanvas, drawRoundedRect, drawDiamond, drawTriangle, drawStar, drawArrow, hexWithAlpha } from './canvas-utils.js';

// --- Module state ---
let initialized = false;
let baseCanvas = null;
let hudCanvas = null;
let baseCtx = null;
let hudCtx = null;
let domOverlay = null;
let containerEl = null;
let canvasW = 0;
let canvasH = 0;
let plotW = 0;
let plotH = 0;
let marginLeft = 0;
let marginTop = 0;
let marginRight = 0;
let marginBottom = 0;
let xScaleOrig = null;
let xScale = null;
let rScale = null;
let laneIdx = {};
let laneH = 0;
let laneOrder = [];
let topicLaneY0 = 0;
let swimH = 0;
let histH = 24;
let forkLabelH = 18;
let zoomBehavior = null;
let zoomTransform = d3.zoomIdentity;
let topicMap = {};
let defaultInfluenceThreshold = 0;

// RAF
let needsBaseRedraw = true;
let needsHudRedraw = true;
let rafId = null;

// Tween system
let tweens = [];
const TWEEN_DURATION = 200;

// Entity arrays
let topicEntities = [];    // { id, x, y, date, r, color, thread, inf, opacity, targetOpacity, visible, isMinor, data }
let edgeData = [];         // { source, target, sd, td, sy, ty, opacity }
let eraData = [];          // { start, end, color, name, idx }
let forkData = [];         // { date, name, displayName, eips, rt, fork, x }
let histData = [];         // { date, count, x, y, w, h }
let liveLineDate = null;

// Hit-testing: per-lane sorted arrays
let laneBuckets = [];      // laneIndex → sorted array of entity indices by screen-X
let entityById = {};       // id → entity index

// Hover/pin state (local, synced with global state)
let hoveredIdx = -1;
let hoveredEntity = null;  // { type, id }

// EIP layer
let eipEntities = [];
let eipEdgeData = [];
let eipLayerBuilt = false;
let eipToTopicMap = {};

// Paper layer
let paperEntities = [];
let paperEdgeData = [];
let paperLayerBuilt = false;
let paperLayerMode = null;

// Magicians layer
let magEntities = [];
let magEdgeData = [];
let magLayerBuilt = false;

// Pin overlay data (drawn on HUD canvas)
let pinOverlayEdges = [];
let pinOverlayLabels = [];

// Labels
let labelSet = new Set();
let currentLabelCount = 30;

// Milestone data
let milestoneData = [];

// Histogram scales
let histYScale = null;
let barWidthBase = 0;
let maxHistCount = 1;

// --- Constants ---
const TL_MIN_ZOOM = TIMELINE_ZOOM_EXTENT[0];
const TL_MAX_ZOOM = TIMELINE_ZOOM_EXTENT[1];
const TL_EDGE_PAD_FRACTION = 0.05;
const TL_EDGE_PAD_MIN = 40;

const STOP_WORDS = new Set([
  'the','and','for','with','from','that','this','have','been','will','are',
  'was','were','but','not','all','can','had','its','they','would','what',
  'when','which','their','also','more','some','than','about','into','over',
  'such','after','through','very','much','only','between','how','does',
  'each','where','based','using','towards','toward','ethereum','analysis',
  'approach','method','protocol','system','systems','network','networks',
]);

// --- Pure utility functions (ported directly) ---

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

function escHtml(s) {
  const el = document.createElement('span');
  el.textContent = s || '';
  return el.innerHTML;
}

function clampTimelineTransform(t) {
  let k = t && isFinite(t.k) ? t.k : 1;
  k = Math.max(TL_MIN_ZOOM, Math.min(TL_MAX_ZOOM, k));
  if (!plotW || plotW <= 0) return d3.zoomIdentity.translate(0, 0).scale(k);
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

// --- Tween system ---

function addTween(entity, prop, to, duration) {
  // Remove existing tween for same entity+prop
  tweens = tweens.filter(tw => !(tw.entity === entity && tw.prop === prop));
  const from = entity[prop];
  if (Math.abs(from - to) < 0.001) { entity[prop] = to; return; }
  tweens.push({ entity, prop, from, to, startTime: performance.now(), duration: duration || TWEEN_DURATION });
}

function tickTweens() {
  if (tweens.length === 0) return false;
  const now = performance.now();
  let anyActive = false;
  const originalLength = tweens.length;
  const remaining = [];
  for (const tw of tweens) {
    const elapsed = now - tw.startTime;
    if (elapsed >= tw.duration) {
      tw.entity[tw.prop] = tw.to;
    } else {
      const t = elapsed / tw.duration;
      tw.entity[tw.prop] = tw.from + (tw.to - tw.from) * t;
      anyActive = true;
      remaining.push(tw);
    }
  }
  tweens = remaining;
  return anyActive || remaining.length < originalLength;
}

// --- Tooltip functions (DOM, ported directly) ---

let hideTooltipTimer = null;
function cancelHideTooltip() { clearTimeout(hideTooltipTimer); }

function hideTooltip() {
  clearTimeout(hideTooltipTimer);
  hideTooltipTimer = setTimeout(() => {
    const tip = document.getElementById('tooltip');
    if (tip) tip.style.display = 'none';
  }, 80);
}

function positionTooltip(tip, clientX, clientY) {
  let x = clientX + 14;
  let y = clientY - 10;
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

function showTooltip(clientX, clientY, t) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const color = THREAD_COLORS[t.th] || '#666';
  const primary = (t.peips && t.peips.length > 0) ? ' [EIP-' + t.peips.join(', EIP-') + ']' : '';
  tip.innerHTML = '<strong>' + escHtml(t.t) + '</strong><br>' +
    escHtml(t.a) + ' \u00b7 ' + (t.d || '').slice(0, 10) + ' \u00b7 inf: ' + (t.inf || 0).toFixed(2) +
    primary;
  tip.style.display = 'block';
  positionTooltip(tip, clientX, clientY);
}

function showHistTooltip(clientX, clientY, d) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const mn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  tip.innerHTML = mn[d.date.getMonth()] + ' ' + d.date.getFullYear() + ': ' + d.count + ' topic' + (d.count !== 1 ? 's' : '');
  tip.style.display = 'block';
  tip.style.left = (clientX + 10) + 'px';
  tip.style.top = (clientY - 24) + 'px';
}

function showForkTooltip(clientX, clientY, f) {
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
  positionTooltip(tip, clientX, clientY);
}

function showEipTooltip(clientX, clientY, d) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const statusColor = EIP_STATUS_COLORS[d.eip.s] || '#555';
  tip.innerHTML = '<strong style="color:' + statusColor + '">EIP-' + d.num + ': ' + escHtml(d.eip.t || '') + '</strong><br>' +
    (d.eip.s || '') + (d.eip.fk ? ' \u00b7 ' + d.eip.fk : '') +
    ' \u00b7 inf: ' + (d.eip.inf || 0).toFixed(2);
  tip.style.display = 'block';
  positionTooltip(tip, clientX, clientY);
}

function showPaperTooltip(clientX, clientY, d) {
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
  positionTooltip(tip, clientX, clientY);
}

function showMagiciansTooltip(clientX, clientY, d) {
  cancelHideTooltip();
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const mt = d.mt;
  const color = (d.thread && THREAD_COLORS[d.thread]) ? THREAD_COLORS[d.thread] : '#bb88cc';
  tip.innerHTML = '<strong style="color:' + color + '">\u25B3 ' + escHtml(mt.t || '') + '</strong><br>' +
    '<span style="color:#888">' + escHtml(mt.a || '') + ' \u00b7 ' + (mt.d || '').slice(0, 10) + '</span>' +
    (mt.eips?.length > 0 ? '<br><span style="color:#88aacc">EIPs: ' + mt.eips.map(e => 'EIP-' + e).join(', ') + '</span>' : '') +
    '<br><span style="color:#666">' + (mt.vw || 0) + ' views \u00b7 ' + (mt.lk || 0) + ' likes \u00b7 ' + (mt.pc || 0) + ' posts</span>';
  tip.style.display = 'block';
  positionTooltip(tip, clientX, clientY);
}

// --- Coordinate helpers ---

function screenToPlot(sx, sy) {
  // Convert canvas-local pixel coords to plot-area coordinates
  // (same coordinate system as curX(date) and entity.y)
  return [sx - marginLeft, sy - marginTop];
}

// --- Hit-testing: binary search in sorted lane arrays ---

function buildLaneBuckets() {
  const numLanes = laneOrder.length;
  laneBuckets = new Array(numLanes);
  for (let i = 0; i < numLanes; i++) laneBuckets[i] = [];

  for (let idx = 0; idx < topicEntities.length; idx++) {
    const e = topicEntities[idx];
    const th = (e.data.th && laneIdx[e.data.th] !== undefined) ? e.data.th : '_other';
    const lane = laneIdx[th];
    if (lane !== undefined) laneBuckets[lane].push(idx);
  }

  // Sort each bucket by date for binary search on X
  for (let i = 0; i < numLanes; i++) {
    laneBuckets[i].sort((a, b) => topicEntities[a].date - topicEntities[b].date);
  }
}

function hitTestTopic(sx, sy) {
  const [wx, wy] = screenToPlot(sx, sy);

  // Determine lane from world Y
  const laneFloat = (wy - topicLaneY0) / laneH;
  const laneI = Math.floor(laneFloat);
  if (laneI < 0 || laneI >= laneOrder.length) return -1;

  const bucket = laneBuckets[laneI];
  if (!bucket || bucket.length === 0) return -1;

  // Compute the world X value
  const curX = xScale || xScaleOrig;

  // Linear scan nearby entities (lanes are narrow, few visible)
  let bestIdx = -1;
  let bestDistSq = Infinity;
  const maxR = 20; // max hit radius in world pixels

  for (const idx of bucket) {
    const e = topicEntities[idx];
    if (e.opacity < 0.05) continue;
    const ex = curX(e.date);
    const ey = e.y;
    const dx = wx - ex;
    const dy = wy - ey;
    const distSq = dx * dx + dy * dy;
    const hitR = Math.max(e.r + 2, 6);
    if (distSq < hitR * hitR && distSq < bestDistSq) {
      bestDistSq = distSq;
      bestIdx = idx;
    }
  }
  return bestIdx;
}

function hitTestAllEntities(sx, sy) {
  // First try topics
  const topicIdx = hitTestTopic(sx, sy);
  if (topicIdx >= 0) return { type: 'topic', idx: topicIdx, entity: topicEntities[topicIdx] };

  const [wx, wy] = screenToPlot(sx, sy);
  const curX = xScale || xScaleOrig;

  // Try EIP entities
  if (eipLayerBuilt) {
    for (let i = 0; i < eipEntities.length; i++) {
      const e = eipEntities[i];
      if (e.opacity < 0.05) continue;
      const ex = curX(e.date);
      const ey = e.y;
      const halfSize = e.size / 2 + 2;
      if (Math.abs(wx - ex) <= halfSize && Math.abs(wy - ey) <= halfSize) {
        return { type: 'eip', idx: i, entity: e };
      }
    }
  }

  // Try paper entities
  if (paperLayerBuilt) {
    for (let i = 0; i < paperEntities.length; i++) {
      const e = paperEntities[i];
      if (e.opacity < 0.05) continue;
      const ex = curX(e.date);
      const ey = e.y;
      const hitR = Math.max(e.r + 3, 8);
      const dx = wx - ex, dy = wy - ey;
      if (dx * dx + dy * dy < hitR * hitR) {
        return { type: 'paper', idx: i, entity: e };
      }
    }
  }

  // Try magicians entities
  if (magLayerBuilt) {
    for (let i = 0; i < magEntities.length; i++) {
      const e = magEntities[i];
      if (e.opacity < 0.05) continue;
      const ex = curX(e.date);
      const ey = e.y;
      const hitR = e.r + 3;
      const dx = wx - ex, dy = wy - ey;
      if (dx * dx + dy * dy < hitR * hitR) {
        return { type: 'magicians', idx: i, entity: e };
      }
    }
  }

  // Try fork lines
  for (const f of forkData) {
    const fx = curX(f.date);
    if (Math.abs(wx - fx) < 6 && wy >= -5 && wy <= topicLaneY0 + swimH + histH) {
      return { type: 'fork', entity: f };
    }
  }

  // Try era labels (clickable text at the top)
  for (const era of eraData) {
    const x0 = curX(era.start);
    const x1 = curX(era.end);
    const midX = (x0 + x1) / 2;
    // Era label is around y=-8, approx 60px wide text
    if (Math.abs(wx - midX) < 40 && wy >= -20 && wy <= 0) {
      return { type: 'era', entity: era };
    }
  }

  // Try histogram bars
  for (const h of histData) {
    const hx = curX(h.date);
    const barW = Math.max(1, (curX(new Date(2020, 1, 1)) - curX(new Date(2020, 0, 1))) * 0.85);
    if (wx >= hx && wx <= hx + barW &&
        wy >= topicLaneY0 + swimH + (histH - h.h) && wy <= topicLaneY0 + swimH + histH) {
      return { type: 'hist', entity: h };
    }
  }

  return null;
}

// --- buildPinnedConnections (ported directly, no DOM ops) ---

function buildPinnedConnections(pinned) {
  const connectedTopics = new Set();
  const connectedEips = new Set();
  const connectedPapers = new Set();
  const connectedMagicians = new Set();

  const indexes = getCoreIndexes();
  const core = getCore();
  const paperDataObj = getPapers();
  const graphData = getGraph();
  const graphIdx = getGraphIndexes();

  if (pinned.type === 'topic') {
    connectedTopics.add(pinned.id);
    const adj = indexes?.topicEdgeIndex?.[String(pinned.id)];
    if (adj) adj.forEach(id => connectedTopics.add(id));
    const topic = core?.topics?.[pinned.id];
    if (topic) {
      for (const eNum of (topic.eips || []).concat(topic.peips || [])) connectedEips.add(Number(eNum));
    }
    if (graphIdx?.topicToMagiciansRefs?.[String(pinned.id)]) {
      graphIdx.topicToMagiciansRefs[String(pinned.id)].forEach(mid => connectedMagicians.add(mid));
    }
    for (const eNum of connectedEips) {
      if (graphIdx?.eipToMagiciansRefs?.[String(eNum)]) {
        graphIdx.eipToMagiciansRefs[String(eNum)].forEach(mid => connectedMagicians.add(mid));
      }
    }
    if (paperDataObj?.papers) {
      const topicKW = extractKeywords(topic?.t);
      const topicThread = topic?.th;
      const scored = [];
      for (const [pid, p] of Object.entries(paperDataObj.papers)) {
        let score = 0;
        for (const peip of (p.eq || [])) {
          if (connectedEips.has(Number(peip))) { score += 3.0; break; }
        }
        if (topicKW.size > 0) {
          const paperKW = extractKeywords(p.t);
          const overlap = keywordOverlap(topicKW, paperKW);
          if (overlap > 0) score += overlap * 0.65;
        }
        if (topicThread && p.th === topicThread) score += 1.0;
        if (score >= 1.0) scored.push({ id: pid, score, inf: p.inf || 0 });
      }
      scored.sort((a, b) => b.score - a.score || b.inf - a.inf);
      for (const s of scored.slice(0, 12)) connectedPapers.add(s.id);
    }
  } else if (pinned.type === 'eip') {
    connectedEips.add(Number(pinned.id));
    const eipTopics = indexes?.eipToTopics?.[String(pinned.id)];
    if (eipTopics) eipTopics.forEach(tid => connectedTopics.add(tid));
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
    const eipDataObj = getEips();
    if (eipDataObj?.eipCatalog) {
      const cat = eipDataObj.eipCatalog[String(pinned.id)];
      if (cat?.req) for (const r of cat.req) connectedEips.add(Number(r));
      for (const [eNum, e] of Object.entries(eipDataObj.eipCatalog)) {
        if ((e.req || []).includes(Number(pinned.id)) || (e.req || []).includes(String(pinned.id))) {
          connectedEips.add(Number(eNum));
        }
      }
    }
    if (paperDataObj?.papers) {
      const eipDataObj2 = getEips();
      const eipTitle = eipDataObj2?.eipCatalog?.[String(pinned.id)]?.t || '';
      const eipKW = extractKeywords(eipTitle);
      const eipThread = eipDataObj2?.eipCatalog?.[String(pinned.id)]?.th;
      const scored = [];
      for (const [pid, p] of Object.entries(paperDataObj.papers)) {
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
    if (paperDataObj?.paperGraph?.edges) {
      for (const edge of paperDataObj.paperGraph.edges) {
        if (edge.source === pinned.id) connectedPapers.add(edge.target);
        else if (edge.target === pinned.id) connectedPapers.add(edge.source);
      }
    }
    const paper = paperDataObj?.papers?.[pinned.id];
    if (paper) {
      for (const eNum of (paper.eq || [])) connectedEips.add(Number(eNum));
    }
    for (const eNum of connectedEips) {
      const eipTopics = indexes?.eipToTopics?.[String(eNum)];
      if (eipTopics) eipTopics.forEach(tid => connectedTopics.add(tid));
    }
    const paper2 = paperDataObj?.papers?.[pinned.id];
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
    for (const eNum of connectedEips) {
      if (graphIdx?.eipToMagiciansRefs?.[String(eNum)]) {
        graphIdx.eipToMagiciansRefs[String(eNum)].forEach(mid => connectedMagicians.add(mid));
      }
    }
  } else if (pinned.type === 'magicians') {
    connectedMagicians.add(pinned.id);
    const mt = graphData?.magiciansTopics?.[String(pinned.id)];
    if (mt) {
      for (const tid of (mt.er || [])) connectedTopics.add(Number(tid));
      for (const eNum of (mt.eips || [])) connectedEips.add(Number(eNum));
    }
    if (graphIdx?.magiciansToEips?.[String(pinned.id)]) {
      for (const eNum of graphIdx.magiciansToEips[String(pinned.id)]) {
        connectedEips.add(Number(eNum));
      }
    }
    for (const eNum of connectedEips) {
      const eipTopics = indexes?.eipToTopics?.[String(eNum)];
      if (eipTopics) eipTopics.forEach(tid => connectedTopics.add(tid));
    }
    if (paperDataObj?.papers && connectedEips.size > 0) {
      for (const [pid, p] of Object.entries(paperDataObj.papers)) {
        for (const peip of (p.eq || [])) {
          if (connectedEips.has(Number(peip))) { connectedPapers.add(pid); break; }
        }
      }
    }
  }

  return { connectedTopics, connectedEips, connectedPapers, connectedMagicians };
}

// --- Init ---

export function init() {
  if (initialized) return;
  initialized = true;

  containerEl = document.getElementById('timeline-view');
  if (!containerEl) return;

  const core = getCore();
  if (!core) return;

  topicMap = core.topics || {};

  buildTimeline(core);

  // Set up default influence threshold
  const defaultThreshold = computeDefaultThreshold(topicMap);
  defaultInfluenceThreshold = defaultThreshold;
  if (defaultThreshold > 0) {
    setFilters({ minInfluence: defaultThreshold });
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
    if (key === 'showPapers' || key === 'showEips') return;
    filterTimeline();
  });
  on('reset', onReset);
  on('pin:changed', ({ current }) => {
    if (!current) {
      clearPinOverlay();
      filterTimeline();
    }
  });

  // ResizeObserver
  let resizeTimer = null;
  const ro = new ResizeObserver(() => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(rebuildTimeline, 200);
  });
  ro.observe(containerEl);

  // Initial filter
  filterTimeline();

  // Start render loop
  renderLoop();
}

function rebuildTimeline() {
  if (!containerEl) return;
  const core = getCore();
  if (!core) return;

  // Clean up
  containerEl.innerHTML = '';
  baseCanvas = null;
  hudCanvas = null;
  baseCtx = null;
  hudCtx = null;
  domOverlay = null;
  topicEntities = [];
  edgeData = [];
  eraData = [];
  forkData = [];
  histData = [];
  eipEntities = [];
  eipEdgeData = [];
  eipLayerBuilt = false;
  paperEntities = [];
  paperEdgeData = [];
  paperLayerBuilt = false;
  paperLayerMode = null;
  magEntities = [];
  magEdgeData = [];
  magLayerBuilt = false;
  pinOverlayEdges = [];
  pinOverlayLabels = [];
  milestoneData = [];
  labelSet = new Set();
  tweens = [];
  zoomTransform = d3.zoomIdentity;

  buildTimeline(core);
  filterTimeline();
}

function buildTimeline(core) {
  const width = containerEl.clientWidth || 900;
  const height = containerEl.clientHeight || 700;

  const margin = { top: 50, right: 40, bottom: 30 + histH + forkLabelH, left: 180 };
  plotW = width - margin.left - margin.right;
  plotH = height - margin.top - margin.bottom;
  marginLeft = margin.left;
  marginTop = margin.top;
  marginRight = margin.right;
  marginBottom = margin.bottom;
  swimH = plotH - histH;
  topicLaneY0 = 0;
  canvasW = width;
  canvasH = height;

  // --- Thread lanes ---
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
  laneIdx = {};
  laneOrder.forEach((tid, i) => { laneIdx[tid] = i; });

  // --- Time scale ---
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

  // --- Size scale ---
  const maxInf = d3.max(Object.values(topicMap), t => t.inf) || 1;
  rScale = d3.scaleSqrt().domain([0, maxInf]).range([2.5, 14]);

  // --- Create wrapper + canvases + DOM overlay ---
  const wrapper = document.createElement('div');
  wrapper.className = 'timeline-container';
  wrapper.style.position = 'relative';
  wrapper.style.width = '100%';
  wrapper.style.height = '100%';
  wrapper.style.overflow = 'hidden';
  containerEl.appendChild(wrapper);

  // Base canvas (z-index: 0)
  baseCanvas = document.createElement('canvas');
  baseCanvas.style.position = 'absolute';
  baseCanvas.style.left = '0';
  baseCanvas.style.top = '0';
  baseCanvas.style.touchAction = 'none';
  wrapper.appendChild(baseCanvas);
  ({ ctx: baseCtx } = setupCanvas(baseCanvas, width, height));

  // HUD canvas (z-index: 1)
  hudCanvas = document.createElement('canvas');
  hudCanvas.style.position = 'absolute';
  hudCanvas.style.left = '0';
  hudCanvas.style.top = '0';
  hudCanvas.style.pointerEvents = 'none';
  hudCanvas.style.zIndex = '1';
  wrapper.appendChild(hudCanvas);
  ({ ctx: hudCtx } = setupCanvas(hudCanvas, width, height));

  // DOM overlay (z-index: 2) for axis + lane labels
  domOverlay = document.createElement('div');
  domOverlay.style.position = 'absolute';
  domOverlay.style.left = '0';
  domOverlay.style.top = '0';
  domOverlay.style.width = '100%';
  domOverlay.style.height = '100%';
  domOverlay.style.pointerEvents = 'none';
  domOverlay.style.zIndex = '2';
  wrapper.appendChild(domOverlay);

  // --- Pre-compute topic positions ---
  Object.values(topicMap).forEach(t => {
    const th = (t.th && laneIdx[t.th] !== undefined) ? t.th : '_other';
    const lane = laneIdx[th];
    const yBase = topicLaneY0 + lane * laneH + laneH * 0.12;
    const yRange = laneH * 0.76;
    t._yPos = yBase + (hashCode(t.id) % 100) / 100 * yRange;
    t._date = new Date(t.d);
  });

  // --- Build topic entities ---
  topicEntities = [];
  entityById = {};
  Object.values(topicMap).forEach(t => {
    if (t._yPos === undefined) return;
    const color = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';
    const entity = {
      id: t.id,
      date: t._date,
      y: t._yPos,
      r: rScale(t.inf),
      color,
      thread: t.th,
      inf: t.inf || 0,
      opacity: 0.65,
      targetOpacity: 0.65,
      visible: true,
      isMinor: !!t.mn,
      data: t,
    };
    entityById[t.id] = topicEntities.length;
    topicEntities.push(entity);
  });

  // Build lane buckets for hit-testing
  buildLaneBuckets();

  // --- Build edge data ---
  edgeData = [];
  const graphEdges = core.graph?.edges || [];
  for (const e of graphEdges) {
    const sT = topicMap[e.source];
    const tT = topicMap[e.target];
    if (sT && tT && sT._yPos !== undefined && tT._yPos !== undefined) {
      edgeData.push({
        source: e.source,
        target: e.target,
        sd: sT._date,
        td: tT._date,
        sy: sT._yPos,
        ty: tT._yPos,
        opacity: 0.06,
        highlighted: false,
      });
    }
  }

  // --- Build era data ---
  const eraColors = ['#334', '#343', '#334', '#433', '#343'];
  eraData = (core.eras || []).map((era, i) => ({
    start: new Date(era.start),
    end: new Date(era.end),
    color: eraColors[i] || '#333',
    name: era.name,
    idx: i,
  }));

  // --- Build fork data ---
  forkData = (core.forks || []).filter(f => f.d).map(f => ({
    date: new Date(f.d),
    name: f.n,
    displayName: f.cn || f.n,
    eips: f.eips || [],
    rt: f.rt || [],
    fork: f,
  }));

  // ethresear.ch live line
  liveLineDate = new Date('2017-08-17');

  // --- Build histogram data ---
  const monthBins = {};
  Object.values(topicMap).forEach(t => {
    const d = t._date;
    if (!d || isNaN(d)) return;
    const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
    if (!monthBins[key]) monthBins[key] = { date: new Date(d.getFullYear(), d.getMonth(), 1), count: 0 };
    monthBins[key].count++;
  });
  histData = Object.values(monthBins).sort((a, b) => a.date - b.date);
  maxHistCount = d3.max(histData, d => d.count) || 1;
  histYScale = d3.scaleLinear().domain([0, maxHistCount]).range([0, histH - 2]);
  barWidthBase = Math.max(1, xScaleOrig(new Date(2020, 1, 1)) - xScaleOrig(new Date(2020, 0, 1)));

  // Pre-compute histogram bar heights
  histData.forEach(d => { d.h = histYScale(d.count); });

  // --- Build milestone data ---
  milestoneData = [];
  const threads = core.threads || {};
  THREAD_ORDER.forEach(tid => {
    const th = threads[tid];
    if (!th || !th.ms) return;
    th.ms.forEach(ms => {
      const topic = topicMap[ms.id];
      if (topic && topic._yPos !== undefined) {
        milestoneData.push({ topic, note: ms.n, threadId: tid });
      }
    });
  });

  // --- Build label set (top 30) ---
  const topByInf = Object.values(topicMap)
    .filter(t => t._yPos !== undefined)
    .sort((a, b) => b.inf - a.inf)
    .slice(0, 30);
  labelSet = new Set(topByInf.map(t => t.id));
  currentLabelCount = 30;

  // --- DOM lane labels + x-axis ---
  buildDomOverlay();

  // --- Zoom ---
  zoomBehavior = d3.zoom()
    .scaleExtent([TL_MIN_ZOOM, TL_MAX_ZOOM])
    .translateExtent([[0, 0], [plotW, canvasH]])
    .extent([[0, 0], [plotW, canvasH]])
    .constrain(function (transform) { return clampTimelineTransform(transform); })
    .filter(function (ev) {
      if (ev.type === 'wheel') return true;
      if (ev.type === 'dblclick') return false;
      return !ev.button;
    })
    .on('zoom', onZoom);

  d3.select(baseCanvas).call(zoomBehavior);

  // Prevent macOS swipe-back
  baseCanvas.addEventListener('wheel', (e) => { e.preventDefault(); }, { passive: false });

  // --- Pointer events ---
  let pointerRafPending = false;
  let lastPointerX = 0;
  let lastPointerY = 0;

  baseCanvas.addEventListener('pointermove', (event) => {
    lastPointerX = event.offsetX;
    lastPointerY = event.offsetY;
    if (!pointerRafPending) {
      pointerRafPending = true;
      requestAnimationFrame(() => {
        pointerRafPending = false;
        handlePointerMove(lastPointerX, lastPointerY);
      });
    }
  });

  baseCanvas.addEventListener('pointerleave', () => {
    if (hoveredIdx >= 0 || hoveredEntity) {
      hoveredIdx = -1;
      hoveredEntity = null;
      hoverEntity(null);
      hideTooltip();
      // If pinned, don't restore — keep pinned state
      if (!getState().pinnedEntity) {
        filterTimeline();
      }
      needsHudRedraw = true;
    }
  });

  // Click handler (single=pin, double=detail)
  let clickTimer = null;
  let clickCount = 0;
  const DBLCLICK_DELAY = 220;

  baseCanvas.addEventListener('click', (event) => {
    const hit = hitTestAllEntities(event.offsetX, event.offsetY);

    if (!hit) {
      // Background click — clear pin/selection
      const st = getState();
      if (st.pinnedEntity || st.selectedEntity) {
        pinEntity(null);
        selectEntity(null);
        clearPinOverlay();
        filterTimeline();
      }
      return;
    }

    const entityRef = resolveHitToEntityRef(hit);
    if (!entityRef) return;

    // Eras and forks: direct select on single click (no pin/double-click)
    if (hit.type === 'era' || hit.type === 'fork') {
      selectEntity(entityRef);
      return;
    }

    // Histogram bars: no click behavior (tooltip only)
    if (hit.type === 'hist') return;

    event.stopPropagation();
    clickCount++;
    if (clickCount === 1) {
      clickTimer = setTimeout(() => {
        clickCount = 0;
        // Single click — pin
        pinEntity(entityRef);
        applyPinnedHighlight();
      }, DBLCLICK_DELAY);
    } else if (clickCount === 2) {
      clearTimeout(clickTimer);
      clickCount = 0;
      // Double click — detail panel
      selectEntity(entityRef);
      applyPinnedHighlight();
    }
  });

  // Double-click on empty canvas resets zoom
  baseCanvas.addEventListener('dblclick', (event) => {
    const hit = hitTestAllEntities(event.offsetX, event.offsetY);
    if (!hit) {
      d3.select(baseCanvas).transition().duration(500).call(zoomBehavior.transform, d3.zoomIdentity);
    }
  });

  needsBaseRedraw = true;
  needsHudRedraw = true;
}

function resolveHitToEntityRef(hit) {
  if (!hit) return null;
  if (hit.type === 'topic') return { type: 'topic', id: hit.entity.data.id };
  if (hit.type === 'eip') return { type: 'eip', id: hit.entity.num };
  if (hit.type === 'paper') return { type: 'paper', id: hit.entity.paper.id };
  if (hit.type === 'magicians') return { type: 'magicians', id: hit.entity.mtid };
  if (hit.type === 'fork') return { type: 'fork', id: hit.entity.name };
  if (hit.type === 'era') return { type: 'era', id: hit.entity.idx };
  return null;
}

// --- DOM overlay (lane labels + x-axis) ---

function buildDomOverlay() {
  if (!domOverlay) return;
  domOverlay.innerHTML = '';

  // Lane labels (left side)
  laneOrder.forEach((tid, i) => {
    const y = marginTop + topicLaneY0 + i * laneH + laneH / 2;
    const name = tid === '_other' ? 'Other' : (THREAD_NAMES[tid] || tid);
    const color = tid === '_other' ? '#555' : (THREAD_COLORS[tid] || '#555');
    const label = document.createElement('div');
    label.style.cssText = `position:absolute;right:${canvasW - marginLeft + 10}px;top:${y}px;transform:translateY(-50%);` +
      `color:${color};font-size:11px;font-weight:500;white-space:nowrap;pointer-events:none;font-family:system-ui,sans-serif;`;
    label.textContent = name.length > 22 ? name.slice(0, 20) + '\u2026' : name;
    domOverlay.appendChild(label);
  });

  // X-axis container (rendered by D3 into an SVG overlay)
  const axisSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  axisSvg.style.cssText = `position:absolute;left:${marginLeft}px;top:${marginTop + topicLaneY0 + swimH + histH + forkLabelH}px;` +
    `width:${plotW}px;height:30px;overflow:visible;pointer-events:none;`;
  axisSvg.setAttribute('width', plotW);
  axisSvg.setAttribute('height', 30);
  domOverlay.appendChild(axisSvg);
  const axisG = d3.select(axisSvg).append('g');
  const xAxisFn = d3.axisBottom(xScaleOrig).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
  axisG.call(xAxisFn);
  axisG.selectAll('text').attr('fill', '#666').attr('font-size', 12);
  axisG.selectAll('.domain, .tick line').attr('stroke', '#333');
  // Store reference for zoom updates
  domOverlay._axisG = axisG;
  domOverlay._axisSvg = axisSvg;
}

function updateDomAxis() {
  if (!domOverlay?._axisG) return;
  const k = zoomTransform.k;
  const newX = zoomTransform.rescaleX(xScaleOrig);
  let axisFn;
  if (k > 4) {
    axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(1)).tickFormat(d3.timeFormat('%b %Y'));
  } else if (k > 2) {
    axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat('%b %Y'));
  } else {
    axisFn = d3.axisBottom(newX).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
  }
  domOverlay._axisG.call(axisFn);
  domOverlay._axisG.selectAll('text').attr('fill', '#666').attr('font-size', 12);
  domOverlay._axisG.selectAll('.domain, .tick line').attr('stroke', '#333');
}

// --- Zoom handler ---

function onZoom(ev) {
  zoomTransform = ev.transform;
  xScale = zoomTransform.rescaleX(xScaleOrig);
  updateLabelsForZoom(zoomTransform.k);
  updateDomAxis();
  needsBaseRedraw = true;
  needsHudRedraw = true;
}

// --- Adaptive labels ---

function updateLabelsForZoom(zoomK) {
  const baseCount = 30;
  const targetCount = Math.min(200, Math.round(baseCount + (zoomK - 1) * 15));

  const sorted = Object.values(topicMap)
    .filter(t => t._yPos !== undefined && t.inf > 0)
    .sort((a, b) => b.inf - a.inf);

  labelSet = new Set(sorted.slice(0, targetCount).map(t => t.id));
  currentLabelCount = targetCount;
}

// --- Pointer move ---

function handlePointerMove(sx, sy) {
  const st = getState();

  const hit = hitTestAllEntities(sx, sy);
  const oldHovered = hoveredEntity;

  if (hit) {
    const ref = resolveHitToEntityRef(hit);
    if (ref && (ref.type !== oldHovered?.type || ref.id !== oldHovered?.id)) {
      hoveredEntity = ref;
      hoverEntity(ref);
      baseCanvas.style.cursor = 'pointer';

      // Show tooltip
      const rect = baseCanvas.getBoundingClientRect();
      const clientX = rect.left + sx;
      const clientY = rect.top + sy;
      if (hit.type === 'topic') showTooltip(clientX, clientY, hit.entity.data);
      else if (hit.type === 'eip') showEipTooltip(clientX, clientY, hit.entity);
      else if (hit.type === 'paper') showPaperTooltip(clientX, clientY, hit.entity);
      else if (hit.type === 'magicians') showMagiciansTooltip(clientX, clientY, hit.entity);
      else if (hit.type === 'fork') showForkTooltip(clientX, clientY, hit.entity.fork);
      else if (hit.type === 'hist') showHistTooltip(clientX, clientY, hit.entity);

      // If pinned, only show tooltip — don't override highlight
      if (st.pinnedEntity) {
        needsHudRedraw = true;
        return;
      }

      // Apply hover highlight
      applyHoverHighlight(ref);
    }
  } else if (oldHovered) {
    hoveredEntity = null;
    hoverEntity(null);
    baseCanvas.style.cursor = 'default';
    hideTooltip();

    if (!st.pinnedEntity) {
      filterTimeline();
    }
    needsHudRedraw = true;
  }
}

function applyHoverHighlight(ref) {
  const st = getState();
  const indexes = getCoreIndexes();
  const hasActiveFilter = st.activeThread || st.activeAuthor || st.activeCategory || st.activeTag;
  const conns = buildPinnedConnections(ref);

  // Topics
  for (const e of topicEntities) {
    const isPinned = ref.type === 'topic' && e.data.id === ref.id;
    const isConnected = conns.connectedTopics.has(e.data.id);
    let op;
    if (isPinned) op = 1;
    else if (isConnected) op = 0.8;
    else {
      const belowThreshold = st.minInfluence > 0 && e.inf < st.minInfluence;
      if (belowThreshold) op = 0.02;
      else if (hasActiveFilter && !topicMatchesFilter(e.data, st)) op = 0.03;
      else op = 0.12;
    }
    e.opacity = op;
    e.targetOpacity = op;
  }

  // Edges
  for (const edge of edgeData) {
    const direct = (ref.type === 'topic') && (edge.source === ref.id || edge.target === ref.id);
    edge.opacity = direct ? 0.5 : 0.01;
    edge.highlighted = direct;
  }

  // EIP entities
  if (eipLayerBuilt) {
    for (const e of eipEntities) {
      const isConn = conns.connectedEips.has(Number(e.num));
      e.opacity = isConn ? 0.5 : 0.06;
    }
    for (const edge of eipEdgeData) {
      const show = conns.connectedEips.has(Number(edge.eipNum)) && conns.connectedTopics.has(Number(edge.topicId));
      edge.opacity = show ? 0.5 : 0.01;
    }
  }

  // Paper entities
  if (paperLayerBuilt) {
    for (const e of paperEntities) {
      const isConn = conns.connectedPapers.has(e.paper.id);
      e.opacity = isConn ? 0.8 : 0.04;
      if (isConn) e.boosted = true;
      else e.boosted = false;
    }
    for (const edge of paperEdgeData) {
      edge.opacity = 0.008;
    }
  }

  // Magicians entities
  if (magLayerBuilt) {
    for (const e of magEntities) {
      const isConn = conns.connectedMagicians.has(e.mtid);
      e.opacity = isConn ? 0.7 : 0.06;
    }
    for (const edge of magEdgeData) {
      const show = conns.connectedMagicians.has(edge.mtid) && conns.connectedTopics.has(Number(edge.topicId));
      edge.opacity = show ? 0.5 : 0.01;
    }
  }

  // Build hover overlay edges (topic → connected papers)
  clearPinOverlay();
  if (ref.type === 'topic' && paperLayerBuilt) {
    const curX = xScale || xScaleOrig;
    const t = topicMap[ref.id];
    if (t) {
      for (const pe of paperEntities) {
        if (!conns.connectedPapers.has(pe.paper.id)) continue;
        pinOverlayEdges.push({
          x1: curX(t._date), y1: t._yPos,
          x2: curX(pe.date), y2: pe.y,
          x1Date: t._date, x2Date: pe.date,
        });
      }
    }
  }

  needsBaseRedraw = true;
  needsHudRedraw = true;
}

// --- Filtering ---

function filterTimeline() {
  // If pinned, re-apply pinned highlight
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
  const showPosts = st.showPosts;

  // Pre-compute academic name aliases for author filter
  let authorAcademicNames = null;
  if (st.activeAuthor) {
    const eipInfo = getEips();
    const ethToEip = eipInfo?.authorLinks?.ethToEip || {};
    authorAcademicNames = (ethToEip[st.activeAuthor] || []).map(n => n.toLowerCase());
  }

  // Compute target opacities for topics
  for (const e of topicEntities) {
    if (!showPosts) { e.targetOpacity = 0; continue; }
    const d = e.data;
    const belowThreshold = st.minInfluence > 0 && e.inf < st.minInfluence;
    if (belowThreshold && hasActiveFilter) {
      e.targetOpacity = 0.03;
    } else if (belowThreshold) {
      e.targetOpacity = d.mn ? 0.25 : 0.35;
    } else if (hasActiveFilter) {
      const passesFilter = (!st.activeThread || d.th === st.activeThread) &&
        (!st.activeAuthor || d.a === st.activeAuthor) &&
        (!st.activeCategory || d.cat === st.activeCategory) &&
        (!st.activeTag || (d.tg || []).includes(st.activeTag));
      e.targetOpacity = passesFilter ? 0.85 : 0.08;
    } else {
      e.targetOpacity = d.mn ? 0.45 : 0.7;
    }
  }

  // Tween opacities
  for (const e of topicEntities) {
    addTween(e, 'opacity', e.targetOpacity, TWEEN_DURATION);
  }

  // Edge opacities
  for (const edge of edgeData) {
    if (!showPosts) { edge.opacity = 0; edge.highlighted = false; continue; }
    if (!hasActiveFilter) {
      const sT = topicMap[edge.source];
      const tT = topicMap[edge.target];
      const sBelowThresh = st.minInfluence > 0 && (sT?.inf || 0) < st.minInfluence;
      const tBelowThresh = st.minInfluence > 0 && (tT?.inf || 0) < st.minInfluence;
      edge.opacity = (sBelowThresh || tBelowThresh) ? 0.02 : 0.06;
    } else {
      const sT = topicMap[edge.source];
      const tT = topicMap[edge.target];
      if (sT && tT && topicMatchesFilter(sT, st) && topicMatchesFilter(tT, st)) edge.opacity = 0.25;
      else edge.opacity = 0.01;
    }
    edge.highlighted = false;
  }

  // Filter EIP entities
  if (eipLayerBuilt) {
    for (const e of eipEntities) {
      const eip = e.eip;
      let show = true;
      if (st.minInfluence > 0 && (eip.inf || 0) < st.minInfluence) show = false;
      if (hasActiveFilter && show) {
        if (st.activeThread && eip.th !== st.activeThread) show = false;
        if (st.activeAuthor && show) {
          if (authorAcademicNames && authorAcademicNames.length > 0) {
            const eipAuthors = (eip.au || []).map(a => (a || '').toLowerCase());
            if (!authorAcademicNames.some(name => eipAuthors.some(ea => ea === name))) show = false;
          } else {
            show = false;
          }
        }
      }
      e.opacity = show ? 0.5 : 0.05;
    }
    for (const edge of eipEdgeData) {
      edge.opacity = hasActiveFilter ? 0.03 : 0.12;
    }
  }

  // Filter paper entities (two-phase: filter then top-N selection)
  if (paperLayerBuilt) {
    const mode = st.paperLayerMode || 'focus';
    const limit = PAPER_LAYER_LIMITS[mode] || 200;
    const passing = [];
    for (const e of paperEntities) {
      const p = e.paper;
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
      if (pass) passing.push(e);
    }
    passing.sort((a, b) => (b.paper.inf || 0) - (a.paper.inf || 0));
    const visiblePaperIds = new Set(passing.slice(0, limit).map(e => e.paper.id));

    for (const e of paperEntities) {
      const show = visiblePaperIds.has(e.paper.id);
      e.opacity = show ? 0.35 : 0.02;
      e.boosted = false;
    }

    // Paper citation edges
    for (const edge of paperEdgeData) {
      const show = visiblePaperIds.has(edge.srcId) && visiblePaperIds.has(edge.tgtId);
      edge.opacity = show ? 0.12 : 0.008;
    }
  }

  // Filter magicians entities
  if (magLayerBuilt) {
    filterMagiciansEntities();
  }

  needsBaseRedraw = true;
  needsHudRedraw = true;
}

function filterMagiciansEntities() {
  const st = getState();
  const hasActiveFilter = st.activeThread || st.activeAuthor || st.activeCategory || st.activeTag;

  for (const e of magEntities) {
    let show = true;
    if (st.minInfluence > 0 && (e.inf || 0) < st.minInfluence) show = false;
    if (hasActiveFilter && show) {
      if (st.activeThread && e.thread !== st.activeThread) show = false;
      if (st.activeAuthor && e.mt.a !== st.activeAuthor) show = false;
    }
    e.opacity = show ? 0.7 : 0;
  }

  for (const edge of magEdgeData) {
    edge.opacity = (st.showPosts && !hasActiveFilter) ? 0.14 : 0;
  }
}

// --- Pinned highlight ---

function applyPinnedHighlight() {
  const st = getState();
  const pinned = st.pinnedEntity;
  if (!pinned) { clearPinOverlay(); filterTimeline(); return; }

  const conns = buildPinnedConnections(pinned);

  // Topics
  for (const e of topicEntities) {
    const isPinned = pinned.type === 'topic' && e.data.id === pinned.id;
    const isConnected = conns.connectedTopics.has(e.data.id);
    e.opacity = isPinned ? 1.0 : isConnected ? 0.8 : 0.06;
    e.targetOpacity = e.opacity;
  }

  // Edges
  for (const edge of edgeData) {
    const touching = conns.connectedTopics.has(edge.source) && conns.connectedTopics.has(edge.target);
    const direct = (pinned.type === 'topic') && (edge.source === pinned.id || edge.target === pinned.id);
    edge.opacity = direct ? 0.6 : touching ? 0.08 : 0.01;
    edge.highlighted = direct;
  }

  // EIPs
  if (eipLayerBuilt) {
    for (const e of eipEntities) {
      const isPinned = pinned.type === 'eip' && Number(e.num) === Number(pinned.id);
      const isConnected = conns.connectedEips.has(Number(e.num));
      e.opacity = isPinned ? 0.8 : isConnected ? 0.5 : 0.06;
    }
    for (const edge of eipEdgeData) {
      const show = conns.connectedEips.has(Number(edge.eipNum)) && conns.connectedTopics.has(Number(edge.topicId));
      edge.opacity = show ? 0.5 : 0.02;
    }
  }

  // Papers
  if (paperLayerBuilt) {
    const curX = xScale || xScaleOrig;
    for (const e of paperEntities) {
      const isPinned = pinned.type === 'paper' && e.paper.id === pinned.id;
      const isConnected = conns.connectedPapers.has(e.paper.id);
      e.opacity = isPinned ? 0.85 : isConnected ? 0.8 : 0.04;
      e.boosted = isPinned || isConnected;
    }
    for (const edge of paperEdgeData) {
      const direct = (pinned.type === 'paper') && (edge.srcId === pinned.id || edge.tgtId === pinned.id);
      const both = conns.connectedPapers.has(edge.srcId) && conns.connectedPapers.has(edge.tgtId);
      edge.opacity = direct ? 0.5 : both ? 0.15 : 0.01;
    }
  }

  // Magicians
  if (magLayerBuilt) {
    for (const e of magEntities) {
      const isPinned = pinned.type === 'magicians' && e.mtid === pinned.id;
      const isConnected = conns.connectedMagicians.has(e.mtid);
      e.opacity = isPinned ? 1.0 : isConnected ? 0.7 : 0.08;
    }
    for (const edge of magEdgeData) {
      const show = conns.connectedMagicians.has(edge.mtid) && conns.connectedTopics.has(Number(edge.topicId));
      edge.opacity = show ? 0.5 : 0.02;
    }
  }

  // Build pin overlay
  buildPinOverlay(pinned, conns);

  needsBaseRedraw = true;
  needsHudRedraw = true;
}

// --- Pin overlay (HUD canvas) ---

function clearPinOverlay() {
  pinOverlayEdges = [];
  pinOverlayLabels = [];
  needsHudRedraw = true;
}

function buildPinOverlay(pinned, conns) {
  clearPinOverlay();
  const curX = xScale || xScaleOrig;

  // Find pinned entity position
  let pinnedPos = null;
  if (pinned.type === 'topic') {
    const t = topicMap[pinned.id];
    if (t) pinnedPos = { x: curX(t._date), y: t._yPos, title: t.t, date: t._date, r: rScale(t.inf) };
  } else if (pinned.type === 'eip') {
    for (const e of eipEntities) {
      if (Number(e.num) === Number(pinned.id)) {
        pinnedPos = { x: curX(e.date), y: e.y, title: 'EIP-' + e.num + ': ' + (e.eip.t || ''), date: e.date, r: e.size / 2 };
        break;
      }
    }
  } else if (pinned.type === 'paper') {
    for (const e of paperEntities) {
      if (e.paper.id === pinned.id) {
        pinnedPos = { x: curX(e.date), y: e.y, title: e.paper.t || '', date: e.date, r: e.r };
        break;
      }
    }
  } else if (pinned.type === 'magicians') {
    for (const e of magEntities) {
      if (e.mtid === pinned.id) {
        pinnedPos = { x: curX(e.date), y: e.y, title: e.mt.t || '', date: e.date, r: e.r };
        break;
      }
    }
  }
  if (!pinnedPos) return;

  // Cross-entity edges (pinned → papers/topics/EIPs)
  if (paperLayerBuilt && conns.connectedPapers.size > 0 && pinned.type !== 'paper') {
    for (const pe of paperEntities) {
      if (!conns.connectedPapers.has(pe.paper.id)) continue;
      pinOverlayEdges.push({
        x1: pinnedPos.x, y1: pinnedPos.y,
        x2: curX(pe.date), y2: pe.y,
        x1Date: pinnedPos.date, x2Date: pe.date,
      });
    }
  }
  if (pinned.type === 'paper') {
    for (const e of topicEntities) {
      if (!conns.connectedTopics.has(e.data.id)) continue;
      pinOverlayEdges.push({
        x1: pinnedPos.x, y1: pinnedPos.y,
        x2: curX(e.date), y2: e.y,
        x1Date: pinnedPos.date, x2Date: e.date,
      });
    }
    if (eipLayerBuilt) {
      for (const e of eipEntities) {
        if (!conns.connectedEips.has(Number(e.num))) continue;
        pinOverlayEdges.push({
          x1: pinnedPos.x, y1: pinnedPos.y,
          x2: curX(e.date), y2: e.y,
          x1Date: pinnedPos.date, x2Date: e.date,
        });
      }
    }
  }

  // Labels
  const labelEntries = [];
  labelEntries.push({ x: pinnedPos.x, y: pinnedPos.y, r: pinnedPos.r || 5, title: pinnedPos.title, isPinned: true, date: pinnedPos.date });

  // Connected topic labels (top 12)
  const topicLabels = [];
  for (const e of topicEntities) {
    if (!conns.connectedTopics.has(e.data.id)) continue;
    if (pinned.type === 'topic' && e.data.id === pinned.id) continue;
    topicLabels.push({ x: curX(e.date), y: e.y, r: e.r, title: e.data.t, inf: e.inf, date: e.date });
  }
  topicLabels.sort((a, b) => b.inf - a.inf);
  for (const tl of topicLabels.slice(0, 12)) labelEntries.push({ ...tl, isPinned: false });

  // Connected EIP labels (top 8)
  if (eipLayerBuilt) {
    const eipLabels = [];
    for (const e of eipEntities) {
      if (!conns.connectedEips.has(Number(e.num))) continue;
      if (pinned.type === 'eip' && Number(e.num) === Number(pinned.id)) continue;
      eipLabels.push({ x: curX(e.date), y: e.y, r: e.size / 2, title: 'EIP-' + e.num, inf: e.eip.inf || 0, date: e.date });
    }
    eipLabels.sort((a, b) => b.inf - a.inf);
    for (const el of eipLabels.slice(0, 8)) labelEntries.push({ ...el, isPinned: false });
  }

  // Connected paper labels (top 6)
  if (paperLayerBuilt) {
    const paperLabels = [];
    for (const e of paperEntities) {
      if (!conns.connectedPapers.has(e.paper.id)) continue;
      if (pinned.type === 'paper' && e.paper.id === pinned.id) continue;
      paperLabels.push({ x: curX(e.date), y: e.y, r: e.r, title: e.paper.t || '', inf: e.paper.inf || 0, date: e.date });
    }
    paperLabels.sort((a, b) => b.inf - a.inf);
    for (const pl of paperLabels.slice(0, 6)) labelEntries.push({ ...pl, isPinned: false });
  }

  // Collision avoidance
  const placed = [];
  const MIN_DIST_SQ = 35 * 35;
  for (const entry of labelEntries) {
    const tooClose = placed.some(p => {
      const dx = entry.x - p.x, dy = entry.y - p.y;
      return dx * dx + dy * dy < MIN_DIST_SQ;
    });
    if (tooClose && !entry.isPinned) continue;
    placed.push(entry);
    pinOverlayLabels.push(entry);
  }

  needsHudRedraw = true;
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

  for (const e of topicEntities) {
    const inLineage = lineageSet.has(e.data.id);
    e.opacity = inLineage ? 1 : 0.04;
    e.targetOpacity = e.opacity;
    e.lineageBoosted = inLineage;
  }

  for (const edge of edgeData) {
    const key = edge.source + '->' + edge.target;
    const keyR = edge.target + '->' + edge.source;
    const inLineage = lineageEdgeSet.has(key) || lineageEdgeSet.has(keyR);
    edge.opacity = inLineage ? 0.6 : 0.01;
    edge.highlighted = inLineage;
    edge.lineage = inLineage;
  }

  needsBaseRedraw = true;
  needsHudRedraw = true;
}

// --- Milestones ---

function onMilestonesChanged({ visible }) {
  needsBaseRedraw = true;
}

// --- Selection ---

function onSelectionChanged({ current }) {
  if (current) applyPinnedHighlight();
  needsBaseRedraw = true;
}

// --- Content toggles ---

async function onContentChanged({ key }) {
  if (key === 'showPosts') {
    filterTimeline();
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
      await loadEips();
      if (getState().showPapers) buildPaperLayer();
    } else {
      removePaperLayer();
    }
  }
}

function onFiltersChangedPaperMode(changed) {
  if (changed.paperLayerMode) {
    const st = getState();
    if (st.showPapers && paperLayerBuilt) {
      paperLayerMode = st.paperLayerMode || 'focus';
      filterTimeline();
    }
  }
  if (changed.eipVisibilityMode) {
    const st = getState();
    if (st.showEips && eipLayerBuilt) {
      removeEipLayer();
      buildEipLayer();
    }
  }
  if (changed.activeAuthor) {
    filterTimeline();
  }
}

// --- EIP layer ---

function buildEipLayer() {
  if (!xScaleOrig || eipLayerBuilt) return;
  const eipDataObj = getEips();
  if (!eipDataObj?.eipCatalog) return;

  const connectedEips = new Set();
  eipToTopicMap = {};
  for (const edge of (eipDataObj.eipGraph?.edges || [])) {
    if (edge.type === 'eip_topic') {
      const eipNum = String(edge.source).replace('eip_', '');
      connectedEips.add(eipNum);
      if (!eipToTopicMap[eipNum]) eipToTopicMap[eipNum] = [];
      eipToTopicMap[eipNum].push(edge.target);
    }
  }

  const st = getState();
  const showAll = st.eipVisibilityMode === 'all';
  const catalog = eipDataObj.eipCatalog;

  eipEntities = [];
  eipEdgeData = [];

  for (const [num, eip] of Object.entries(catalog)) {
    if (!eip.cr) continue;
    if (!showAll && !connectedEips.has(num)) continue;
    const date = new Date(eip.cr);
    if (isNaN(date)) continue;

    const th = eip.th;
    const lane = (th && laneIdx[th] !== undefined) ? laneIdx[th] : laneIdx['_other'] ?? laneOrder.length - 1;
    const yBase = topicLaneY0 + lane * laneH + laneH * 0.08;
    const y = yBase + (hashCode(Number(num)) % 100) / 100 * (laneH * 0.3);
    const size = 8 + Math.min(8, (eip.inf || 0) * 12);
    const statusColor = EIP_STATUS_COLORS[eip.s] || '#555';

    eipEntities.push({
      num, eip, date, y, size, statusColor,
      opacity: 0.5,
      type: 'eip',
    });

    // Cross-ref edges
    const topicIds = eipToTopicMap[num] || [];
    for (const tid of topicIds) {
      const topic = topicMap[tid];
      if (!topic || topic._yPos === undefined) continue;
      eipEdgeData.push({
        eipNum: num, topicId: tid,
        eipDate: date, topicDate: topic._date,
        eipY: y, topicY: topic._yPos,
        opacity: 0.12,
      });
    }
  }

  eipLayerBuilt = true;
  filterTimeline();
}

function removeEipLayer() {
  eipEntities = [];
  eipEdgeData = [];
  eipLayerBuilt = false;
  needsBaseRedraw = true;
}

// --- Paper layer ---

function buildPaperLayer() {
  if (!xScaleOrig) return;
  const paperDataObj = getPapers();
  if (!paperDataObj?.papers) return;

  const allPapers = Object.values(paperDataObj.papers);
  paperEntities = [];
  paperEdgeData = [];

  const paperPos = {};
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

    const color = p.th ? (THREAD_COLORS[p.th] || '#2f4f77') : '#2f4f77';
    paperEntities.push({
      paper: p, date, y, r, color,
      opacity: 0.4,
      boosted: false,
      type: 'paper',
    });
  });

  // Citation edges
  const pgEdges = paperDataObj.paperGraph?.edges || [];
  for (const edge of pgEdges) {
    const src = paperPos[edge.source];
    const tgt = paperPos[edge.target];
    if (!src || !tgt) continue;
    paperEdgeData.push({
      srcId: edge.source, tgtId: edge.target,
      srcDate: src.date, srcY: src.y,
      tgtDate: tgt.date, tgtY: tgt.y,
      opacity: 0.12,
    });
  }

  paperLayerBuilt = true;
  paperLayerMode = getState().paperLayerMode || 'focus';
  filterTimeline();
}

function removePaperLayer() {
  paperEntities = [];
  paperEdgeData = [];
  paperLayerBuilt = false;
  paperLayerMode = null;
  needsBaseRedraw = true;
}

// --- Magicians layer ---

function buildMagiciansLayer() {
  if (!xScaleOrig || magLayerBuilt) return;
  const graphData = getGraph();
  if (!graphData?.magiciansTopics) return;

  const magTopics = graphData.magiciansTopics;
  let maxMagInf = 0;
  const magEntryList = [];

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
    magEntryList.push({ mtid: Number(mtid), mt, date, inf, thread, y });
  }

  const magRScale = d3.scaleSqrt().domain([0, maxMagInf || 1]).range([3, 11]);

  magEntities = [];
  magEdgeData = [];

  for (const entry of magEntryList) {
    const r = magRScale(entry.inf);
    const color = (entry.thread && THREAD_COLORS[entry.thread]) ? THREAD_COLORS[entry.thread] : '#bb88cc';

    magEntities.push({
      mtid: entry.mtid, mt: entry.mt,
      date: entry.date, y: entry.y,
      inf: entry.inf, thread: entry.thread,
      r, color,
      opacity: 0.7,
      type: 'magicians',
    });

    // Cross-ref edges
    for (const tid of (entry.mt.er || [])) {
      const topic = topicMap[tid];
      if (!topic || topic._yPos === undefined) continue;
      magEdgeData.push({
        mtid: entry.mtid, topicId: tid,
        magDate: entry.date, topicDate: topic._date,
        magY: entry.y, topicY: topic._yPos,
        opacity: 0.14,
      });
    }
  }

  magLayerBuilt = true;
  filterMagiciansEntities();
  needsBaseRedraw = true;
}

function removeMagiciansLayer() {
  magEntities = [];
  magEdgeData = [];
  magLayerBuilt = false;
  needsBaseRedraw = true;
}

// --- Reset ---

function onReset() {
  if (baseCanvas && zoomBehavior) {
    d3.select(baseCanvas).transition().duration(300).call(zoomBehavior.transform, d3.zoomIdentity);
  }
  removeEipLayer();
  removePaperLayer();
  removeMagiciansLayer();
  clearPinOverlay();

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

// === RENDER ===

function renderLoop() {
  const tweenActive = tickTweens();
  if (tweenActive) {
    needsBaseRedraw = true;
  }

  if (needsBaseRedraw) {
    needsBaseRedraw = false;
    drawBase();
  }
  if (needsHudRedraw) {
    needsHudRedraw = false;
    drawHud();
  }
  rafId = requestAnimationFrame(renderLoop);
}

function drawBase() {
  if (!baseCtx) return;
  const ctx = baseCtx;
  const w = canvasW;
  const h = canvasH;

  ctx.save();
  ctx.clearRect(0, 0, w, h);

  // 1. Background
  ctx.fillStyle = '#0a0a0f';
  ctx.fillRect(0, 0, w, h);

  // Translate to plot area
  ctx.save();
  ctx.translate(marginLeft, marginTop);

  const curX = xScale || xScaleOrig;
  const st = getState();
  const showPosts = st.showPosts;

  // 2. Era background rects
  for (const era of eraData) {
    const x0 = curX(era.start);
    const x1 = curX(era.end);
    ctx.fillStyle = era.color;
    ctx.fillRect(x0, 0, Math.max(0, x1 - x0), topicLaneY0 + swimH);
  }

  // Era labels
  ctx.font = '10px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = '#555';
  for (const era of eraData) {
    const x0 = curX(era.start);
    const x1 = curX(era.end);
    ctx.fillText(era.name, (x0 + x1) / 2, -8);
  }

  // Lane separators
  ctx.strokeStyle = '#1a1a2a';
  ctx.lineWidth = 0.5;
  for (let i = 1; i < laneOrder.length; i++) {
    const y = topicLaneY0 + i * laneH;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(plotW, y);
    ctx.stroke();
  }

  // 3. Fork lines (dashed)
  ctx.setLineDash([6, 4]);
  ctx.strokeStyle = 'rgba(255, 204, 0, 0.25)';
  ctx.lineWidth = 1;
  for (const f of forkData) {
    const fx = curX(f.date);
    ctx.beginPath();
    ctx.moveTo(fx, -5);
    ctx.lineTo(fx, topicLaneY0 + swimH + histH);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Fork labels
  ctx.font = '10px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = '#cc9933';
  ctx.strokeStyle = '#0a0a0f';
  ctx.lineWidth = 3;
  for (const f of forkData) {
    const fx = curX(f.date);
    const y = topicLaneY0 + swimH + histH + 15;
    ctx.strokeText(f.displayName, fx, y);
    ctx.fillText(f.displayName, fx, y);
  }

  // 4. ethresear.ch live line
  if (liveLineDate) {
    const lx = curX(liveLineDate);
    ctx.setLineDash([6, 3]);
    ctx.strokeStyle = 'rgba(90, 138, 90, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(lx, -5);
    ctx.lineTo(lx, topicLaneY0 + swimH + histH);
    ctx.stroke();
    ctx.setLineDash([]);

    // Label
    ctx.font = '600 10px system-ui, sans-serif';
    ctx.fillStyle = '#6aaa6a';
    ctx.textAlign = 'center';
    ctx.strokeStyle = '#0a0a0f';
    ctx.lineWidth = 3;
    ctx.strokeText('ethresear.ch live', lx, -12);
    ctx.fillText('ethresear.ch live', lx, -12);
  }

  // 5. Citation edges (batch)
  if (showPosts) {
    for (const edge of edgeData) {
      if (edge.opacity < 0.005) continue;
      const x1 = curX(edge.sd);
      const x2 = curX(edge.td);
      // Viewport culling
      if (x1 < -50 && x2 < -50) continue;
      if (x1 > plotW + 50 && x2 > plotW + 50) continue;

      if (edge.highlighted || edge.lineage) {
        ctx.strokeStyle = hexWithAlpha('#88aaff', Math.min(edge.opacity, 0.8));
        ctx.lineWidth = 2;
      } else {
        ctx.strokeStyle = hexWithAlpha('#556688', edge.opacity);
        ctx.lineWidth = 1;
      }
      ctx.beginPath();
      ctx.moveTo(x1, edge.sy);
      ctx.lineTo(x2, edge.ty);
      ctx.stroke();

      // Arrow for highlighted edges
      if (edge.highlighted || edge.lineage) {
        drawArrow(ctx, x1, edge.sy, x2, edge.ty, 5,
          edge.lineage ? '#88aaff' : 'rgba(136,170,255,0.8)');
      }
    }
  }

  // EIP cross-ref edges
  if (eipLayerBuilt) {
    ctx.setLineDash([4, 3]);
    for (const edge of eipEdgeData) {
      if (edge.opacity < 0.01) continue;
      ctx.strokeStyle = hexWithAlpha('#7788cc', edge.opacity);
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(curX(edge.eipDate), edge.eipY);
      ctx.lineTo(curX(edge.topicDate), edge.topicY);
      ctx.stroke();
    }
    ctx.setLineDash([]);
  }

  // Paper citation edges
  if (paperLayerBuilt) {
    for (const edge of paperEdgeData) {
      if (edge.opacity < 0.005) continue;
      ctx.strokeStyle = hexWithAlpha('#8fb7ef', edge.opacity);
      ctx.lineWidth = edge.opacity > 0.1 ? 0.6 : 0.3;
      ctx.beginPath();
      ctx.moveTo(curX(edge.srcDate), edge.srcY);
      ctx.lineTo(curX(edge.tgtDate), edge.tgtY);
      ctx.stroke();
    }
  }

  // Magicians cross-ref edges
  if (magLayerBuilt) {
    ctx.setLineDash([3, 3]);
    for (const edge of magEdgeData) {
      if (edge.opacity < 0.01) continue;
      ctx.strokeStyle = hexWithAlpha('#9b72c2', edge.opacity);
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.moveTo(curX(edge.magDate), edge.magY);
      ctx.lineTo(curX(edge.topicDate), edge.topicY);
      ctx.stroke();
    }
    ctx.setLineDash([]);
  }

  // 6. Histogram bars
  const histY0 = topicLaneY0 + swimH;
  // Compute bar width from zoomed scale (1 month width)
  const zoomedBarW = Math.max(1, (curX(new Date(2020, 1, 1)) - curX(new Date(2020, 0, 1))) * 0.85);
  for (const d of histData) {
    const x = curX(d.date);
    ctx.fillStyle = 'rgba(85, 102, 136, 0.25)';
    ctx.fillRect(x, histY0 + histH - d.h, zoomedBarW, d.h);
  }

  // 7. Topic circles — use globalAlpha for element-level opacity (matches SVG behavior,
  // prevents alpha accumulation in overlapping regions)
  if (showPosts) {
    // Minor topics first (behind normal)
    for (const e of topicEntities) {
      if (!e.isMinor) continue;
      if (e.opacity < 0.01) continue;
      const cx = curX(e.date);
      if (cx < -20 || cx > plotW + 20) continue;

      const r = e.lineageBoosted ? e.r * 1.2 : e.r;
      ctx.globalAlpha = e.opacity * 0.8;
      ctx.beginPath();
      ctx.arc(cx, e.y, r, 0, Math.PI * 2);
      ctx.fillStyle = e.color || '#888';
      ctx.fill();
      // Dashed stroke for minor
      ctx.globalAlpha = e.opacity;
      ctx.setLineDash([3, 2]);
      ctx.strokeStyle = e.color || '#888';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.globalAlpha = 1;

    // Normal topics
    for (const e of topicEntities) {
      if (e.isMinor) continue;
      if (e.opacity < 0.01) continue;
      const cx = curX(e.date);
      if (cx < -20 || cx > plotW + 20) continue;

      const r = e.lineageBoosted ? e.r * 1.2 : e.r;
      ctx.globalAlpha = e.opacity;
      ctx.beginPath();
      ctx.arc(cx, e.y, r, 0, Math.PI * 2);
      ctx.fillStyle = e.color || '#888';
      ctx.fill();
      ctx.strokeStyle = e.color || '#888';
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Selected topic stroke
    const selected = st.selectedEntity;
    if (selected?.type === 'topic') {
      const idx = entityById[selected.id];
      if (idx !== undefined) {
        const e = topicEntities[idx];
        const cx = curX(e.date);
        ctx.beginPath();
        ctx.arc(cx, e.y, e.r + 2, 0, Math.PI * 2);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    }
  }

  // 8. EIP squares — globalAlpha for element-level opacity
  if (eipLayerBuilt) {
    for (const e of eipEntities) {
      if (e.opacity < 0.02) continue;
      const cx = curX(e.date);
      if (cx < -20 || cx > plotW + 20) continue;
      const half = e.size / 2;
      ctx.globalAlpha = e.opacity;
      drawRoundedRect(ctx, cx - half, e.y - half, e.size, e.size, 3,
        e.statusColor || '#888',
        e.statusColor || '#888',
        0.8);
    }
    ctx.globalAlpha = 1;
  }

  // 9. Paper diamonds — globalAlpha for element-level opacity
  if (paperLayerBuilt) {
    for (const e of paperEntities) {
      if (e.opacity < 0.01) continue;
      const cx = curX(e.date);
      if (cx < -20 || cx > plotW + 20) continue;
      const r = e.boosted ? Math.max(7, e.r * 1.6) : e.r;
      const strokeC = e.boosted ? '#fff' : e.color;
      const strokeW = e.boosted ? 1.5 : 0.6;
      ctx.globalAlpha = e.opacity;
      drawDiamond(ctx, cx, e.y, r * 2,
        e.color || '#2f4f77',
        strokeC || '#2f4f77',
        strokeW);
    }
    ctx.globalAlpha = 1;
  }

  // 10. Magicians triangles — globalAlpha for element-level opacity
  if (magLayerBuilt) {
    for (const e of magEntities) {
      if (e.opacity < 0.01) continue;
      const cx = curX(e.date);
      if (cx < -20 || cx > plotW + 20) continue;
      ctx.globalAlpha = e.opacity;
      drawTriangle(ctx, cx, e.y, e.r * 2,
        e.color || '#bb88cc',
        e.color || '#bb88cc',
        0.5);
    }
    ctx.globalAlpha = 1;
  }

  // 11. Milestone stars
  if (st.milestonesVisible && showPosts) {
    for (const md of milestoneData) {
      const t = md.topic;
      if (t._yPos === undefined) continue;
      const idx = entityById[t.id];
      if (idx !== undefined && topicEntities[idx].opacity < 0.25) continue;
      const cx = curX(t._date);
      if (cx < -20 || cx > plotW + 20) continue;
      const r = rScale(t.inf) + 4;
      const color = THREAD_COLORS[md.threadId] || '#ffcc00';
      ctx.globalAlpha = 0.6;
      drawStar(ctx, cx, t._yPos, r, r * 0.5, 4,
        color,
        'rgba(255,255,255,0.8)',
        1);
    }
    ctx.globalAlpha = 1;
  }

  // 12. Topic labels
  if (showPosts) {
    ctx.font = '10px system-ui, sans-serif';
    ctx.textAlign = 'left';
    for (const e of topicEntities) {
      if (!labelSet.has(e.data.id)) continue;
      if (e.opacity < 0.25) continue;
      const cx = curX(e.date);
      if (cx < -50 || cx > plotW + 50) continue;

      const maxChars = 28;
      const title = e.data.t || '';
      const txt = title.length > maxChars ? title.slice(0, maxChars - 1) + '\u2026' : title;
      const lx = cx + e.r + 3;
      const ly = e.y + 3;
      const alpha = Math.min(e.opacity + 0.05, 0.9);

      // Text outline for readability
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = '#0a0a0f';
      ctx.lineWidth = 3;
      ctx.strokeText(txt, lx, ly);
      ctx.fillStyle = '#ddd';
      ctx.fillText(txt, lx, ly);
    }
    ctx.globalAlpha = 1;
  }

  // EIP labels (top 12 by influence)
  if (eipLayerBuilt) {
    const sorted = eipEntities.slice().sort((a, b) => (b.eip.inf || 0) - (a.eip.inf || 0));
    ctx.font = '9px system-ui, sans-serif';
    let eipLabelCount = 0;
    for (const e of sorted) {
      if (eipLabelCount >= 12) break;
      if (e.opacity < 0.2) continue;
      const cx = curX(e.date);
      if (cx < -50 || cx > plotW + 50) continue;
      const txt = 'EIP-' + e.num;
      const lx = cx + e.size / 2 + 3;
      const ly = e.y + 3;
      ctx.globalAlpha = e.opacity;
      ctx.strokeStyle = '#0a0a0f';
      ctx.lineWidth = 3;
      ctx.strokeText(txt, lx, ly);
      ctx.fillStyle = '#aabbcc';
      ctx.fillText(txt, lx, ly);
      eipLabelCount++;
    }
    ctx.globalAlpha = 1;
  }

  // Magicians labels (top 12 by engagement)
  if (magLayerBuilt) {
    const sorted = magEntities.slice().sort((a, b) => (b.inf || 0) - (a.inf || 0));
    ctx.font = '8px system-ui, sans-serif';
    let magLabelCount = 0;
    for (const e of sorted) {
      if (magLabelCount >= 12) break;
      if (e.opacity < 0.3) continue;
      const cx = curX(e.date);
      if (cx < -50 || cx > plotW + 50) continue;
      const title = e.mt.t || '';
      const txt = title.length > 28 ? title.slice(0, 27) + '\u2026' : title;
      const lx = cx + e.r + 3;
      const ly = e.y + 3;
      ctx.strokeStyle = '#0a0a0f';
      ctx.lineWidth = 2;
      ctx.strokeText(txt, lx, ly);
      ctx.fillStyle = '#c8b5db';
      ctx.fillText(txt, lx, ly);
      magLabelCount++;
    }
  }

  ctx.restore(); // plot area
  ctx.restore(); // global
}

function drawHud() {
  if (!hudCtx) return;
  const ctx = hudCtx;
  ctx.clearRect(0, 0, canvasW, canvasH);

  if (pinOverlayEdges.length === 0 && pinOverlayLabels.length === 0) return;

  ctx.save();
  ctx.translate(marginLeft, marginTop);

  const curX = xScale || xScaleOrig;

  // Pin overlay edges
  ctx.setLineDash([4, 2]);
  ctx.strokeStyle = 'rgba(142, 184, 255, 0.5)';
  ctx.lineWidth = 1.2;
  for (const edge of pinOverlayEdges) {
    const x1 = curX(edge.x1Date);
    const x2 = curX(edge.x2Date);
    ctx.beginPath();
    ctx.moveTo(x1, edge.y1);
    ctx.lineTo(x2, edge.y2);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Pin overlay labels
  for (const entry of pinOverlayLabels) {
    const x = curX(entry.date) + (entry.r || 5) + 4;
    const y = entry.y + 3;
    const txt = entry.title.length > 35 ? entry.title.slice(0, 34) + '\u2026' : entry.title;

    ctx.font = entry.isPinned ? 'bold 11px system-ui, sans-serif' : '9px system-ui, sans-serif';
    ctx.strokeStyle = '#0a0a0f';
    ctx.lineWidth = 3;
    ctx.textAlign = 'left';
    ctx.strokeText(txt, x, y);
    ctx.fillStyle = entry.isPinned ? '#fff' : '#ccc';
    ctx.globalAlpha = entry.isPinned ? 1.0 : 0.85;
    ctx.fillText(txt, x, y);
    ctx.globalAlpha = 1;
  }

  ctx.restore();
}

// --- Exports ---

export function onActivate() {
  filterTimeline();
  needsBaseRedraw = true;
  needsHudRedraw = true;
}
