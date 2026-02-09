// network.js — Canvas citation network view
// Renders unified graph (topics, EIPs, forks, magicians, papers) with
// force-directed layout, viewport culling, edge LOD, quadtree hit-testing,
// and Shift+click BFS path finding.

import { THREAD_COLORS, NETWORK_ZOOM_EXTENT, EIP_STATUS_COLORS } from './constants.js';
import { getState, on, selectEntity, hoverEntity, setPath } from './state.js';
import { getCore, getGraph, getGraphIndexes, loadGraph, getPapers } from './data.js';
import {
  setupCanvas, observeResize, findNodeAtPoint,
  drawCircle, drawRoundedRect, drawDiamond, drawTriangle,
  drawArrow, getVisibleNodes,
} from './canvas-utils.js';

let canvas = null;
let ctx = null;
let simulation = null;
let nodes = [];
let edges = [];
let transform = d3.zoomIdentity;
let width = 0;
let height = 0;
let needsRedraw = true;
let rafId = null;
let quadtree = null;
let quadtreeDirty = true;
let hoveredNode = null;
let dragTarget = null;
let initialized = false;

// Pre-sorted edge groups for batch rendering
let edgeGroups = {};

// Per-node adjacency for fast connection lookups
const nodeEdgeIndex = {};

// Influence-sorted nodes for label rendering
let labelCandidates = [];

// Paper augmentation state
let paperNodesAdded = false;
let paperNodeIds = new Set();
let currentPaperMode = null;
const PAPER_LAYER_LIMITS = { focus: 200, context: 400, broad: 651 };

// rScale for node sizing — computed once after data load
let rScale = null;
let maxInfluence = 1;

// Edge type rendering config
const EDGE_STYLES = {
  topic_citation: { color: 'rgba(85, 102, 136, 0.15)', width: 0.5, dash: null },
  eip_topic:      { color: 'rgba(136, 170, 204, 0.2)',  width: 0.5, dash: [4, 3] },
  eip_requires:   { color: 'rgba(136, 170, 204, 0.15)', width: 0.5, dash: [4, 3] },
  paper_cites:    { color: 'rgba(140, 180, 230, 0.1)',   width: 0.3, dash: null, minZoom: 0.8 },
  paper_related:  { color: 'rgba(140, 180, 230, 0.09)',  width: 0.3, dash: [2, 2], minZoom: 0.6 },
  fork_topic:     { color: 'rgba(255, 204, 0, 0.15)',    width: 0.5, dash: [3, 3] },
  topic_magicians:{ color: 'rgba(187, 136, 204, 0.15)',  width: 0.4, dash: [2, 3] },
  eip_magicians:  { color: 'rgba(187, 136, 204, 0.15)',  width: 0.4, dash: [5, 3] },
  _default:       { color: 'rgba(80, 80, 120, 0.1)',     width: 0.4, dash: null },
};

export function init() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('network-view');
  if (!container) return;

  canvas = document.createElement('canvas');
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  container.appendChild(canvas);

  const core = getCore();
  const graph = getGraph();
  if (!graph?.unifiedGraph) return;

  // Build node array with warm-start positions
  const warmPositions = core?.warmPositions || {};
  const nodeMap = {};

  for (const n of (graph.unifiedGraph.nodes || [])) {
    const pos = warmPositions[String(n.id)];
    const node = {
      ...n,
      x: pos ? pos.x * 1000 : (Math.random() - 0.5) * 800 + 500,
      y: pos ? pos.y * 700 : (Math.random() - 0.5) * 600 + 350,
    };
    nodes.push(node);
    nodeMap[String(n.id)] = node;
  }

  // Build edges, resolve endpoints, build adjacency index
  for (const e of (graph.unifiedGraph.edges || [])) {
    const srcKey = String(e.source);
    const tgtKey = String(e.target);
    const src = nodeMap[srcKey];
    const tgt = nodeMap[tgtKey];
    if (!src || !tgt) continue;

    const edge = { ...e, source: src, target: tgt };
    edges.push(edge);

    // Adjacency index
    if (!nodeEdgeIndex[srcKey]) nodeEdgeIndex[srcKey] = [];
    nodeEdgeIndex[srcKey].push(edge);
    if (!nodeEdgeIndex[tgtKey]) nodeEdgeIndex[tgtKey] = [];
    nodeEdgeIndex[tgtKey].push(edge);
  }

  // Pre-sort edges into type groups for batch drawing
  rebuildEdgeGroups();

  // Compute scales
  maxInfluence = 0;
  for (const n of nodes) {
    if ((n.influence || 0) > maxInfluence) maxInfluence = n.influence;
  }
  if (maxInfluence === 0) maxInfluence = 1;
  rScale = (inf) => Math.max(3, Math.sqrt(inf / maxInfluence) * 16);

  // Pre-compute label candidates (top 20 non-fork, non-paper nodes by influence)
  labelCandidates = nodes
    .filter(n => (n.sourceType || 'topic') !== 'fork' && (n.sourceType || 'topic') !== 'paper' && n.influence)
    .sort((a, b) => (b.influence || 0) - (a.influence || 0))
    .slice(0, 20);

  // Setup canvas
  width = container.clientWidth || 1200;
  height = container.clientHeight || 700;
  ({ ctx } = setupCanvas(canvas, width, height));

  // ResizeObserver
  observeResize(container, canvas, (w, h, c) => {
    width = w;
    height = h;
    ctx = c;
    needsRedraw = true;
  });

  // Force simulation
  simulation = d3.forceSimulation(nodes)
    .alphaDecay(0.05)
    .force('charge', d3.forceManyBody().strength(-30).distanceMax(300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('link', d3.forceLink(edges).id(d => String(d.id)).distance(60).strength(0.1))
    .force('collide', d3.forceCollide().radius(d => {
      if ((d.sourceType || 'topic') === 'fork') return 10;
      const r = rScale(d.influence || 0);
      return r + 2;
    }))
    .on('tick', () => {
      needsRedraw = true;
      quadtreeDirty = true;
    })
    .on('end', () => {
      quadtreeDirty = true;
    });

  // Zoom
  const zoomBehavior = d3.zoom()
    .scaleExtent(NETWORK_ZOOM_EXTENT)
    .on('zoom', (event) => {
      transform = event.transform;
      needsRedraw = true;
    });

  d3.select(canvas)
    .call(zoomBehavior)
    .on('dblclick.zoom', null); // disable double-click zoom

  // Prevent macOS swipe-back
  canvas.addEventListener('wheel', (e) => { e.preventDefault(); }, { passive: false });
  canvas.style.touchAction = 'none';

  // Drag behavior
  setupDrag(zoomBehavior);

  // Pointer move — debounced quadtree hit-test
  let pointerRafPending = false;
  let lastPointerX = 0;
  let lastPointerY = 0;

  canvas.addEventListener('pointermove', (event) => {
    lastPointerX = event.offsetX;
    lastPointerY = event.offsetY;
    if (!pointerRafPending && !dragTarget) {
      pointerRafPending = true;
      requestAnimationFrame(() => {
        pointerRafPending = false;
        if (dragTarget) return;
        const [mx, my] = transform.invert([lastPointerX, lastPointerY]);
        ensureQuadtree();
        const found = findNodeAtPoint(quadtree, mx, my, 20 / transform.k);
        if (found !== hoveredNode) {
          hoveredNode = found;
          needsRedraw = true;
          if (found) {
            hoverEntity({ type: found.sourceType || 'topic', id: found.id });
            canvas.style.cursor = 'pointer';
            showNetworkTooltip(lastPointerX, lastPointerY, found);
          } else {
            hoverEntity(null);
            canvas.style.cursor = 'default';
            hideNetworkTooltip();
          }
        }
      });
    }
  });

  // Click — entity selection + Shift+click path finding
  canvas.addEventListener('click', (event) => {
    if (dragTarget) return;
    const [mx, my] = transform.invert([event.offsetX, event.offsetY]);
    ensureQuadtree();
    const found = findNodeAtPoint(quadtree, mx, my, 20 / transform.k);
    if (!found) return;

    if (event.shiftKey) {
      // BFS path finding from pinned topic
      const st = getState();
      const startId = st.pinnedTopicId;
      if (startId && String(found.id) !== String(startId)) {
        const pathResult = bfsPath(String(startId), String(found.id), 8);
        if (pathResult) {
          setPath(true, startId, pathResult.nodeSet, pathResult.edgeSet);
        }
      }
    } else {
      selectEntity({ type: found.sourceType || 'topic', id: found.id });
    }
  });

  // Listen for state changes
  on('filters:changed', onFiltersChanged);
  on('selection:changed', () => { needsRedraw = true; });
  on('content:changed', onContentChanged);
  on('path:changed', () => { needsRedraw = true; });
  on('lineage:changed', () => { needsRedraw = true; });

  // Start render loop
  renderLoop();
}

function setupDrag(zoomBehavior) {
  let dragStartX = 0;
  let dragStartY = 0;

  const drag = d3.drag()
    .container(canvas)
    .subject((event) => {
      const [mx, my] = transform.invert([event.x, event.y]);
      ensureQuadtree();
      const found = findNodeAtPoint(quadtree, mx, my, 20 / transform.k);
      if (found) {
        found.x = transform.applyX(found.x);
        found.y = transform.applyY(found.y);
        return found;
      }
      return null;
    })
    .on('start', (event) => {
      if (!event.subject) return;
      dragTarget = event.subject;
      simulation.alphaTarget(0.3).restart();
      const [wx, wy] = transform.invert([event.x, event.y]);
      dragTarget.fx = wx;
      dragTarget.fy = wy;
      dragStartX = event.x;
      dragStartY = event.y;
    })
    .on('drag', (event) => {
      if (!dragTarget) return;
      const [wx, wy] = transform.invert([event.x, event.y]);
      dragTarget.fx = wx;
      dragTarget.fy = wy;
    })
    .on('end', (event) => {
      if (!dragTarget) return;
      simulation.alphaTarget(0);
      dragTarget.fx = null;
      dragTarget.fy = null;
      dragTarget = null;
      quadtreeDirty = true;
    });

  d3.select(canvas).call(drag).call(zoomBehavior);
}

function rebuildEdgeGroups() {
  edgeGroups = {};
  for (const edge of edges) {
    const type = edge.type || '_default';
    if (!edgeGroups[type]) edgeGroups[type] = [];
    edgeGroups[type].push(edge);
  }
}

function ensureQuadtree() {
  if (quadtreeDirty || !quadtree) {
    quadtree = d3.quadtree()
      .x(d => d.x)
      .y(d => d.y)
      .addAll(nodes);
    quadtreeDirty = false;
  }
}

function renderLoop() {
  if (needsRedraw) {
    needsRedraw = false;
    draw();
  }
  rafId = requestAnimationFrame(renderLoop);
}

// --- BFS path finding (max depth hops) ---
function bfsPath(startId, endId, maxDepth) {
  const visited = new Set();
  const parent = {};
  const parentEdge = {};
  const queue = [{ id: startId, depth: 0 }];
  visited.add(startId);

  while (queue.length > 0) {
    const { id, depth } = queue.shift();
    if (id === endId) {
      // Reconstruct path
      const nodeSet = new Set();
      const edgeSet = new Set();
      let cur = endId;
      while (cur) {
        nodeSet.add(cur);
        if (parentEdge[cur]) edgeSet.add(parentEdge[cur]);
        cur = parent[cur];
      }
      return { nodeSet, edgeSet };
    }
    if (depth >= maxDepth) continue;

    const neighbors = nodeEdgeIndex[id] || [];
    for (const edge of neighbors) {
      const srcId = String(edge.source.id ?? edge.source);
      const tgtId = String(edge.target.id ?? edge.target);
      const neighborId = srcId === id ? tgtId : srcId;
      if (!visited.has(neighborId)) {
        visited.add(neighborId);
        parent[neighborId] = id;
        parentEdge[neighborId] = edge;
        queue.push({ id: neighborId, depth: depth + 1 });
      }
    }
  }
  return null; // no path found
}

// --- Visibility helpers ---
function nodeMatchesFilter(node, st) {
  const type = node.sourceType || 'topic';

  // Content toggles
  if (type === 'eip' && !st.showEips) return false;
  if (type === 'magicians' && !st.showMagicians) return false;
  if (type === 'paper' && !st.showPapers) return false;

  // EIP visibility mode
  if (type === 'eip' && st.eipVisibilityMode === 'connected') {
    const graphIndexes = getGraphIndexes();
    const connectedEips = graphIndexes?.connectedEipNodeIds;
    if (connectedEips && !connectedEips.has(String(node.id))) return false;
  }

  // Thread filter
  if (st.activeThread && node.thread && node.thread !== st.activeThread) return false;

  // Influence filter
  if (st.minInfluence > 0 && (node.influence || 0) < st.minInfluence) return false;

  // Author filter
  if (st.activeAuthor && type === 'topic') {
    const author = node.author || '';
    const coauthors = node.coauthors || [];
    if (author !== st.activeAuthor && !coauthors.includes(st.activeAuthor)) return false;
  }

  return true;
}

function getNodeRadius(node) {
  const type = node.sourceType || 'topic';
  if (type === 'fork') return 7;
  const inf = node.influence || 0;
  if (type === 'paper') return Math.max(4, rScale(inf) * 0.78);
  return rScale(inf);
}

function getNodeColor(node) {
  const type = node.sourceType || 'topic';
  if (type === 'fork') return '#ffcc00';
  if (type === 'eip') return THREAD_COLORS[node.thread] || EIP_STATUS_COLORS[node.status] || '#555';
  if (type === 'paper') return THREAD_COLORS[node.thread] || '#2f4f77';
  if (type === 'magicians') return THREAD_COLORS[node.thread] || '#bb88cc';
  return THREAD_COLORS[node.thread] || '#666';
}

// --- Main draw ---
function draw() {
  if (!ctx) return;
  const w = width;
  const h = height;

  ctx.save();
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#0a0a0f';
  ctx.fillRect(0, 0, w, h);

  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);

  const st = getState();
  const selectedId = st.selectedEntity?.id;
  const selectedType = st.selectedEntity?.type;
  const zoom = transform.k;

  // Path highlight state
  const pathActive = st.pathMode;
  const pathNodeSet = st.pathSet;
  const pathEdgeSet = st.pathEdgeSet;

  // Lineage state
  const lineageActive = st.lineageActive;
  const lineageSet = st.lineageSet;

  // Get visible nodes for viewport culling
  const visibleNodes = getVisibleNodes(nodes, transform, w, h, 100);
  const visibleIdSet = new Set();
  for (const n of visibleNodes) visibleIdSet.add(String(n.id));

  // Determine connected set for hover/selection highlighting
  const focusId = hoveredNode ? String(hoveredNode.id) : (selectedId ? String(selectedId) : null);
  let connectedSet = null;
  if (focusId) {
    connectedSet = new Set();
    connectedSet.add(focusId);
    const adj = nodeEdgeIndex[focusId] || [];
    for (const edge of adj) {
      const srcId = String(edge.source.id ?? edge.source);
      const tgtId = String(edge.target.id ?? edge.target);
      connectedSet.add(srcId);
      connectedSet.add(tgtId);
    }
  }

  // --- Draw edges (batched by type) ---
  for (const [type, group] of Object.entries(edgeGroups)) {
    const style = EDGE_STYLES[type] || EDGE_STYLES._default;

    // LOD: skip certain edge types at low zoom
    if (style.minZoom && zoom < style.minZoom) continue;

    ctx.strokeStyle = style.color;
    ctx.lineWidth = style.width;
    if (style.dash) {
      ctx.setLineDash(style.dash);
    } else {
      ctx.setLineDash([]);
    }

    ctx.beginPath();
    for (const edge of group) {
      const src = edge.source;
      const tgt = edge.target;
      const srcId = String(src.id ?? src);
      const tgtId = String(tgt.id ?? tgt);

      // Viewport culling
      if (!visibleIdSet.has(srcId) && !visibleIdSet.has(tgtId)) continue;

      // When path or lineage is active, only draw edges in the sets
      if (pathActive && !pathEdgeSet.has(edge)) continue;

      const sx = src.x || 0;
      const sy = src.y || 0;
      const tx = tgt.x || 0;
      const ty = tgt.y || 0;

      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
    }
    ctx.stroke();
  }

  ctx.setLineDash([]);

  // --- Draw highlighted edges for hovered/selected node ---
  if (focusId && !pathActive) {
    const adj = nodeEdgeIndex[focusId] || [];
    if (adj.length > 0 && adj.length < 200) {
      ctx.strokeStyle = 'rgba(136, 170, 255, 0.5)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (const edge of adj) {
        const sx = edge.source.x || 0;
        const sy = edge.source.y || 0;
        const tx = edge.target.x || 0;
        const ty = edge.target.y || 0;
        ctx.moveTo(sx, sy);
        ctx.lineTo(tx, ty);
      }
      ctx.stroke();

      // Conditional arrows — only for focused node's edges (max ~50)
      const arrowEdges = adj.length > 50 ? adj.slice(0, 50) : adj;
      for (const edge of arrowEdges) {
        drawArrow(ctx,
          edge.source.x || 0, edge.source.y || 0,
          edge.target.x || 0, edge.target.y || 0,
          6, '#88aaff');
      }
    }
  }

  // --- Draw path edges highlighted ---
  if (pathActive && pathEdgeSet.size > 0) {
    ctx.strokeStyle = 'rgba(255, 200, 80, 0.7)';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    for (const edge of pathEdgeSet) {
      const sx = edge.source?.x || 0;
      const sy = edge.source?.y || 0;
      const tx = edge.target?.x || 0;
      const ty = edge.target?.y || 0;
      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
    }
    ctx.stroke();

    for (const edge of pathEdgeSet) {
      drawArrow(ctx,
        edge.source?.x || 0, edge.source?.y || 0,
        edge.target?.x || 0, edge.target?.y || 0,
        7, '#ffc850');
    }
  }

  // --- Draw nodes ---
  for (const node of visibleNodes) {
    const type = node.sourceType || 'topic';
    const color = getNodeColor(node);
    const isSelected = String(node.id) === String(selectedId);
    const isHovered = node === hoveredNode;

    // Determine node opacity
    let alpha = 1;
    if (pathActive) {
      alpha = pathNodeSet.has(String(node.id)) ? 1 : 0.06;
    } else if (lineageActive) {
      alpha = lineageSet.has(String(node.id)) ? 1 : 0.06;
    } else if (connectedSet) {
      alpha = connectedSet.has(String(node.id)) ? 1 : 0.08;
    } else if (!nodeMatchesFilter(node, st)) {
      alpha = 0.05;
    } else {
      alpha = type === 'fork' ? 0.65 : (node.isMinor ? 0.4 : 0.7);
    }

    const strokeColor = isSelected || isHovered ? '#fff' : color;
    const strokeWidth = isSelected ? 2.5 : (isHovered ? 2 : (type === 'fork' ? 1.5 : 0.5));

    if (type === 'topic') {
      const r = rScale(node.influence || 0);
      drawCircle(ctx, node.x, node.y, r,
        hexWithAlpha(color, alpha * 0.7),
        hexWithAlpha(strokeColor, alpha),
        strokeWidth);
    } else if (type === 'eip') {
      const size = rScale(node.influence || 0) * 1.4;
      drawRoundedRect(ctx,
        node.x - size / 2, node.y - size / 2,
        size, size, 3,
        hexWithAlpha(color, alpha * 0.65),
        hexWithAlpha(strokeColor, alpha),
        strokeWidth);
    } else if (type === 'fork') {
      drawDiamond(ctx, node.x, node.y, 14,
        hexWithAlpha('#ffcc00', alpha),
        hexWithAlpha('#aa8800', alpha),
        strokeWidth);
    } else if (type === 'magicians') {
      const r = rScale(node.influence || 0) * 0.9;
      drawTriangle(ctx, node.x, node.y, r * 2,
        hexWithAlpha(color, alpha * 0.6),
        hexWithAlpha(strokeColor, alpha),
        strokeWidth);
    } else if (type === 'paper') {
      const r = Math.max(4, rScale(node.influence || 0) * 0.78);
      drawCircle(ctx, node.x, node.y, r,
        hexWithAlpha(color, alpha * 0.6),
        hexWithAlpha(THREAD_COLORS[node.thread] || '#8fb8ef', alpha * 0.7),
        strokeWidth);
    }
  }

  // --- Draw labels for top nodes ---
  if (zoom > 0.4) {
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    const fontSize = Math.max(8, Math.min(11, 8 / zoom));
    ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;

    // Top 20 pre-computed candidates that are visible + hovered node
    for (const node of labelCandidates) {
      if (!visibleIdSet.has(String(node.id))) continue;

      let labelAlpha = 0.8;
      if (connectedSet && !connectedSet.has(String(node.id))) labelAlpha = 0.1;
      if (pathActive && !pathNodeSet.has(String(node.id))) labelAlpha = 0;

      if (labelAlpha <= 0) continue;

      ctx.fillStyle = hexWithAlpha('#bbb', labelAlpha);
      const title = node.title || '';
      const label = title.length > 24 ? title.slice(0, 23) + '\u2026' : title;
      const r = rScale(node.influence || 0);
      ctx.fillText(label, node.x, node.y + r + 4);
    }

    // Hovered node label (always visible)
    if (hoveredNode && hoveredNode.title) {
      ctx.fillStyle = '#fff';
      const title = hoveredNode.title;
      const label = title.length > 40 ? title.slice(0, 39) + '\u2026' : title;
      const r = getNodeRadius(hoveredNode);
      ctx.fillText(label, hoveredNode.x, hoveredNode.y + r + 4);
    }
  }

  ctx.restore();
}

// Helper: apply alpha to a hex color
function hexWithAlpha(hex, alpha) {
  const a = Math.round(Math.max(0, Math.min(1, alpha)) * 255);
  const alphaHex = a.toString(16).padStart(2, '0');
  // Handle shorthand hex
  if (hex.length === 4) {
    const r = hex[1], g = hex[2], b = hex[3];
    return '#' + r + r + g + g + b + b + alphaHex;
  }
  if (hex.length === 7) {
    return hex + alphaHex;
  }
  // Already has alpha — replace it
  if (hex.length === 9) {
    return hex.slice(0, 7) + alphaHex;
  }
  return hex + alphaHex;
}

function showNetworkTooltip(clientX, clientY, node) {
  const tip = document.getElementById('tooltip');
  if (!tip) return;
  const type = node.sourceType || 'topic';
  let html = '<strong>' + escapeHtml(node.title || node.id || '') + '</strong>';
  if (type === 'eip') {
    html += '<br>' + (node.status || '') + (node.fork ? ' \u00b7 ' + node.fork : '');
  }
  if (node.influence) html += '<br>inf: ' + node.influence.toFixed(2);
  if (type === 'topic' && node.author) html += '<br>' + escapeHtml(node.author);
  tip.innerHTML = html;
  tip.style.display = 'block';
  const rect = canvas.getBoundingClientRect();
  let x = rect.left + clientX + 14;
  let y = rect.top + clientY - 10;
  if (x + tip.offsetWidth > window.innerWidth - 10) x = rect.left + clientX - tip.offsetWidth - 14;
  if (y + tip.offsetHeight > window.innerHeight - 10) y = window.innerHeight - tip.offsetHeight - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

function hideNetworkTooltip() {
  const tip = document.getElementById('tooltip');
  if (tip) tip.style.display = 'none';
}

function escapeHtml(text) {
  const el = document.createElement('span');
  el.textContent = text || '';
  return el.innerHTML;
}

// --- Content/filter change handlers ---

function onContentChanged({ key }) {
  needsRedraw = true;
  if (key === 'showPapers') {
    const st = getState();
    if (st.showPapers) {
      addPaperNodes();
    } else {
      removePaperNodes();
    }
  }
}

function onFiltersChanged(changed) {
  needsRedraw = true;
  if (changed.paperLayerMode && getState().showPapers && paperNodesAdded) {
    // Mode changed — rebuild paper nodes with new limit
    removePaperNodes();
    addPaperNodes();
  }
}

// --- Paper node augmentation for network ---

function addPaperNodes() {
  const paperData = getPapers();
  if (!paperData?.papers || !simulation) return;

  const st = getState();
  const mode = st.paperLayerMode || 'focus';
  const limit = PAPER_LAYER_LIMITS[mode] || 200;

  // Sort papers by influence, take top N
  const allPapers = Object.values(paperData.papers);
  allPapers.sort((a, b) => (b.inf || 0) - (a.inf || 0));
  const selected = allPapers.slice(0, limit);

  // Build a set of existing node IDs to avoid duplicates
  const existingIds = new Set(nodes.map(n => String(n.id)));
  const newPaperNodeMap = {};

  for (const p of selected) {
    const nodeId = 'paper_' + p.id;
    if (existingIds.has(nodeId)) continue;

    const node = {
      id: nodeId,
      title: p.t || '',
      sourceType: 'paper',
      thread: p.th || null,
      influence: p.inf || 0,
      year: p.y,
      citedByCount: p.cb || 0,
      isMinor: false,
      x: (Math.random() - 0.5) * 600 + width / 2,
      y: (Math.random() - 0.5) * 400 + height / 2,
    };
    nodes.push(node);
    newPaperNodeMap[nodeId] = node;
    paperNodeIds.add(nodeId);
  }

  // Add paper citation edges from paperGraph
  const pg = paperData.paperGraph;
  if (pg?.edges) {
    const nodeMap = {};
    for (const n of nodes) nodeMap[String(n.id)] = n;

    for (const e of pg.edges) {
      const srcKey = 'paper_' + e.source;
      const tgtKey = 'paper_' + e.target;
      const src = nodeMap[srcKey];
      const tgt = nodeMap[tgtKey];
      if (!src || !tgt) continue;

      const edge = { source: src, target: tgt, type: 'paper_cites' };
      edges.push(edge);

      // Update adjacency index
      if (!nodeEdgeIndex[srcKey]) nodeEdgeIndex[srcKey] = [];
      nodeEdgeIndex[srcKey].push(edge);
      if (!nodeEdgeIndex[tgtKey]) nodeEdgeIndex[tgtKey] = [];
      nodeEdgeIndex[tgtKey].push(edge);
    }
  }

  // Rebuild edge groups
  rebuildEdgeGroups();

  // Update simulation
  simulation.nodes(nodes);
  simulation.force('link').links(edges);
  simulation.alpha(0.3).restart();

  // Update label candidates
  labelCandidates = nodes
    .filter(n => (n.sourceType || 'topic') !== 'fork' && (n.sourceType || 'topic') !== 'paper' && n.influence)
    .sort((a, b) => (b.influence || 0) - (a.influence || 0))
    .slice(0, 20);

  paperNodesAdded = true;
  currentPaperMode = mode;
  quadtreeDirty = true;
}

function removePaperNodes() {
  if (!paperNodesAdded || !simulation) return;

  // Remove paper nodes
  for (let i = nodes.length - 1; i >= 0; i--) {
    if (paperNodeIds.has(String(nodes[i].id))) {
      nodes.splice(i, 1);
    }
  }

  // Remove paper edges
  for (let i = edges.length - 1; i >= 0; i--) {
    const srcId = String(edges[i].source.id ?? edges[i].source);
    const tgtId = String(edges[i].target.id ?? edges[i].target);
    if (paperNodeIds.has(srcId) || paperNodeIds.has(tgtId)) {
      edges.splice(i, 1);
    }
  }

  // Clean up adjacency index
  for (const id of paperNodeIds) {
    delete nodeEdgeIndex[id];
  }
  // Also clean references in other nodes' adjacency lists
  for (const [id, adj] of Object.entries(nodeEdgeIndex)) {
    nodeEdgeIndex[id] = adj.filter(e => {
      const srcId = String(e.source.id ?? e.source);
      const tgtId = String(e.target.id ?? e.target);
      return !paperNodeIds.has(srcId) && !paperNodeIds.has(tgtId);
    });
  }

  paperNodeIds.clear();
  paperNodesAdded = false;
  currentPaperMode = null;

  // Rebuild edge groups
  rebuildEdgeGroups();

  // Update simulation
  simulation.nodes(nodes);
  simulation.force('link').links(edges);
  simulation.alpha(0.2).restart();

  // Update label candidates
  labelCandidates = nodes
    .filter(n => (n.sourceType || 'topic') !== 'fork' && (n.sourceType || 'topic') !== 'paper' && n.influence)
    .sort((a, b) => (b.influence || 0) - (a.influence || 0))
    .slice(0, 20);

  quadtreeDirty = true;
}

export function onActivate() {
  needsRedraw = true;
  if (simulation) simulation.alpha(0.1).restart();
}
