// search.js — Debounced search with dropdown

import { THREAD_COLORS, AUTHOR_COLORS } from './constants.js';
import { getState, selectEntity, hoverEntity, emit } from './state.js';
import { getEips, loadEips, getPapers, loadPapers } from './data.js';
import { linkedEipAuthors, linkedEthAuthors } from './identity.js';

let coreData = null;
let searchTimeout = null;
let activeIndex = -1;

export function init(core) {
  coreData = core;
  const input = document.getElementById('search-box');
  const dropdown = document.getElementById('search-dropdown');
  if (!input || !dropdown) return;

  input.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const q = input.value.toLowerCase().trim();
      if (!q) {
        dropdown.style.display = 'none';
        activeIndex = -1;
        return;
      }
      runSearch(q, dropdown);
    }, 150);
  });

  input.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('.search-item');
    if (!items.length || dropdown.style.display === 'none') return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      updateActiveItem(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      updateActiveItem(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < items.length) {
        items[activeIndex].click();
      } else if (items.length > 0) {
        items[0].click();
      }
    } else if (e.key === 'Escape') {
      dropdown.style.display = 'none';
      activeIndex = -1;
      input.blur();
    }
  });

  input.addEventListener('focus', () => {
    if (input.value.trim().length >= 2) {
      runSearch(input.value.toLowerCase().trim(), document.getElementById('search-dropdown'));
    }
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrap')) {
      dropdown.style.display = 'none';
      activeIndex = -1;
    }
  });
}

// --- Text normalization for paper search ---

function normalizeSearchText(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function tokenizeSearchText(value) {
  const norm = normalizeSearchText(value);
  if (!norm) return [];
  return norm.split(/\s+/).filter(Boolean);
}

function paperAuthorsShort(paper, maxCount) {
  const authors = (paper && paper.a) ? paper.a : [];
  if (authors.length === 0) return '';
  const max = Math.max(1, maxCount || 3);
  if (authors.length <= max) return authors.join(', ');
  return authors.slice(0, max).join(', ') + ' +' + (authors.length - max);
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// --- Main search logic ---

async function runSearch(q, dropdown) {
  // Lazy-load EIPs when searching for EIP patterns
  if (/^eip[- ]?\d*/i.test(q) && !getEips()) {
    await loadEips();
  }

  const view = getState().view;

  // In coauthor view, only show author results
  if (view === 'coauthor') {
    runCoauthorSearch(q, dropdown);
    return;
  }

  // --- Collect results from each category ---

  // 1. EIP results (by number or title)
  const eipResults = searchEips(q);

  // 2. EIP author results
  const eipAuthorResults = searchEipAuthors(q);

  // 3. Ethresearch author results (with EIP alias matching)
  const authorResults = searchAuthors(q);

  // 4. Paper results (with sophisticated scoring)
  const paperResults = searchPapers(q);

  // 5. Topic results (with scoring across multiple fields)
  const topicResults = searchTopics(q);

  // Slice to fit in dropdown (8 items total budget)
  const eipSlice = eipResults.slice(0, 3);
  const eipAuthorSlice = eipAuthorResults.slice(0, 2);
  const authorSlice = authorResults.slice(0, 3);
  const paperSlice = paperResults.slice(0, 4);
  const maxTopics = Math.max(0, 8 - eipSlice.length - eipAuthorSlice.length - authorSlice.length - paperSlice.length);
  const topicSlice = topicResults.slice(0, maxTopics);

  // Build dropdown HTML
  activeIndex = -1;
  dropdown.innerHTML = '';

  const allSlices = [
    ...eipSlice.map(r => renderEipItem(r)),
    ...eipAuthorSlice.map(r => renderEipAuthorItem(r)),
    ...authorSlice.map(r => renderAuthorItem(r)),
    ...paperSlice.map(r => renderPaperItem(r)),
    ...topicSlice.map(r => renderTopicItem(r)),
  ];

  if (allSlices.length === 0) {
    dropdown.style.display = 'none';
    return;
  }

  for (const html of allSlices) {
    dropdown.insertAdjacentHTML('beforeend', html);
  }

  // Attach click handlers
  wireDropdownHandlers(dropdown);

  dropdown.style.display = 'block';
}

// --- Coauthor view search ---

function runCoauthorSearch(q, dropdown) {
  const results = [];
  for (const a of Object.values(coreData?.authors || {})) {
    if ((a.u || '').toLowerCase().includes(q)) {
      results.push(a);
    }
  }
  results.sort((a, b) => (b.inf || 0) - (a.inf || 0));
  const slice = results.slice(0, 8);

  activeIndex = -1;
  dropdown.innerHTML = '';

  if (slice.length === 0) {
    dropdown.style.display = 'none';
    return;
  }

  for (const a of slice) {
    const color = AUTHOR_COLORS[Math.abs(hashStr(a.u)) % AUTHOR_COLORS.length] || '#667';
    dropdown.insertAdjacentHTML('beforeend',
      `<div class="search-item" data-author="${escHtml(a.u)}">
        <div class="si-title"><span style="color:${color}">\u25CF</span> ${escHtml(a.u)}</div>
        <div class="si-meta">${a.tc || 0} topics \u00b7 inf: ${(a.inf || 0).toFixed(2)}</div>
      </div>`
    );
  }

  wireDropdownHandlers(dropdown);
  dropdown.style.display = 'block';
}

// --- Search: EIPs ---

function searchEips(q) {
  const eips = getEips();
  if (!eips?.eipCatalog) return [];
  const results = [];
  for (const [num, eip] of Object.entries(eips.eipCatalog)) {
    const numMatch = num.startsWith(q.replace(/^eip-?/i, '')) || ('eip-' + num).includes(q);
    const titleMatch = eip.t && eip.t.toLowerCase().includes(q);
    if (numMatch || titleMatch) {
      results.push({ num, eip, exact: num === q.replace(/^eip-?/i, '') });
    }
  }
  results.sort((a, b) => (b.exact ? 1 : 0) - (a.exact ? 1 : 0));
  return results;
}

// --- Search: EIP Authors ---

function searchEipAuthors(q) {
  const eips = getEips();
  if (!eips?.eipAuthors) return [];
  const results = [];
  for (const a of Object.values(eips.eipAuthors || {})) {
    const linkedEth = linkedEthAuthors(a.n);
    const linkedMatch = linkedEth.some(u => u.toLowerCase().includes(q));
    if (a.n.toLowerCase().includes(q) || linkedMatch) {
      results.push({ author: a, linkedEth });
    }
  }
  results.sort((a, b) => (b.author.inf || 0) - (a.author.inf || 0));
  return results;
}

// --- Search: ethresearch authors ---

function searchAuthors(q) {
  const results = [];
  for (const a of Object.values(coreData?.authors || {})) {
    const aliases = linkedEipAuthors(a.u || '');
    const aliasMatch = aliases.some(name => name.toLowerCase().includes(q));
    if ((a.u || '').toLowerCase().includes(q) || aliasMatch) {
      results.push({ author: a, aliases });
    }
  }
  results.sort((a, b) => (b.author.inf || 0) - (a.author.inf || 0));
  return results;
}

// --- Search: Papers (sophisticated scoring from reference) ---

function searchPapers(q) {
  const papers = getPapers();
  if (!papers?.papers) return [];

  const qNorm = normalizeSearchText(q);
  const qTokens = tokenizeSearchText(qNorm);
  const results = [];

  for (const [pid, p] of Object.entries(papers.papers)) {
    let score = 0;
    const titleNorm = normalizeSearchText(p.t || '');
    const titleTokens = titleNorm ? titleNorm.split(/\s+/).filter(Boolean) : [];
    const authorNames = p.a || [];
    const authorNormRows = authorNames.map(name => normalizeSearchText(name)).filter(Boolean);
    const tagNormRows = (p.tg || []).map(tag => normalizeSearchText(tag)).filter(Boolean);

    // Author matching with priority levels
    let matchedAuthor = '';
    let authorExact = false;
    let authorTokenMatch = false;
    let authorPrefixMatch = false;
    let authorSubstringMatch = false;

    if (qNorm) {
      for (const name of authorNames) {
        if (matchedAuthor) break;
        const nNorm = normalizeSearchText(name || '');
        if (!nNorm) continue;
        const nTokens = nNorm.split(/\s+/).filter(Boolean);
        if (nNorm === qNorm) {
          matchedAuthor = String(name || '');
          authorExact = true;
          break;
        }
        if (qTokens.length > 0 && qTokens.every(tok => nTokens.indexOf(tok) >= 0)) {
          matchedAuthor = String(name || '');
          authorTokenMatch = true;
          break;
        }
        if (qTokens.length === 1 && qTokens[0].length >= 2 &&
            nTokens.some(tok => tok.indexOf(qTokens[0]) === 0)) {
          matchedAuthor = String(name || '');
          authorPrefixMatch = true;
          break;
        }
        if (nNorm.indexOf(qNorm) >= 0) {
          matchedAuthor = String(name || '');
          authorSubstringMatch = true;
        }
      }
    }

    if (authorExact) score += 8;
    else if (authorTokenMatch) score += 6;
    else if (authorPrefixMatch) score += 4;
    else if (authorSubstringMatch) score += 3;

    // Title matching
    const titleExactTokenMatch = qTokens.length > 0 &&
      qTokens.every(tok => titleTokens.indexOf(tok) >= 0);
    const titlePhraseMatch = qNorm.length >= 4 && titleNorm.indexOf(qNorm) >= 0;
    const titlePrefixMatch = qTokens.length === 1 && qTokens[0].length >= 4 &&
      titleTokens.some(tok => tok.indexOf(qTokens[0]) === 0);
    if (titleExactTokenMatch) score += 3;
    else if (titlePhraseMatch) score += 2;
    else if (titlePrefixMatch) score += 1;

    // Tag matching
    if (qNorm && tagNormRows.some(tag => tag.indexOf(qNorm) >= 0)) score += 1;

    // EIP matching
    if ((p.eq || []).some(e => ('eip-' + e).includes(q) || String(e) === q)) score += 2;

    if (score > 0) {
      results.push({
        paper: p, pid, score, matchedAuthor,
        authorStrong: !!(authorExact || authorTokenMatch || authorPrefixMatch),
        authorExact: !!authorExact,
      });
    }
  }

  results.sort((a, b) => {
    if (Number(b.authorExact || 0) !== Number(a.authorExact || 0))
      return Number(b.authorExact || 0) - Number(a.authorExact || 0);
    if (Number(b.authorStrong || 0) !== Number(a.authorStrong || 0))
      return Number(b.authorStrong || 0) - Number(a.authorStrong || 0);
    if (b.score !== a.score) return b.score - a.score;
    const bCb = Number((b.paper || {}).cb || 0);
    const aCb = Number((a.paper || {}).cb || 0);
    if (bCb !== aCb) return bCb - aCb;
    const bRs = Number((b.paper || {}).rs || 0);
    const aRs = Number((a.paper || {}).rs || 0);
    if (bRs !== aRs) return bRs - aRs;
    return String((a.paper || {}).t || '').localeCompare(String((b.paper || {}).t || ''));
  });

  return results;
}

// --- Search: Topics (multi-field scoring) ---

function searchTopics(q) {
  const results = [];
  for (const t of Object.values(coreData?.topics || {})) {
    let score = 0;
    const tl = (t.t || '').toLowerCase();
    if (tl.includes(q)) score += 3;
    if ((t.a || '').toLowerCase().includes(q)) score += 2;
    if ((t.coauth || []).some(u => u.toLowerCase().includes(q))) score += 2;
    // Check EIP author aliases for topic author
    if (linkedEipAuthors(t.a || '').some(name => name.toLowerCase().includes(q))) score += 2;
    // Check EIP author aliases for coauthors
    if ((t.coauth || []).some(u =>
      linkedEipAuthors(u).some(name => name.toLowerCase().includes(q))
    )) score += 1;
    if (t.cat && t.cat.toLowerCase().includes(q)) score += 1;
    if ((t.eips || []).some(e => ('eip-' + e).includes(q) || ('' + e) === q)) score += 2;
    if ((t.tg || []).some(tag => tag.toLowerCase().includes(q))) score += 1;
    if (score > 0) results.push({ topic: t, score });
  }
  results.sort((a, b) => b.score - a.score || (b.topic.inf || 0) - (a.topic.inf || 0));
  return results;
}

// --- Render functions ---

function renderEipItem(r) {
  const meta = [r.eip.s, r.eip.ty, r.eip.c, r.eip.fk].filter(Boolean).join(' \u00b7 ');
  return `<div class="search-item search-item-eip" data-eip="${r.num}">
    <div class="si-title"><span class="eip-tag primary" style="margin-right:4px">EIP-${r.num}</span>${escHtml(r.eip.t || '')}</div>
    <div class="si-meta">${escHtml(meta)}</div>
  </div>`;
}

function renderEipAuthorItem(r) {
  const a = r.author;
  const linkedEth = r.linkedEth || [];
  const meta = (a.eips || []).length + ' EIPs' +
    (linkedEth.length > 0 ? ' \u00b7 eth: ' + linkedEth[0] + (linkedEth.length > 1 ? ' +' + (linkedEth.length - 1) : '') : '');
  return `<div class="search-item" data-eip-author="${escHtml(a.n)}">
    <div class="si-title"><span style="color:#88aacc">\u25A0</span> ${escHtml(a.n)}</div>
    <div class="si-meta">${escHtml(meta)}</div>
  </div>`;
}

function renderAuthorItem(r) {
  const a = r.author;
  const aliases = r.aliases || [];
  const color = AUTHOR_COLORS[Math.abs(hashStr(a.u)) % AUTHOR_COLORS.length] || '#667';
  const aliasMeta = aliases.length > 0
    ? ' \u00b7 EIP: ' + aliases[0] + (aliases.length > 1 ? ' +' + (aliases.length - 1) : '')
    : '';
  return `<div class="search-item" data-author="${escHtml(a.u)}">
    <div class="si-title"><span style="color:${color}">\u25CF</span> ${escHtml(a.u)}</div>
    <div class="si-meta">${a.tc || 0} topics \u00b7 inf: ${(a.inf || 0).toFixed(2)}${escHtml(aliasMeta)}</div>
  </div>`;
}

function renderPaperItem(r) {
  const p = r.paper || {};
  const year = p.y ? String(p.y) : '?';
  const authorShort = paperAuthorsShort(p, 2);
  let meta = year +
    (authorShort ? ' \u00b7 ' + authorShort : '') +
    (p.cb ? ' \u00b7 OpenAlex cites ' + Number(p.cb).toLocaleString() : '');
  if (r.matchedAuthor) meta += ' \u00b7 author match: ' + r.matchedAuthor;
  return `<div class="search-item search-item-paper" data-paper-id="${escHtml(String(r.pid || p.id || ''))}">
    <div class="si-title"><span style="color:#9cc8ff">\u25C6</span> ${escHtml(p.t || '')}</div>
    <div class="si-meta">${escHtml(meta)}</div>
  </div>`;
}

function renderTopicItem(r) {
  const t = r.topic;
  const thColor = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';
  return `<div class="search-item" data-topic-id="${t.id}">
    <div class="si-title"><span class="si-thread" style="background:${thColor}"></span>${escHtml(t.t || '')}</div>
    <div class="si-meta">${escHtml(t.a || '')} \u00b7 ${(t.d || '').slice(0, 7)} \u00b7 inf: ${(t.inf || 0).toFixed(2)}</div>
  </div>`;
}

// --- Dropdown click/hover handlers ---

function wireDropdownHandlers(dropdown) {
  for (const el of dropdown.querySelectorAll('.search-item')) {
    el.addEventListener('click', () => {
      const topicId = el.dataset.topicId;
      const authorId = el.dataset.author;
      const eipId = el.dataset.eip;
      const eipAuthorId = el.dataset.eipAuthor;
      const paperId = el.dataset.paperId;

      if (eipId) {
        selectEntity({ type: 'eip', id: eipId });
      } else if (paperId) {
        selectEntity({ type: 'paper', id: paperId });
      } else if (eipAuthorId) {
        selectEntity({ type: 'eipAuthor', id: eipAuthorId });
      } else if (topicId) {
        selectEntity({ type: 'topic', id: Number(topicId) });
      } else if (authorId) {
        selectEntity({ type: 'author', id: authorId });
      }

      dropdown.style.display = 'none';
      activeIndex = -1;
      const input = document.getElementById('search-box');
      if (input) input.value = '';
    });

    // Hover to highlight in active view
    el.addEventListener('mouseenter', () => {
      const topicId = el.dataset.topicId;
      if (topicId) {
        hoverEntity({ type: 'topic', id: Number(topicId) });
      }
    });

    el.addEventListener('mouseleave', () => {
      hoverEntity(null);
    });
  }
}

// --- Helpers ---

function updateActiveItem(items) {
  for (let i = 0; i < items.length; i++) {
    items[i].classList.toggle('active', i === activeIndex);
  }
  if (activeIndex >= 0 && items[activeIndex]) {
    items[activeIndex].scrollIntoView({ block: 'nearest' });
  }
}

function hashStr(s) {
  let h = 0;
  for (let i = 0; i < (s || '').length; i++) {
    h = ((h << 5) - h) + s.charCodeAt(i);
    h |= 0;
  }
  return h;
}
