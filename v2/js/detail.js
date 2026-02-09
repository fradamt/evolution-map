// detail.js — Right panel: topic/EIP/paper/author/fork/thread detail

import { THREAD_COLORS, THREAD_NAMES, EIP_STATUS_COLORS, MILESTONE_LABELS, AUTHOR_COLORS } from './constants.js';
import { getState, on, selectEntity, setFilters, setDetailOpen, setLineage } from './state.js';
import { getCore, getCoreIndexes, getEips, loadEips, getPapers, getGraph, getGraphIndexes } from './data.js';
import { linkedEipAuthors, linkedEthAuthors, linkedEthAuthorsFromMag, linkedEipAuthorsFromMag } from './identity.js';

export function init() {
  on('selection:changed', ({ current }) => {
    if (current) show(current);
  });
  on('detail:changed', ({ open }) => {
    if (!open) {
      const panel = document.getElementById('detail-panel');
      if (panel) panel.classList.remove('open');
    }
  });
}

export function show({ type, id }) {
  const panel = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');
  if (!panel || !content) return;

  panel.classList.add('open');
  content.innerHTML = '';

  switch (type) {
    case 'topic': showTopicDetail(content, id); break;
    case 'eip': showEipDetail(content, id); break;
    case 'paper': showPaperDetail(content, id); break;
    case 'author': showAuthorDetail(content, id); break;
    case 'eipAuthor': showEipAuthorDetail(content, id); break;
    case 'thread': showThreadDetail(content, id); break;
    case 'fork': showForkDetail(content, id); break;
    case 'era': showEraDetail(content, id); break;
    case 'magicians': showMagiciansDetail(content, id); break;
    default: content.innerHTML = `<p style="color:#888">Unknown entity type: ${type}</p>`;
  }
}

function h(text) {
  const el = document.createElement('span');
  el.textContent = text;
  return el.innerHTML;
}

// --- TOPIC DETAIL ---
function showTopicDetail(el, id) {
  const core = getCore();
  const t = core?.topics?.[id];
  if (!t) {
    el.innerHTML = `<p style="color:#888">Topic ${id} not found</p>`;
    return;
  }

  const threadColor = THREAD_COLORS[t.th] || '#666';
  const threadName = THREAD_NAMES[t.th] || t.th || 'Uncategorized';
  const isMinor = !!t.mn;

  // Milestone badge
  const indexes = getCoreIndexes();
  const msInfo = indexes?.milestoneIndex?.[id];
  let msBadge = '';
  if (msInfo) {
    const msColor = THREAD_COLORS[msInfo.threadId] || '#ffcc44';
    msBadge = `<div class="milestone-badge"><span class="mb-icon">\u2605</span>${h(msInfo.note?.replace('_', ' ') || '')} in <span style="color:${msColor}" data-thread="${h(msInfo.threadId)}">${h(msInfo.threadName || '')}</span></div>`;
  }

  // Coauthors
  const coauthors = (t.coauth || []).filter(u => u && u !== t.a);
  let coauthorInline = '';
  if (coauthors.length > 0) {
    const shown = coauthors.slice(0, 3).map(u =>
      `<span style="cursor:pointer;color:#7788cc" data-author="${h(u)}">${h(u)}</span>`
    ).join(', ');
    const extra = coauthors.length > 3 ? ` <span style="color:#666">+${coauthors.length - 3}</span>` : '';
    coauthorInline = ' \u00b7 with ' + shown + extra;
  }

  let html = `<h2>${h(t.t)}</h2>`;
  if (isMinor) {
    html += `<div style="display:inline-block;font-size:10px;padding:2px 8px;border-radius:3px;margin:4px 0 8px;background:#1a1a2a;border:1px solid #333;color:#889">Minor Topic</div>`;
  }
  html += msBadge;
  html += `<div class="meta">by <strong style="cursor:pointer;color:#7788cc" data-author="${h(t.a)}">${h(t.a)}</strong>${coauthorInline} \u00b7 ${t.d?.slice(0, 10) || ''}
    \u00b7 <a href="https://ethresear.ch/t/${id}" target="_blank">Open on ethresear.ch \u2192</a></div>`;

  // Coauthors row when >3
  if (coauthors.length > 3) {
    html += `<div class="detail-stat"><span class="label">Coauthors</span><span class="value">${coauthors.map(u => `<span style="cursor:pointer;color:#7788cc" data-author="${h(u)}">${h(u)}</span>`).join(', ')}</span></div>`;
  }

  // Stats
  html += `<div class="detail-stat"><span class="label">Thread</span><span class="value" style="color:${threadColor};cursor:pointer" data-thread="${h(t.th || '')}">${threadName}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Influence</span><span class="value">${(t.inf || 0).toFixed(3)}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Views</span><span class="value">${(t.vw || 0).toLocaleString()}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Likes</span><span class="value">${t.lk || 0}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Posts</span><span class="value">${t.pc || 0}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Cited by</span><span class="value">${t.ind || 0} topics</span></div>`;
  if (t.cat) {
    html += `<div class="detail-stat"><span class="label">Category</span><span class="value" style="cursor:pointer;color:#7788cc" data-category="${h(t.cat)}">${h(t.cat)}</span></div>`;
  }

  // Action buttons
  const st = getState();
  const lineageActive = st.lineageActive && st.lineageSet.has(id);
  html += `<div style="margin:10px 0 6px;display:flex;gap:6px">`;
  html += `<button class="action-btn" id="lineage-btn" style="border-color:${lineageActive ? '#88aaff' : '#5566aa'};color:${lineageActive ? '#88aaff' : '#8899cc'}">${lineageActive ? 'Clear Lineage (' + st.lineageSet.size + ')' : 'Trace Lineage'}</button>`;
  html += `<button class="action-btn" id="similar-btn" style="border-color:#44aa88;color:#66bbaa">Find Similar</button>`;
  html += `</div>`;

  // Excerpt
  if (t.exc) {
    const short = t.exc.length > 300 ? t.exc.slice(0, 300) + '...' : t.exc;
    html += `<div class="detail-excerpt"><span id="excerpt-short">${h(short)}</span>`;
    if (t.exc.length > 300) {
      html += `<span id="excerpt-full" style="display:none">${h(t.exc)}</span>`;
      html += ` <span id="excerpt-toggle" style="color:#66bbaa;cursor:pointer;font-size:10px;font-style:normal">show more</span>`;
    }
    html += `</div>`;
  }

  // EIP mentions
  const primarySet = new Set(t.peips || []);
  if (t.peips?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIPs discussed:</strong> `;
    for (const eip of t.peips) {
      html += `<span class="eip-tag primary" data-eip="${eip}">EIP-${eip}</span> `;
    }
    html += `</div>`;
  }
  const secondaryEips = (t.eips || []).filter(e => !primarySet.has(e));
  if (secondaryEips.length > 0) {
    html += `<div style="margin:4px 0"><strong style="font-size:11px;color:#666">Also mentions:</strong> `;
    for (const eip of secondaryEips) {
      html += `<span class="eip-tag" data-eip="${eip}">EIP-${eip}</span> `;
    }
    html += `</div>`;
  }

  // Magicians cross-references
  if (t.mr?.length > 0) {
    html += `<div class="detail-refs"><h4>Magicians Discussions (${t.mr.length})</h4>`;
    for (const mtid of t.mr) {
      html += `<div class="ref-item"><a data-magicians="${mtid}" style="color:#bb88cc;cursor:pointer">M#${mtid}</a>
        <a href="https://ethereum-magicians.org/t/${mtid}" target="_blank" class="magicians-link">open on magicians &#8599;</a></div>`;
    }
    html += `</div>`;
  }

  // References
  if (t.out?.length > 0) {
    html += `<div class="detail-refs"><h4>References (${t.out.length})</h4>`;
    for (const ref of t.out.slice(0, 10)) {
      const refTopic = core.topics?.[ref];
      const refTitle = refTopic ? refTopic.t : `Topic #${ref}`;
      html += `<div class="ref-item"><a data-topic="${ref}">${h(refTitle)}</a></div>`;
    }
    html += `</div>`;
  }

  if (t.inc?.length > 0) {
    html += `<div class="detail-refs"><h4>Cited by (${t.inc.length})</h4>`;
    for (const ref of t.inc.slice(0, 10)) {
      const refTopic = core.topics?.[ref];
      const refTitle = refTopic ? refTopic.t : `Topic #${ref}`;
      html += `<div class="ref-item"><a data-topic="${ref}">${h(refTitle)}</a></div>`;
    }
    html += `</div>`;
  }

  el.innerHTML = html;
  wireUpDetailLinks(el);
  wireUpActionButtons(el, id, core);
}

// --- EIP DETAIL ---
function showEipDetail(el, id) {
  const eips = getEips();
  const eip = eips?.eipCatalog?.[id];
  if (!eip) {
    loadEips().then(() => {
      const loaded = getEips()?.eipCatalog?.[id];
      if (loaded) showEipDetail(el, id);
      else el.innerHTML = `<p style="color:#888">EIP-${id} not found</p>`;
    });
    return;
  }

  const statusColor = EIP_STATUS_COLORS[eip.s] || '#555';
  const statusClass = 'eip-status eip-status-' + (eip.s || '').toLowerCase().replace(/\s+/g, '');

  let html = `<h2 style="color:${statusColor}">EIP-${id}: ${h(eip.t || 'Untitled')}</h2>`;
  html += `<div class="meta">
    <span class="${statusClass}">${eip.s || 'Unknown'}</span>`;
  // Type / Category
  const typeCat = [eip.ty, eip.c].filter(Boolean);
  if (typeCat.length) html += ' \u00b7 ' + typeCat.map(h).join(' \u00b7 ');
  if (eip.fk) html += ` <span class="fork-tag" data-fork="${h(eip.fk)}">${h(eip.fk)}</span>`;
  html += `</div>`;

  // Stats
  if (eip.cr) html += `<div class="eip-detail-stat"><span class="label">Created</span><span class="value">${h(eip.cr)}</span></div>`;
  html += `<div class="eip-detail-stat"><span class="label">Influence</span><span class="value">${(eip.inf || 0).toFixed(3)}</span></div>`;
  if (eip.mv) html += `<div class="eip-detail-stat"><span class="label">Magicians Views</span><span class="value">${(eip.mv || 0).toLocaleString()}</span></div>`;
  if (eip.ml) html += `<div class="eip-detail-stat"><span class="label">Magicians Likes</span><span class="value">${eip.ml || 0}</span></div>`;
  if (eip.mp) html += `<div class="eip-detail-stat"><span class="label">Magicians Posts</span><span class="value">${eip.mp || 0}</span></div>`;
  if (eip.mpc) html += `<div class="eip-detail-stat"><span class="label">Magicians Participants</span><span class="value">${eip.mpc || 0}</span></div>`;
  html += `<div class="eip-detail-stat"><span class="label">ethresearch Citations</span><span class="value">${eip.erc || 0}</span></div>`;

  // Authors
  if (eip.au?.length > 0) {
    html += `<div class="eip-detail-stat"><span class="label">Authors</span><span class="value">`;
    html += eip.au.map(a => {
      const ea = eips?.eipAuthors?.[a];
      if (ea) return `<span style="cursor:pointer;color:#7788cc" data-eip-author="${h(a)}">${h(a)}</span>`;
      return h(a);
    }).join(', ');
    html += `</span></div>`;
  }

  // Requires
  if (eip.rq?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Requires</strong> `;
    for (const req of eip.rq) {
      html += `<span class="eip-requires-tag" data-eip="${req}">EIP-${req}</span> `;
    }
    html += `</div>`;
  }

  // Required by (reverse lookup)
  const reqByList = buildRequiredBy(id, eips);
  if (reqByList.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Required by</strong> `;
    for (const r of reqByList) {
      html += `<span class="eip-requires-tag" data-eip="${r}">EIP-${r}</span> `;
    }
    html += `</div>`;
  }

  // External links
  html += `<div style="margin-top:8px;display:flex;flex-direction:column;gap:3px">`;
  html += `<a href="https://eips.ethereum.org/EIPS/eip-${id}" target="_blank" class="magicians-link">eips.ethereum.org &#8599;</a>`;
  if (eip.mt) html += `<a href="https://ethereum-magicians.org/t/${eip.mt}" target="_blank" class="magicians-link">Magicians discussion &#8599;</a>`;
  if (eip.et) html += `<a href="https://ethresear.ch/t/${eip.et}" target="_blank" class="magicians-link">ethresear.ch discussion &#8599;</a>`;
  html += `</div>`;

  // Related ethresearch topics
  const core = getCore();
  const coreIndexes = getCoreIndexes();
  const relTopicIds = coreIndexes?.eipToTopics?.[id];
  if (relTopicIds && relTopicIds.size > 0) {
    const sorted = Array.from(relTopicIds)
      .map(tid => core?.topics?.[tid])
      .filter(Boolean)
      .sort((a, b) => (b.inf || 0) - (a.inf || 0))
      .slice(0, 10);
    if (sorted.length > 0) {
      html += `<div class="detail-refs" style="margin-top:12px"><h4>Related ethresearch topics (${relTopicIds.size})</h4>`;
      for (const t of sorted) {
        html += `<div class="ref-item"><a data-topic="${t.id}">${h(t.t)}</a> <span style="color:#666;font-size:10px">(${(t.inf || 0).toFixed(2)})</span></div>`;
      }
      html += `</div>`;
    }
  }

  el.innerHTML = html;
  wireUpDetailLinks(el);
}

function buildRequiredBy(eipNum, eipsData) {
  if (!eipsData?.eipCatalog) return [];
  const result = [];
  for (const [num, eip] of Object.entries(eipsData.eipCatalog)) {
    if ((eip.rq || []).includes(Number(eipNum)) || (eip.rq || []).includes(String(eipNum))) {
      result.push(Number(num));
    }
  }
  return result.sort((a, b) => a - b);
}

// --- PAPER DETAIL ---
function showPaperDetail(el, id) {
  const papers = getPapers();
  const p = papers?.papers?.[id];
  if (!p) {
    el.innerHTML = `<p style="color:#888">Paper not found</p>`;
    return;
  }
  const pid = String(p.id || id).trim();

  const url = p.u || (p.doi ? 'https://doi.org/' + p.doi : (p.ax ? 'https://arxiv.org/abs/' + p.ax : ''));

  let html = `<h2>${h(p.t)}</h2>`;
  html += `<div class="meta">`;
  if (p.a?.length > 0) {
    html += h(p.a.join(', '));
    html += ' \u00b7 ';
  }
  html += (p.y || '?');
  if (p.v) html += ' \u00b7 ' + h(p.v);
  html += ' \u00b7 ';
  if (url) html += `<a href="${h(url)}" target="_blank">Open paper \u2192</a>`;
  else html += 'No canonical URL';
  html += `</div>`;

  html += `<div class="detail-stat"><span class="label">Relevance</span><span class="value">${Number(p.rs || 0).toFixed(3)}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Citations (OpenAlex)</span><span class="value">${Number(p.cb || 0).toLocaleString()}</span></div>`;
  if (p.inf) html += `<div class="detail-stat"><span class="label">Influence</span><span class="value">${(p.inf || 0).toFixed(3)}</span></div>`;
  if (p.doi) html += `<div class="detail-stat"><span class="label">DOI</span><span class="value">${h(p.doi)}</span></div>`;
  if (p.ax) html += `<div class="detail-stat"><span class="label">ArXiv/ePrint</span><span class="value">${h(p.ax)}</span></div>`;

  // EIP mentions
  if (p.eq?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIP Mentions</strong> `;
    for (const eip of p.eq.slice(0, 14)) {
      html += `<span class="eip-tag primary" data-eip="${eip}">EIP-${eip}</span> `;
    }
    if (p.eq.length > 14) html += `<span style="color:#666;font-size:10px">+${p.eq.length - 14}</span>`;
    html += `</div>`;
  }

  // Tags
  if (p.tg?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#666">Tags</strong> `;
    html += p.tg.slice(0, 8).map(t => `<span class="eip-tag" style="border-color:#3a4f6c;color:#9cc8ff">${h(t)}</span>`).join(' ');
    html += `</div>`;
  }

  // Citation graph: Cited by / References
  html += buildPaperCitationHtml(pid, papers);

  el.innerHTML = html;
  wireUpDetailLinks(el);
}

function buildPaperCitationHtml(pid, papers) {
  const pgEdges = papers?.paperGraph?.edges || [];
  const cites = [];
  const citedBy = [];
  for (const edge of pgEdges) {
    const src = String(edge.source || '');
    const tgt = String(edge.target || '');
    if (src === pid && tgt !== pid) cites.push(tgt);
    if (tgt === pid && src !== pid) citedBy.push(src);
  }
  if (cites.length === 0 && citedBy.length === 0) return '';

  const allPapers = papers?.papers || {};
  let html = '';

  if (citedBy.length > 0) {
    citedBy.sort((a, b) => (allPapers[b]?.inf || 0) - (allPapers[a]?.inf || 0));
    html += `<div class="detail-refs"><h4>Cited by (${citedBy.length})</h4>`;
    for (const otherId of citedBy.slice(0, 10)) {
      const op = allPapers[otherId];
      if (!op) continue;
      const label = (op.t || 'Untitled').slice(0, 60) + ((op.t || '').length > 60 ? '\u2026' : '');
      html += `<div class="ref-item"><a data-paper="${h(otherId)}">${h(label)}</a>${op.y ? ` <span style="color:#666;font-size:10px">(${op.y})</span>` : ''}</div>`;
    }
    if (citedBy.length > 10) html += `<div style="color:#666;font-size:10px">+${citedBy.length - 10} more</div>`;
    html += `</div>`;
  }

  if (cites.length > 0) {
    cites.sort((a, b) => (allPapers[b]?.inf || 0) - (allPapers[a]?.inf || 0));
    html += `<div class="detail-refs"><h4>References (${cites.length})</h4>`;
    for (const otherId of cites.slice(0, 10)) {
      const op = allPapers[otherId];
      if (!op) continue;
      const label = (op.t || 'Untitled').slice(0, 60) + ((op.t || '').length > 60 ? '\u2026' : '');
      html += `<div class="ref-item"><a data-paper="${h(otherId)}">${h(label)}</a>${op.y ? ` <span style="color:#666;font-size:10px">(${op.y})</span>` : ''}</div>`;
    }
    if (cites.length > 10) html += `<div style="color:#666;font-size:10px">+${cites.length - 10} more</div>`;
    html += `</div>`;
  }

  return html;
}

// --- AUTHOR DETAIL ---
function showAuthorDetail(el, id) {
  const core = getCore();
  const a = core?.authors?.[id];
  if (!a) {
    el.innerHTML = `<p style="color:#888">Author "${id}" not found</p>`;
    return;
  }

  const authorList = Object.values(core.authors || {}).sort((x, y) => (y.inf || 0) - (x.inf || 0));
  const rank = authorList.findIndex(x => x.u === id);
  const color = rank >= 0 && rank < 15 ? AUTHOR_COLORS[rank] : '#667';

  const linked = linkedEipAuthors(a.u);

  // Identity tabs
  let identityTabs = '';
  if (linked.length > 0) {
    identityTabs = `<div class="author-tab-wrap" style="margin-top:2px;margin-bottom:10px">
      <span class="author-tab active">ethresearch</span>
      <span class="author-tab" data-eip-author="${h(linked[0])}">EIPs</span>
    </div>`;
  }

  let html = `<h2 style="color:${color}">${h(a.u)}</h2>`;
  html += `<div class="meta">Researcher \u00b7 <a href="https://ethresear.ch/u/${encodeURIComponent(a.u)}" target="_blank">View profile \u2192</a></div>`;
  html += identityTabs;

  html += `<div class="detail-stat"><span class="label">Topics Created</span><span class="value">${a.tc || 0} influential${a.at?.length > a.tc ? ' / ' + a.at.length + ' total' : ''}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Total Posts</span><span class="value">${(a.tp || 0).toLocaleString()}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Total Likes</span><span class="value">${(a.lk || 0).toLocaleString()}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Influence Score</span><span class="value">${(a.inf || 0).toFixed(3)}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Cited by</span><span class="value">${a.ind || 0} topics</span></div>`;
  if (a.yrs?.length > 0) {
    html += `<div class="detail-stat"><span class="label">Active Years</span><span class="value">${a.yrs.join(', ')}</span></div>`;
  }

  // Linked EIP authors
  if (linked.length > 0) {
    const eips = getEips();
    const linkedEipCount = linked.reduce((sum, name) => {
      const ea = eips?.eipAuthors?.[name];
      return sum + ((ea?.eips || []).length || 0);
    }, 0);
    html += `<div class="detail-stat"><span class="label">Linked EIP Authors</span><span class="value">${linked.map(name => `<span style="cursor:pointer;color:#7788cc" data-eip-author="${h(name)}">${h(name)}</span>`).join(', ')}</span></div>`;
    html += `<div class="detail-stat"><span class="label">Linked EIPs</span><span class="value">${linkedEipCount}</span></div>`;
  }

  // Thread distribution bars
  if (a.ths && Object.keys(a.ths).length > 0) {
    html += `<div style="margin-top:12px"><strong style="font-size:11px;color:#888">Thread Distribution</strong><div style="margin-top:6px">`;
    const total = Object.values(a.ths).reduce((s, v) => s + v, 0) || 1;
    const sorted = Object.entries(a.ths).sort((x, y) => y[1] - x[1]);
    for (const [tid, count] of sorted.slice(0, 6)) {
      const pct = Math.round(count / total * 100);
      const tColor = THREAD_COLORS[tid] || '#555';
      html += `<div class="thread-bar-row">
        <span class="thread-bar-label" style="color:${tColor}">${THREAD_NAMES[tid] || tid}</span>
        <span class="thread-bar-track"><span class="thread-bar-fill" style="width:${pct}%;background:${tColor}"></span></span>
        <span class="thread-bar-pct">${pct}%</span>
      </div>`;
    }
    html += `</div></div>`;
  }

  // Top topics
  if (a.tops?.length > 0) {
    html += `<div class="detail-refs" style="margin-top:12px"><h4>Top Topics</h4>`;
    for (const tid of a.tops) {
      const topic = core.topics?.[tid];
      if (topic) {
        html += `<div class="ref-item"><a data-topic="${tid}">${h(topic.t)}</a> <span style="color:#666;font-size:10px">(${(topic.inf || 0).toFixed(2)})</span></div>`;
      }
    }
    html += `</div>`;
  }

  // Minor topics for this author
  const minorForAuthor = Object.values(core.topics || {})
    .filter(t => t.mn && (t.a === id || (t.coauth || []).includes(id)))
    .sort((a, b) => (b.d || '').localeCompare(a.d || ''));
  if (minorForAuthor.length > 0) {
    html += `<div class="detail-refs" style="margin-top:12px"><h4 style="color:#667">Other Topics</h4>`;
    for (const mt of minorForAuthor.slice(0, 15)) {
      html += `<div class="ref-item minor-ref"><a data-topic="${mt.id}" style="color:#889;font-style:italic">${h(mt.t)}</a> <span style="color:#556;font-size:10px">${(mt.d || '').slice(0, 7)}</span></div>`;
    }
    if (minorForAuthor.length > 15) {
      html += `<div style="font-size:10px;color:#667;padding:3px 0">+${minorForAuthor.length - 15} more</div>`;
    }
    html += `</div>`;
  }

  // Co-researchers
  if (a.co && Object.keys(a.co).length > 0) {
    html += `<div style="margin-top:12px"><strong style="font-size:11px;color:#888">Co-Researchers</strong><div style="margin-top:6px">`;
    for (const [coName, coCount] of Object.entries(a.co)) {
      const coRank = authorList.findIndex(x => x.u === coName);
      const coColor = coRank >= 0 && coRank < 15 ? AUTHOR_COLORS[coRank] : '#667';
      html += `<span style="display:inline-block;font-size:11px;margin:2px 4px 2px 0;padding:1px 6px;background:${coColor}22;border:1px solid ${coColor}44;border-radius:3px;color:${coColor};cursor:pointer" data-author="${h(coName)}">${h(coName)} <span style="color:#666;font-size:9px">(${coCount})</span></span>`;
    }
    html += `</div></div>`;
  }

  el.innerHTML = html;
  wireUpDetailLinks(el);
}

// --- EIP AUTHOR DETAIL ---
function showEipAuthorDetail(el, id) {
  const eips = getEips();
  const a = eips?.eipAuthors?.[id];
  if (!a) {
    el.innerHTML = `<p style="color:#888">EIP Author "${id}" not found</p>`;
    return;
  }

  const aliasMap = eips?.authorLinks?.eipAliasToCanonical || {};
  const linkedEth = linkedEthAuthors(a.n, aliasMap);

  // Identity tabs
  let identityTabs = '';
  if (linkedEth.length > 0) {
    identityTabs = `<div class="author-tab-wrap" style="margin-top:2px;margin-bottom:10px">
      <span class="author-tab" data-author="${h(linkedEth[0])}">ethresearch</span>
      <span class="author-tab active">EIPs</span>
    </div>`;
  }

  let html = `<h2>${h(a.n)}</h2>`;
  html += `<div class="meta">EIP Author</div>`;
  html += identityTabs;

  html += `<div class="eip-detail-stat"><span class="label">EIPs</span><span class="value">${(a.eips || []).length}</span></div>`;
  html += `<div class="eip-detail-stat"><span class="label">Influence Score</span><span class="value">${(a.inf || 0).toFixed(3)}</span></div>`;
  if (a.yrs?.length > 0) {
    html += `<div class="eip-detail-stat"><span class="label">Active Years</span><span class="value">${a.yrs.join(', ')}</span></div>`;
  }

  // Linked ethresearch
  if (linkedEth.length > 0) {
    const core = getCore();
    let linkedTopicCount = 0;
    const linkedEthSet = new Set(linkedEth);
    for (const t of Object.values(core?.topics || {})) {
      if (linkedEthSet.has(t.a) || (t.coauth || []).some(u => linkedEthSet.has(u))) {
        linkedTopicCount++;
      }
    }
    html += `<div class="eip-detail-stat"><span class="label">ethresearch</span><span class="value">${linkedEth.map(u => `<span style="cursor:pointer;color:#7788cc" data-author="${h(u)}">${h(u)}</span>`).join(', ')}</span></div>`;
    html += `<div class="eip-detail-stat"><span class="label">Linked Topics</span><span class="value">${linkedTopicCount}</span></div>`;
  }

  // EIP tags
  if (a.eips?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIPs (${a.eips.length})</strong><div style="margin-top:4px">`;
    for (const num of a.eips) {
      html += `<span class="eip-requires-tag" data-eip="${num}">EIP-${num}</span> `;
    }
    html += `</div></div>`;
  }

  if (a.fk?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Forks Contributed</strong><div style="margin-top:4px">`;
    html += a.fk.map(f => `<span class="fork-tag" data-fork="${h(f)}">${h(f)}</span>`).join(' ');
    html += `</div></div>`;
  }

  if (a.st && Object.keys(a.st).length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIP Statuses</strong><div style="margin-top:4px;font-size:11px;color:#aaa">`;
    html += Object.entries(a.st).map(([s, c]) => s + ': ' + c).join(', ');
    html += `</div></div>`;
  }

  el.innerHTML = html;
  wireUpDetailLinks(el);
}

// --- THREAD DETAIL ---
function showThreadDetail(el, id) {
  const core = getCore();
  const th = core?.threads?.[id];
  if (!th) {
    el.innerHTML = `<p style="color:#888">Thread "${id}" not found</p>`;
    return;
  }

  const color = THREAD_COLORS[id] || '#666';
  let html = `<h2 style="color:${color}">${THREAD_NAMES[id] || id}</h2>`;
  if (th.dr) html += `<div class="meta">${h(th.dr)}</div>`;

  html += `<div class="thread-stat-grid">
    <div class="thread-stat-box"><div class="tsb-val">${th.tc || 0}</div><div class="tsb-lbl">Topics</div></div>
    <div class="thread-stat-box"><div class="tsb-val">${(th.ay || []).length || th.ad || 0}</div><div class="tsb-lbl">Active Years</div></div>
    <div class="thread-stat-box"><div class="tsb-val">${th.py || '\u2014'}</div><div class="tsb-lbl">Peak Year</div></div>
    <div class="thread-stat-box"><div class="tsb-val">${(th.eips || th.te || []).length}</div><div class="tsb-lbl">EIP mentions</div></div>
  </div>`;

  // Key authors
  if (th.ka && Object.keys(th.ka).length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Key Authors</strong><div style="margin-top:4px">`;
    for (const [name, count] of Object.entries(th.ka)) {
      html += `<span style="display:inline-block;font-size:11px;margin:2px 4px 2px 0;padding:1px 6px;background:#33334422;border:1px solid #44445544;border-radius:3px;color:#8899cc;cursor:pointer" data-author="${h(name)}">${h(name)} <span style="color:#666;font-size:9px">(${count})</span></span>`;
    }
    html += `</div></div>`;
  }

  // Milestones
  if (th.ms?.length > 0) {
    html += `<div style="margin:12px 0"><strong style="font-size:11px;color:#888">Influential Posts</strong><div class="milestone-list">`;
    for (const ms of th.ms) {
      const label = MILESTONE_LABELS[ms.n] || ms.n?.replace('_', ' ') || '';
      html += `<div class="milestone-item">
        <span class="ms-note">${label}</span>
        <span class="ms-title" data-topic="${ms.id}">${h(ms.t)}</span>
        <span style="color:#666;font-size:10px;flex-shrink:0">${(ms.d || '').slice(0, 7)}</span>
      </div>`;
    }
    html += `</div></div>`;
  }

  // Top EIPs
  const topEips = th.te || th.eips || [];
  if (topEips.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Top EIPs</strong> `;
    for (const eip of topEips) {
      html += `<span class="eip-tag primary" data-eip="${eip}">EIP-${eip}</span> `;
    }
    html += `</div>`;
  }

  // Top topics
  if (th.tops?.length > 0) {
    html += `<div class="detail-refs"><h4>Top Topics</h4>`;
    for (const tid of th.tops.slice(0, 15)) {
      const topic = core.topics?.[tid];
      if (topic) {
        html += `<div class="ref-item"><a data-topic="${tid}">${h(topic.t)}</a></div>`;
      }
    }
    html += `</div>`;
  }

  el.innerHTML = html;
  wireUpDetailLinks(el);
}

// --- FORK DETAIL ---
function showForkDetail(el, id) {
  const core = getCore();
  const fork = core?.forks?.find(f => f.n === id || f.cn === id);
  if (!fork) {
    el.innerHTML = `<p style="color:#888">Fork "${id}" not found</p>`;
    return;
  }

  let html = `<h2>${h(fork.cn || fork.n)}</h2>`;
  html += `<div class="meta">${fork.d || ''}</div>`;
  if (fork.el || fork.cl) {
    html += `<div class="detail-stat"><span class="label">EL</span><span class="value">${fork.el || '-'}</span></div>`;
    html += `<div class="detail-stat"><span class="label">CL</span><span class="value">${fork.cl || '-'}</span></div>`;
  }

  if (fork.eips?.length > 0) {
    html += `<div style="margin-top:8px"><strong style="font-size:11px;color:#888">EIPs (${fork.eips.length}):</strong> `;
    for (const eip of fork.eips) {
      html += `<span class="eip-tag" data-eip="${eip}">EIP-${eip}</span> `;
    }
    html += `</div>`;
  }

  if (fork.rt?.length > 0) {
    html += `<div class="detail-refs"><h4>Related Topics</h4>`;
    for (const tid of fork.rt) {
      const topic = core.topics?.[tid];
      if (topic) {
        html += `<div class="ref-item"><a data-topic="${tid}">${h(topic.t)}</a></div>`;
      }
    }
    html += `</div>`;
  }

  el.innerHTML = html;
  wireUpDetailLinks(el);
}

// --- ERA DETAIL ---
function showEraDetail(el, id) {
  const core = getCore();
  const era = core?.eras?.find(e => e.id === id || e.name === id);
  if (!era) {
    el.innerHTML = `<p style="color:#888">Era "${id}" not found</p>`;
    return;
  }

  el.innerHTML = `<h2>${h(era.name)}</h2>
    <div class="meta">${era.start || ''} \u2013 ${era.end || ''}</div>
    <p style="color:#999;font-size:12px;margin-top:8px">${h(era.description || '')}</p>`;
}

// --- MAGICIANS DETAIL ---
function showMagiciansDetail(el, id) {
  const graphData = getGraph();
  const mt = graphData?.magiciansTopics?.[String(id)];

  if (!mt) {
    el.innerHTML = `<h2>Magicians Topic #${id}</h2>
      <div class="meta">
        <a href="https://ethereum-magicians.org/t/${id}" target="_blank" style="color:#bb88cc">
          ethereum-magicians.org \u2192
        </a>
      </div>`;
    return;
  }

  const title = mt.t || 'Untitled Topic (M#' + id + ')';
  const authorName = (mt.a || 'unknown').trim();
  const linkedEth = linkedEthAuthorsFromMag(authorName);
  const linkedEip = linkedEipAuthorsFromMag(authorName);
  const authorLinkable = linkedEth.length > 0 || linkedEip.length > 0;
  const authorHtml = authorLinkable
    ? `<span style="cursor:pointer;color:#7788cc" data-author="${h(linkedEth[0] || authorName)}">${h(authorName)}</span>`
    : `<strong>${h(authorName)}</strong>`;

  let html = `<h2>${h(title)}</h2>`;
  html += `<div class="meta">M#${id} \u00b7 by ${authorHtml} \u00b7 ${mt.d || ''}
    \u00b7 <a href="https://ethereum-magicians.org/t/${mt.sl ? encodeURIComponent(mt.sl) + '/' : ''}${id}" target="_blank">Open on ethereum-magicians.org \u2192</a></div>`;

  html += `<div class="detail-stat"><span class="label">Views</span><span class="value">${Number(mt.vw || 0).toLocaleString()}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Likes</span><span class="value">${Number(mt.lk || 0).toLocaleString()}</span></div>`;
  html += `<div class="detail-stat"><span class="label">Posts</span><span class="value">${Number(mt.pc || 0).toLocaleString()}</span></div>`;

  if (linkedEth.length > 0) {
    html += `<div class="detail-stat"><span class="label">ethresearch</span><span class="value">${linkedEth.map(u => `<span style="cursor:pointer;color:#7788cc" data-author="${h(u)}">${h(u)}</span>`).join(', ')}</span></div>`;
  }
  if (linkedEip.length > 0) {
    html += `<div class="detail-stat"><span class="label">EIP Authors</span><span class="value">${linkedEip.map(n => `<span style="cursor:pointer;color:#7788cc" data-eip-author="${h(n)}">${h(n)}</span>`).join(', ')}</span></div>`;
  }
  if (mt.cat) {
    html += `<div class="detail-stat"><span class="label">Category</span><span class="value">${h(mt.cat)}</span></div>`;
  }

  // Related EIPs
  if (mt.eips?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Related EIPs</strong> `;
    for (const e of mt.eips) {
      html += `<span class="eip-tag primary" data-eip="${e}">EIP-${e}</span> `;
    }
    html += `</div>`;
  }

  // Tags
  if (mt.tg?.length > 0) {
    html += `<div style="margin:8px 0"><strong style="font-size:11px;color:#666">Tags</strong> `;
    html += mt.tg.map(tag => `<span class="eip-tag" style="border-color:#6a4a85;color:#c8b5db">${h(tag)}</span>`).join(' ');
    html += `</div>`;
  }

  // Related ethresearch topics
  const core = getCore();
  if (mt.er?.length > 0) {
    const relTopics = mt.er.map(tid => core?.topics?.[tid]).filter(Boolean)
      .sort((a, b) => (b.inf || 0) - (a.inf || 0));
    if (relTopics.length > 0) {
      html += `<div class="detail-refs"><h4>Related ethresear.ch Topics (${relTopics.length})</h4>`;
      for (const t of relTopics.slice(0, 12)) {
        html += `<div class="ref-item"><a data-topic="${t.id}">${h(t.t)}</a></div>`;
      }
      html += `</div>`;
    }
  }

  el.innerHTML = html;
  wireUpDetailLinks(el);
}

// --- EIP POPOVER ---
export function showEipPopover(eipNum, anchorEl) {
  const pop = document.getElementById('eip-popover');
  if (!pop) return;

  const eips = getEips();
  const eip = eips?.eipCatalog?.[String(eipNum)];

  if (!eip) {
    pop.innerHTML = `<h3>EIP-${eipNum}</h3><div style="color:#888">No metadata available</div>
      <div style="margin-top:8px"><a href="https://eips.ethereum.org/EIPS/eip-${eipNum}" target="_blank" class="magicians-link">View on eips.ethereum.org &#8599;</a></div>`;
  } else {
    const statusClass = 'eip-status eip-status-' + (eip.s || '').toLowerCase().replace(/\s+/g, '');
    let html = `<h3>EIP-${eipNum}: ${h(eip.t || '')}</h3>`;
    html += `<span class="${statusClass}">${h(eip.s || 'Unknown')}</span>`;
    const typeCat = [eip.ty, eip.c].filter(Boolean);
    if (typeCat.length) html += `<div style="margin-top:6px;color:#aaa;font-size:11px">${typeCat.map(h).join(' \u00b7 ')}</div>`;
    if (eip.fk) html += `<div style="margin-top:4px"><span class="fork-tag">${h(eip.fk)}</span></div>`;
    if (eip.cr) html += `<div style="margin-top:4px;color:#888;font-size:11px">Created: ${h(eip.cr)}</div>`;
    if (eip.au?.length > 0) {
      html += `<div style="margin-top:4px;color:#888;font-size:11px">Authors: ${eip.au.map(h).join(', ')}</div>`;
    }
    if (eip.rq?.length > 0) {
      html += `<div style="margin-top:6px;font-size:11px;color:#888">Requires: ${eip.rq.map(r => `<span class="eip-tag" data-eip="${r}">EIP-${r}</span>`).join(' ')}</div>`;
    }
    html += `<div style="margin-top:8px;display:flex;flex-direction:column;gap:3px">`;
    html += `<a href="https://eips.ethereum.org/EIPS/eip-${eipNum}" target="_blank" class="magicians-link">View on eips.ethereum.org &#8599;</a>`;
    if (eip.mt) html += `<a href="https://ethereum-magicians.org/t/${eip.mt}" target="_blank" class="magicians-link">Magicians discussion &#8599;</a>`;
    if (eip.et) html += `<a href="https://ethresear.ch/t/${eip.et}" target="_blank" class="magicians-link">ethresear.ch discussion &#8599;</a>`;
    html += `</div>`;

    // Related topics quick view
    const coreIndexes = getCoreIndexes();
    const core = getCore();
    const relTopicIds = coreIndexes?.eipToTopics?.[String(eipNum)];
    if (relTopicIds && relTopicIds.size > 0) {
      const sorted = Array.from(relTopicIds).map(tid => core?.topics?.[tid]).filter(Boolean)
        .sort((a, b) => (b.inf || 0) - (a.inf || 0)).slice(0, 5);
      if (sorted.length > 0) {
        html += `<div style="margin-top:8px;border-top:1px solid #333;padding-top:6px">`;
        html += `<div style="font-size:10px;color:#666;margin-bottom:4px">Related topics (${relTopicIds.size})</div>`;
        for (const rt of sorted) {
          html += `<div style="font-size:11px;padding:2px 0"><a data-topic="${rt.id}" style="color:#7788cc;cursor:pointer">${h(rt.t)}</a></div>`;
        }
        html += `</div>`;
      }
    }

    pop.innerHTML = html;
  }

  // Position near the anchor
  pop.style.display = 'block';
  if (anchorEl) {
    const rect = anchorEl.getBoundingClientRect();
    let x = rect.right + 8;
    let y = rect.top;
    const pw = pop.offsetWidth;
    const ph = pop.offsetHeight;
    if (x + pw > window.innerWidth - 10) x = rect.left - pw - 8;
    if (y + ph > window.innerHeight - 10) y = window.innerHeight - ph - 10;
    if (y < 5) y = 5;
    pop.style.left = x + 'px';
    pop.style.top = y + 'px';
  }

  wireUpDetailLinks(pop);
}

// --- EIP POPOVER DISMISS ---
let popoverHideTimer = null;

function dismissEipPopover() {
  const pop = document.getElementById('eip-popover');
  if (pop) pop.style.display = 'none';
}

// Click outside eip-popover dismisses it
document.addEventListener('click', (e) => {
  if (!e.target.closest('#eip-popover') && !e.target.closest('[data-eip]')) {
    dismissEipPopover();
  }
});

// --- WIRE UP ALL CLICKABLE LINKS ---
function wireUpDetailLinks(container) {
  for (const a of container.querySelectorAll('[data-topic]')) {
    a.style.cursor = 'pointer';
    a.addEventListener('click', (e) => {
      e.stopPropagation();
      selectEntity({ type: 'topic', id: Number(a.dataset.topic) });
    });
  }
  for (const tag of container.querySelectorAll('[data-eip]')) {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      dismissEipPopover();
      selectEntity({ type: 'eip', id: tag.dataset.eip });
    });
    // Hover popover
    tag.addEventListener('mouseenter', (e) => {
      clearTimeout(popoverHideTimer);
      showEipPopover(tag.dataset.eip, tag);
    });
    tag.addEventListener('mouseleave', () => {
      popoverHideTimer = setTimeout(dismissEipPopover, 300);
    });
  }
  // Keep popover open when hovering on it
  const pop = document.getElementById('eip-popover');
  if (pop) {
    pop.addEventListener('mouseenter', () => { clearTimeout(popoverHideTimer); });
    pop.addEventListener('mouseleave', () => { popoverHideTimer = setTimeout(dismissEipPopover, 300); });
  }
  for (const tag of container.querySelectorAll('[data-fork]')) {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      selectEntity({ type: 'fork', id: tag.dataset.fork });
    });
  }
  for (const tag of container.querySelectorAll('[data-author]')) {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      selectEntity({ type: 'author', id: tag.dataset.author });
    });
  }
  for (const tag of container.querySelectorAll('[data-eip-author]')) {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      selectEntity({ type: 'eipAuthor', id: tag.dataset.eipAuthor });
    });
  }
  for (const tag of container.querySelectorAll('[data-magicians]')) {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      selectEntity({ type: 'magicians', id: tag.dataset.magicians });
    });
  }
  for (const tag of container.querySelectorAll('[data-paper]')) {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      selectEntity({ type: 'paper', id: tag.dataset.paper });
    });
  }
  for (const tag of container.querySelectorAll('[data-thread]')) {
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      setFilters({ activeThread: tag.dataset.thread });
    });
  }
  for (const tag of container.querySelectorAll('[data-category]')) {
    tag.addEventListener('click', (e) => {
      e.stopPropagation();
      setFilters({ activeCategory: tag.dataset.category });
    });
  }
  // Excerpt toggle
  const excerptToggle = container.querySelector('#excerpt-toggle');
  if (excerptToggle) {
    excerptToggle.addEventListener('click', () => {
      const short = container.querySelector('#excerpt-short');
      const full = container.querySelector('#excerpt-full');
      if (short && full) {
        const showing = full.style.display !== 'none';
        short.style.display = showing ? '' : 'none';
        full.style.display = showing ? 'none' : '';
        excerptToggle.textContent = showing ? 'show more' : 'show less';
      }
    });
  }
}

function wireUpActionButtons(container, topicId, core) {
  const lineageBtn = container.querySelector('#lineage-btn');
  if (lineageBtn) {
    lineageBtn.addEventListener('click', () => {
      const st = getState();
      if (st.lineageActive && st.lineageSet.has(topicId)) {
        setLineage(false, new Set(), new Set());
      } else {
        traceLineage(topicId, core);
      }
    });
  }
  const similarBtn = container.querySelector('#similar-btn');
  if (similarBtn) {
    similarBtn.addEventListener('click', () => {
      findSimilar(topicId, core, container);
    });
  }
}

function traceLineage(topicId, core) {
  const topics = core?.topics || {};
  const t = topics[topicId];
  if (!t) return;

  const nodeSet = new Set([topicId]);
  const edgeSet = new Set();

  // BFS upstream (ancestors via outgoing refs), capped at 2 hops (matches v1)
  const upQueue = [{ id: topicId, depth: 0 }];
  const upVisited = new Set([topicId]);
  while (upQueue.length > 0) {
    const cur = upQueue.shift();
    if (cur.depth >= 2) continue;
    const ct = topics[cur.id];
    if (!ct) continue;
    for (const ref of (ct.out || [])) {
      nodeSet.add(ref);
      edgeSet.add(cur.id + '->' + ref);
      if (!upVisited.has(ref)) {
        upVisited.add(ref);
        upQueue.push({ id: ref, depth: cur.depth + 1 });
      }
    }
  }

  // BFS downstream (descendants via incoming refs), capped at 2 hops
  const downQueue = [{ id: topicId, depth: 0 }];
  const downVisited = new Set([topicId]);
  while (downQueue.length > 0) {
    const cur = downQueue.shift();
    if (cur.depth >= 2) continue;
    const ct = topics[cur.id];
    if (!ct) continue;
    for (const ref of (ct.inc || [])) {
      nodeSet.add(ref);
      edgeSet.add(ref + '->' + cur.id);
      if (!downVisited.has(ref)) {
        downVisited.add(ref);
        downQueue.push({ id: ref, depth: cur.depth + 1 });
      }
    }
  }

  setLineage(true, nodeSet, edgeSet);
}

function findSimilar(topicId, core, container) {
  const topics = core?.topics || {};
  const t = topics[topicId];
  if (!t) return;

  // Score all topics by similarity
  const tTags = new Set(t.tg || []);
  const tEips = new Set([...(t.eips || []), ...(t.peips || [])]);
  const scores = [];

  for (const [oid, other] of Object.entries(topics)) {
    const otherId = Number(oid);
    if (otherId === topicId) continue;
    let score = 0;

    // Thread match
    if (t.th && other.th === t.th) score += 1;
    // Tag overlap
    const oTags = new Set(other.tg || []);
    for (const tag of tTags) { if (oTags.has(tag)) score += 0.5; }
    // EIP overlap
    const oEips = new Set([...(other.eips || []), ...(other.peips || [])]);
    for (const eip of tEips) { if (oEips.has(eip)) score += 1; }
    // Author match
    if (t.a === other.a) score += 0.5;
    // Influence boost
    score += Math.min(0.3, (other.inf || 0) / 3);

    if (score >= 1.5) scores.push({ id: otherId, score });
  }

  scores.sort((a, b) => b.score - a.score);
  const top = scores.slice(0, 10);

  // Show in a similar-list div
  let listEl = container.querySelector('#similar-list');
  if (!listEl) {
    listEl = document.createElement('div');
    listEl.id = 'similar-list';
    listEl.className = 'detail-refs';
    container.appendChild(listEl);
  }

  if (top.length === 0) {
    listEl.innerHTML = '<h4>Similar Topics</h4><p style="color:#888;font-size:11px">No similar topics found</p>';
    return;
  }

  let html = `<h4>Similar Topics (${top.length})</h4>`;
  for (const { id, score } of top) {
    const st = topics[id];
    if (!st) continue;
    html += `<div class="ref-item"><a data-topic="${id}">${h(st.t)}</a> <span style="color:#666;font-size:10px">(${score.toFixed(1)})</span></div>`;
  }
  listEl.innerHTML = html;
  wireUpDetailLinks(listEl);
}
