// data.js — Progressive data loading + index building

const cache = {};
const BASE = import.meta.url.includes('/js/')
  ? new URL('..', import.meta.url).href
  : './';
const DATA_DIR = BASE + 'data/';

async function fetchJSON(filename) {
  if (cache[filename]) return cache[filename];
  const resp = await fetch(DATA_DIR + filename);
  if (!resp.ok) throw new Error(`Failed to load ${filename}: ${resp.status}`);
  const data = await resp.json();
  cache[filename] = data;
  return data;
}

// --- Core data (topics, threads, forks, eras, authors, topic edges) ---
let coreData = null;
let coreIndexes = null;

export async function loadCore() {
  if (coreData) return coreData;
  coreData = await fetchJSON('core.json');
  coreIndexes = buildCoreIndexes(coreData);
  return coreData;
}

export function getCore() { return coreData; }
export function getCoreIndexes() { return coreIndexes; }

function buildCoreIndexes(data) {
  const topicEdgeIndex = {};
  const eipToTopics = {};
  const tagToTopics = {};

  // Build topic edge adjacency
  for (const e of (data.graph?.edges || [])) {
    const s = String(e.source), t = String(e.target);
    if (!topicEdgeIndex[s]) topicEdgeIndex[s] = new Set();
    if (!topicEdgeIndex[t]) topicEdgeIndex[t] = new Set();
    topicEdgeIndex[s].add(Number(e.target));
    topicEdgeIndex[t].add(Number(e.source));
  }

  // Build EIP → topic and tag → topic indices
  for (const topic of Object.values(data.topics || {})) {
    const allEips = (topic.eips || []).concat(topic.peips || []);
    for (const eip of allEips) {
      if (!eipToTopics[eip]) eipToTopics[eip] = new Set();
      eipToTopics[eip].add(topic.id);
    }
    for (const tag of (topic.tg || [])) {
      if (!tagToTopics[tag]) tagToTopics[tag] = new Set();
      tagToTopics[tag].add(topic.id);
    }
  }

  // Build milestone index
  const milestoneIndex = {};
  for (const [tid, th] of Object.entries(data.threads || {})) {
    if (!th?.ms) continue;
    for (const ms of th.ms) {
      milestoneIndex[ms.id] = {
        threadId: tid,
        threadName: th.n,
        note: ms.n,
      };
    }
  }

  return { topicEdgeIndex, eipToTopics, tagToTopics, milestoneIndex };
}


// --- EIP data ---
let eipData = null;

export async function loadEips() {
  if (eipData) return eipData;
  eipData = await fetchJSON('eips.json');
  return eipData;
}

export function getEips() { return eipData; }


// --- Paper data ---
let paperData = null;

export async function loadPapers() {
  if (paperData) return paperData;
  paperData = await fetchJSON('papers.json');
  return paperData;
}

export function getPapers() { return paperData; }


// --- Unified graph data (for network view) ---
let graphData = null;
let graphIndexes = null;

export async function loadGraph() {
  if (graphData) return graphData;
  graphData = await fetchJSON('graph.json');
  graphIndexes = buildGraphIndexes(graphData);
  return graphData;
}

export function getGraph() { return graphData; }
export function getGraphIndexes() { return graphIndexes; }

function buildGraphIndexes(data) {
  // Per-node adjacency sets for viewport culling
  const nodeAdjacency = {};
  for (const edge of (data.unifiedGraph?.edges || [])) {
    const s = String(edge.source), t = String(edge.target);
    if (!nodeAdjacency[s]) nodeAdjacency[s] = [];
    nodeAdjacency[s].push(edge);
    if (!nodeAdjacency[t]) nodeAdjacency[t] = [];
    nodeAdjacency[t].push(edge);
  }

  // Sort edges by type for batch rendering
  const edgesByType = {};
  for (const edge of (data.unifiedGraph?.edges || [])) {
    const type = edge.type || 'unknown';
    if (!edgesByType[type]) edgesByType[type] = [];
    edgesByType[type].push(edge);
  }

  // Connected EIP node IDs (have eip_topic edge)
  const connectedEipNodeIds = new Set();
  for (const edge of (data.unifiedGraph?.edges || [])) {
    if (edge.type === 'eip_topic' && typeof edge.source === 'string' && edge.source.startsWith('eip_')) {
      connectedEipNodeIds.add(edge.source);
    }
  }

  // EIP → topic reverse lookup
  const eipToTopicIds = {};
  for (const edge of (data.unifiedGraph?.edges || [])) {
    if (edge.type === 'eip_topic') {
      const eipId = String(edge.source);
      if (!eipToTopicIds[eipId]) eipToTopicIds[eipId] = [];
      eipToTopicIds[eipId].push(edge.target);
    }
  }

  // Cross-forum traversal indices
  const eipToMagiciansRefs = {};
  const topicToMagiciansRefs = {};
  for (const edge of (data.crossForumEdges || [])) {
    if (!edge) continue;
    if (edge.sT === 'eip' && edge.tT === 'magicians_topic') {
      const eipNum = String(edge.s);
      if (!eipToMagiciansRefs[eipNum]) eipToMagiciansRefs[eipNum] = new Set();
      eipToMagiciansRefs[eipNum].add(Number(edge.t));
    }
    if (edge.sT === 'topic' && edge.tT === 'magicians_topic') {
      const topicId = String(edge.s);
      if (!topicToMagiciansRefs[topicId]) topicToMagiciansRefs[topicId] = new Set();
      topicToMagiciansRefs[topicId].add(Number(edge.t));
    }
  }

  // Magicians → EIP reverse lookup
  const magiciansToEips = {};
  for (const [eipNum, eip] of Object.entries(data.eipCatalog || {})) {
    if (eip.mt) {
      if (!magiciansToEips[eip.mt]) magiciansToEips[eip.mt] = [];
      magiciansToEips[eip.mt].push(eipNum);
    }
  }

  return {
    nodeAdjacency,
    edgesByType,
    connectedEipNodeIds,
    eipToTopicIds,
    eipToMagiciansRefs,
    topicToMagiciansRefs,
    magiciansToEips,
  };
}


// --- Co-author graph ---
let coauthorData = null;

export async function loadCoauthor() {
  if (coauthorData) return coauthorData;
  coauthorData = await fetchJSON('coauthor.json');
  return coauthorData;
}

export function getCoauthor() { return coauthorData; }


// --- Utility: check if a dataset is loaded ---
export function isLoaded(name) {
  return cache[name + '.json'] !== undefined;
}
