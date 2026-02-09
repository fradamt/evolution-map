// main.js — App init, view switching, hash routing, keyboard shortcuts

import { THREAD_COLORS, THREAD_ORDER } from './constants.js';
import {
  getState, on, setView, setFilters, setContentToggle, setHelp,
  setSidebarWidth, setSidebarHidden, setMilestones, resetAll,
  selectEntity, pinEntity, setDetailOpen,
} from './state.js';
import { loadCore, loadEips, loadPapers, loadGraph, loadCoauthor, getCore, getCoreIndexes } from './data.js';
import { buildIdentityGraph } from './identity.js';

// View modules — lazy imported
let timelineModule = null;
let networkModule = null;
let coauthorModule = null;
let sidebarModule = null;
let detailModule = null;
let searchModule = null;

// --- macOS trackpad swipe-back prevention ---
document.documentElement.style.overscrollBehavior = 'none';
document.body.style.overscrollBehavior = 'none';
document.addEventListener('wheel', function (ev) {
  if (getState().view !== 'timeline') return;
  // Allow scrolling inside detail panel and sidebar
  if (ev.target?.closest?.('#detail-panel')) return;
  if (ev.target?.closest?.('#sidebar')) return;
  if (ev.target?.closest?.('#search-dropdown')) return;
  // Only prevent if inside main-area (timeline) — prevents macOS swipe-back
  if (ev.target?.closest?.('#main-area')) {
    ev.preventDefault();
  }
}, { passive: false, capture: true });


// --- View switching ---
function switchView(name) {
  setView(name);
}

on('view:changed', async ({ current }) => {
  const views = { timeline: 'timeline-view', network: 'network-view', coauthor: 'coauthor-view' };
  for (const [key, id] of Object.entries(views)) {
    const el = document.getElementById(id);
    if (el) el.style.display = key === current ? 'block' : 'none';
  }

  // Update header buttons
  for (const btn of document.querySelectorAll('.controls button[data-view]')) {
    btn.classList.toggle('active', btn.dataset.view === current);
  }

  // Lazy-load view modules and data
  if (current === 'timeline') {
    if (!timelineModule) {
      timelineModule = await import('./timeline.js');
      timelineModule.init();
    }
    timelineModule.onActivate?.();
  } else if (current === 'network') {
    if (!networkModule) {
      await loadGraph();
      networkModule = await import('./network.js');
      networkModule.init();
    }
    networkModule.onActivate?.();
  } else if (current === 'coauthor') {
    if (!coauthorModule) {
      await loadCoauthor();
      coauthorModule = await import('./coauthor.js');
      coauthorModule.init();
    }
    coauthorModule.onActivate?.();
  }
});


// --- Content toggles ---
function toggleContent(type) {
  const st = getState();
  if (type === 'posts') {
    setContentToggle('showPosts', !st.showPosts);
  } else if (type === 'eips') {
    if (!st.showEips) loadEips();
    setContentToggle('showEips', !st.showEips);
  } else if (type === 'magicians') {
    setContentToggle('showMagicians', !st.showMagicians);
  } else if (type === 'papers') {
    if (!st.showPapers) {
      loadPapers();
      setContentToggle('showPapers', true);
    } else {
      // Cycle: focus → context → broad → off
      const modes = ['focus', 'context', 'broad'];
      const idx = modes.indexOf(st.paperLayerMode);
      if (idx < modes.length - 1) {
        setFilters({ paperLayerMode: modes[idx + 1] });
      } else {
        setContentToggle('showPapers', false);
        setFilters({ paperLayerMode: 'focus' });
      }
    }
  }
  updateContentToggleUI();
}

function updateContentToggleUI() {
  const st = getState();
  const postBtn = document.getElementById('toggle-posts');
  const eipBtn = document.getElementById('toggle-eips');
  const magBtn = document.getElementById('toggle-magicians');
  const paperBtn = document.getElementById('toggle-papers');

  if (postBtn) postBtn.classList.toggle('active', st.showPosts);
  if (eipBtn) eipBtn.classList.toggle('active', st.showEips);
  if (magBtn) magBtn.classList.toggle('active', st.showMagicians);
  if (paperBtn) {
    paperBtn.classList.toggle('active', st.showPapers);
    paperBtn.classList.remove('mode-focus', 'mode-context', 'mode-broad');
    if (st.showPapers) paperBtn.classList.add('mode-' + st.paperLayerMode);
  }

  // Show/hide EIP mode toggle based on whether EIPs are active
  let eipModeBtn = document.getElementById('eip-mode-toggle');
  if (st.showEips) {
    if (!eipModeBtn) {
      eipModeBtn = document.createElement('button');
      eipModeBtn.id = 'eip-mode-toggle';
      eipModeBtn.className = 'content-toggle active';
      eipModeBtn.onclick = window.toggleEipMode;
      eipModeBtn.title = 'Toggle between linked EIPs and all EIPs';
      eipModeBtn.style.fontSize = '9px';
      eipBtn.parentNode.insertBefore(eipModeBtn, eipBtn.nextSibling);
    }
    eipModeBtn.textContent = st.eipVisibilityMode === 'all' ? 'All EIPs' : 'Linked EIPs';
    eipModeBtn.style.display = '';
  } else if (eipModeBtn) {
    eipModeBtn.style.display = 'none';
  }
}

on('content:changed', updateContentToggleUI);
on('filters:changed', updateContentToggleUI);


// --- Keyboard shortcuts ---
document.addEventListener('keydown', (e) => {
  // Ignore when typing in inputs
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

  const st = getState();

  if (e.key === '?') {
    e.preventDefault();
    setHelp(!st.helpOpen);
  } else if (e.key === 'Escape') {
    if (st.helpOpen) {
      setHelp(false);
    } else if (st.pinnedEntity || st.selectedEntity) {
      // First Escape: just unpin / deselect (preserves content toggles)
      pinEntity(null);
      selectEntity(null);
    } else {
      // Second Escape (nothing pinned/selected): full reset
      resetAll();
    }
  } else if (e.key === '1') {
    switchView('timeline');
  } else if (e.key === '2') {
    switchView('network');
  } else if (e.key === '3') {
    switchView('coauthor');
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    navigateConnected(e.key === 'ArrowRight' ? 1 : -1);
  }
});

// --- Arrow key navigation between connected topics ---
function navigateConnected(direction) {
  const st = getState();
  if (!st.pinnedTopicId) return;
  const core = getCore();
  const indexes = getCoreIndexes();
  if (!core || !indexes) return;

  const topic = core.topics?.[st.pinnedTopicId];
  if (!topic) return;

  // Gather connected topics (outgoing for right, incoming for left)
  const refs = direction > 0 ? (topic.out || []) : (topic.inc || []);
  if (refs.length === 0) return;

  // Sort by date for chronological navigation
  const sortedRefs = refs
    .map(id => core.topics?.[id])
    .filter(Boolean)
    .sort((a, b) => (a.d || '').localeCompare(b.d || ''));

  if (sortedRefs.length === 0) return;

  // Pick the one with highest influence among connected
  const best = sortedRefs.reduce((a, b) => (b.inf || 0) > (a.inf || 0) ? b : a);
  selectEntity({ type: 'topic', id: best.id });
}


// --- Help overlay ---
on('help:changed', ({ open }) => {
  const overlay = document.getElementById('help-overlay');
  if (overlay) overlay.classList.toggle('open', open);
});


// --- Sidebar ---
function positionSidebarButtons() {
  const sidebar = document.getElementById('sidebar');
  const widthBtn = document.getElementById('sidebar-width-toggle');
  const hideBtn = document.getElementById('sidebar-hide-toggle');
  const st = getState();
  if (sidebar && (widthBtn || hideBtn)) {
    const rect = sidebar.getBoundingClientRect();
    const leftPx = (st.sidebarHidden ? window.innerWidth : rect.left) + 'px';
    if (widthBtn) {
      widthBtn.style.left = leftPx;
      widthBtn.style.display = st.sidebarHidden ? 'none' : '';
    }
    if (hideBtn) hideBtn.style.left = leftPx;
  }
}

on('sidebar:changed', ({ wide, hidden }) => {
  const app = document.getElementById('app');
  if (!app) return;
  app.classList.toggle('sidebar-wide', wide);
  app.classList.toggle('sidebar-hidden', hidden);
  positionSidebarButtons();
});

// Reposition sidebar buttons on window resize
window.addEventListener('resize', positionSidebarButtons);


// --- Detail panel close ---
on('detail:changed', ({ open }) => {
  const panel = document.getElementById('detail-panel');
  if (panel) panel.classList.toggle('open', open);
});

on('selection:changed', ({ current }) => {
  if (current && detailModule) {
    detailModule.show(current);
  }
});


// --- Hash routing (basic) ---
function parseHash() {
  const hash = window.location.hash.slice(1);
  if (!hash) return {};
  const params = {};
  for (const part of hash.split('&')) {
    const [k, v] = part.split('=');
    if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || '');
  }
  return params;
}

function applyHash() {
  const params = parseHash();
  if (params.view) setView(params.view);
  if (params.thread) setFilters({ activeThread: params.thread });
  if (params.author) setFilters({ activeAuthor: params.author });
  if (params.topic) selectEntity({ type: 'topic', id: Number(params.topic) });
  if (params.eip) selectEntity({ type: 'eip', id: params.eip });
  if (params.paper) selectEntity({ type: 'paper', id: params.paper });
  if (params.inf) setFilters({ minInfluence: Number(params.inf) });
  if (params.eipmode) setFilters({ eipVisibilityMode: params.eipmode });
  if (params.eips === '1') { loadEips(); setContentToggle('showEips', true); }
  if (params.papers) {
    loadPapers();
    setContentToggle('showPapers', true);
    if (['focus', 'context', 'broad'].includes(params.papers)) {
      setFilters({ paperLayerMode: params.papers });
    }
  }
  if (params.category) setFilters({ activeCategory: params.category });
  if (params.tag) setFilters({ activeTag: params.tag });
}

export function updateHash() {
  const st = getState();
  const parts = [];
  if (st.view !== 'timeline') parts.push('view=' + st.view);
  if (st.activeThread) parts.push('thread=' + encodeURIComponent(st.activeThread));
  if (st.activeAuthor) parts.push('author=' + encodeURIComponent(st.activeAuthor));
  if (st.activeCategory) parts.push('category=' + encodeURIComponent(st.activeCategory));
  if (st.activeTag) parts.push('tag=' + encodeURIComponent(st.activeTag));
  if (st.selectedEntity) {
    const { type, id } = st.selectedEntity;
    parts.push(type + '=' + encodeURIComponent(id));
  }
  if (st.minInfluence > 0) parts.push('inf=' + st.minInfluence.toFixed(4));
  if (st.showEips) parts.push('eips=1');
  if (st.eipVisibilityMode !== 'connected') parts.push('eipmode=' + st.eipVisibilityMode);
  if (st.showPapers) parts.push('papers=' + st.paperLayerMode);

  const hash = parts.length ? '#' + parts.join('&') : '';
  if (window.location.hash !== hash) {
    history.replaceState(null, '', hash || window.location.pathname);
  }
}

// Update hash on state changes
on('view:changed', updateHash);
on('filters:changed', updateHash);
on('selection:changed', updateHash);
on('content:changed', updateHash);

window.addEventListener('hashchange', applyHash);


// --- Toast notifications ---
let toastTimer = null;
export function showToast(msg) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2500);
}


// --- Expose toggle functions for inline HTML handlers ---
window.showView = switchView;
window.toggleContent = toggleContent;
window.toggleHelp = () => setHelp(!getState().helpOpen);
window.toggleSidebarWidth = () => setSidebarWidth(!getState().sidebarWide);
window.toggleSidebarHidden = () => setSidebarHidden(!getState().sidebarHidden);
window.toggleMilestones = () => {
  const visible = !getState().milestonesVisible;
  setMilestones(visible);
  const btn = document.getElementById('milestone-toggle');
  if (btn) btn.classList.toggle('active', visible);
};
window.toggleEipMode = () => {
  const st = getState();
  const newMode = st.eipVisibilityMode === 'connected' ? 'all' : 'connected';
  setFilters({ eipVisibilityMode: newMode });
  const btn = document.getElementById('eip-mode-toggle');
  if (btn) btn.textContent = newMode === 'all' ? 'All EIPs' : 'Linked EIPs';
};
window.togglePaperMatch = () => {
  const st = getState();
  const modes = ['balanced', 'strict', 'loose'];
  const idx = modes.indexOf(st.paperMatchMode);
  const next = modes[(idx + 1) % modes.length];
  setFilters({ paperMatchMode: next });
  const btn = document.getElementById('paper-match-toggle');
  if (btn) {
    btn.textContent = 'Papers: ' + next;
    btn.classList.remove('mode-strict', 'mode-balanced', 'mode-loose');
    btn.classList.add('mode-' + next);
  }
};
window.closeDetail = () => setDetailOpen(false);


// --- App init ---
async function init() {
  // Load core data first
  const core = await loadCore();

  // Build identity graph from core data (needs authorLinks from eips.json)
  // We'll rebuild it after eips load too — for now use whatever's in core
  buildIdentityGraph(core);

  // Init sidebar and search modules
  [sidebarModule, detailModule, searchModule] = await Promise.all([
    import('./sidebar.js'),
    import('./detail.js'),
    import('./search.js'),
  ]);
  sidebarModule.init(core);
  detailModule.init();
  searchModule.init(core);

  // Init default view (timeline)
  timelineModule = await import('./timeline.js');
  timelineModule.init();

  // Pre-load EIPs in background for identity links and search
  loadEips().then(eipsData => {
    if (eipsData) {
      // Rebuild identity graph with EIP author links
      const merged = { ...core };
      merged.eipAuthors = eipsData.eipAuthors || {};
      merged.authorLinks = eipsData.authorLinks || {};
      merged.magiciansTopics = {};
      buildIdentityGraph(merged);
    }
  });

  // Apply hash state after everything is ready
  applyHash();

  // Update content toggle UI
  updateContentToggleUI();

  // Position sidebar buttons on initial load
  positionSidebarButtons();
}

// Boot
init().catch(err => {
  console.error('Failed to initialize app:', err);
  document.getElementById('main-area').innerHTML =
    '<div style="color:#f66;padding:40px;font-size:14px">Failed to load: ' +
    err.message + '</div>';
});
