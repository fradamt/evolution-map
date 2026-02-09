// identity.js — Cross-forum author identity linking (BFS components)

const IDENTITY_GRAPH = new Map();
const IDENTITY_COMPONENT_BY_NODE = new Map();
const IDENTITY_MEMBERS_BY_COMPONENT = new Map();

function identityNode(kind, name) {
  return kind + ':' + name;
}

function parseIdentityNode(node) {
  const idx = String(node).indexOf(':');
  if (idx < 0) return { kind: '', name: String(node) };
  return { kind: String(node).slice(0, idx), name: String(node).slice(idx + 1) };
}

function ensureIdentityNode(kind, name) {
  if (!name) return;
  const node = identityNode(kind, name);
  if (!IDENTITY_GRAPH.has(node)) IDENTITY_GRAPH.set(node, new Set());
}

function connectIdentityNodes(aKind, aName, bKind, bName) {
  if (!aName || !bName) return;
  const a = identityNode(aKind, aName);
  const b = identityNode(bKind, bName);
  ensureIdentityNode(aKind, aName);
  ensureIdentityNode(bKind, bName);
  if (a === b) return;
  IDENTITY_GRAPH.get(a).add(b);
  IDENTITY_GRAPH.get(b).add(a);
}

export function buildIdentityGraph(data) {
  // Clear previous graph
  IDENTITY_GRAPH.clear();
  IDENTITY_COMPONENT_BY_NODE.clear();
  IDENTITY_MEMBERS_BY_COMPONENT.clear();

  const authorLinks = data.authorLinks || {};
  const ethToEipAuthors = authorLinks.ethToEip || {};
  const magToEthAuthors = authorLinks.magToEth || {};
  const magToEipAuthors = authorLinks.magToEip || {};

  // Register all known identities
  for (const username of Object.keys(data.authors || {})) {
    ensureIdentityNode('eth', username);
  }
  for (const t of Object.values(data.topics || {})) {
    if (t?.a) ensureIdentityNode('eth', t.a);
    for (const u of (t?.coauth || [])) if (u) ensureIdentityNode('eth', u);
    for (const u of (t?.parts || [])) if (u) ensureIdentityNode('eth', u);
  }
  for (const name of Object.keys(data.eipAuthors || {})) {
    ensureIdentityNode('eip', name);
  }
  for (const mt of Object.values(data.magiciansTopics || {})) {
    if (mt?.a) ensureIdentityNode('mag', mt.a);
  }

  // Connect across forums
  for (const [username, names] of Object.entries(ethToEipAuthors)) {
    for (const name of (names || [])) {
      connectIdentityNodes('eth', username, 'eip', name);
    }
  }
  for (const [handle, usernames] of Object.entries(magToEthAuthors)) {
    for (const username of (usernames || [])) {
      connectIdentityNodes('mag', handle, 'eth', username);
    }
  }
  for (const [handle, names] of Object.entries(magToEipAuthors)) {
    for (const name of (names || [])) {
      connectIdentityNodes('mag', handle, 'eip', name);
    }
  }

  // Build connected components via BFS
  let compIndex = 0;
  for (const [startNode] of IDENTITY_GRAPH) {
    if (IDENTITY_COMPONENT_BY_NODE.has(startNode)) continue;
    compIndex += 1;
    const compId = 'idc' + compIndex;
    const members = { eth: new Set(), eip: new Set(), mag: new Set() };
    const stack = [startNode];
    IDENTITY_COMPONENT_BY_NODE.set(startNode, compId);
    while (stack.length > 0) {
      const node = stack.pop();
      const parsed = parseIdentityNode(node);
      if (members[parsed.kind]) members[parsed.kind].add(parsed.name);
      const neighbors = IDENTITY_GRAPH.get(node) || new Set();
      for (const nextNode of neighbors) {
        if (!IDENTITY_COMPONENT_BY_NODE.has(nextNode)) {
          IDENTITY_COMPONENT_BY_NODE.set(nextNode, compId);
          stack.push(nextNode);
        }
      }
    }
    IDENTITY_MEMBERS_BY_COMPONENT.set(compId, members);
  }
}

function sortedSetValues(setObj) {
  return Array.from(setObj || []).sort((a, b) => String(a).localeCompare(String(b)));
}

export function identityMembers(kind, name) {
  const empty = { eth: [], eip: [], mag: [] };
  if (!name) return empty;
  const node = identityNode(kind, name);
  if (!IDENTITY_GRAPH.has(node)) {
    const fallback = { eth: [], eip: [], mag: [] };
    if (fallback[kind]) fallback[kind] = [String(name)];
    return fallback;
  }
  const compId = IDENTITY_COMPONENT_BY_NODE.get(node);
  if (!compId) {
    const lonely = { eth: [], eip: [], mag: [] };
    if (lonely[kind]) lonely[kind] = [String(name)];
    return lonely;
  }
  const members = IDENTITY_MEMBERS_BY_COMPONENT.get(compId);
  if (!members) return empty;
  return {
    eth: sortedSetValues(members.eth),
    eip: sortedSetValues(members.eip),
    mag: sortedSetValues(members.mag),
  };
}

export function linkedEipAuthors(username) {
  return identityMembers('eth', username).eip;
}

export function linkedEthAuthors(eipAuthorName, aliasMap) {
  const canonical = aliasMap?.[eipAuthorName] || eipAuthorName;
  return identityMembers('eip', canonical).eth;
}

export function linkedEthAuthorsFromMag(magAuthor) {
  return identityMembers('mag', magAuthor).eth;
}

export function linkedEipAuthorsFromMag(magAuthor) {
  return identityMembers('mag', magAuthor).eip;
}

export function linkedMagAuthorsFromEth(username) {
  return identityMembers('eth', username).mag;
}

export function linkedMagAuthorsFromEip(eipAuthorName, aliasMap) {
  const canonical = aliasMap?.[eipAuthorName] || eipAuthorName;
  return identityMembers('eip', canonical).mag;
}
