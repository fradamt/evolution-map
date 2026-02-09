// constants.js — Thread/author colors, EIP status colors, config

export const THREAD_COLORS = {
  consensus: '#e63946',
  scaling: '#457b9d',
  layer2: '#2a9d8f',
  mev: '#f4a261',
  execution: '#606c38',
  cryptography: '#4361ee',
  defi: '#7209b7',
  privacy: '#06b6d4',
  security: '#b45309',
  governance: '#eab308',
};

export const THREAD_ORDER = [
  'consensus', 'scaling', 'layer2', 'mev',
  'execution', 'cryptography', 'defi', 'privacy',
  'security', 'governance',
];

export const THREAD_NAMES = {
  consensus: 'Consensus',
  scaling: 'Scaling',
  layer2: 'Layer 2',
  mev: 'MEV & Fees',
  execution: 'Execution',
  cryptography: 'Cryptography',
  defi: 'DeFi',
  privacy: 'Privacy',
  security: 'Security',
  governance: 'Governance',
};

export const AUTHOR_COLORS = [
  '#e63946', '#457b9d', '#2a9d8f', '#e9c46a', '#f4a261',
  '#d62828', '#6a994e', '#bc6c25', '#7209b7', '#4361ee',
  '#606c38', '#9d4edd', '#264653', '#a8dadc', '#b5838d',
];

export const EIP_STATUS_COLORS = {
  Final: '#4caf50',
  Living: '#26c6da',
  Review: '#fdd835',
  'Last Call': '#fdd835',
  Draft: '#42a5f5',
  Stagnant: '#666',
  Withdrawn: '#555',
  Moved: '#555',
};

export const PAPER_MATCH_MODES = {
  strict: {
    label: 'strict',
    limit: 12,
    relevanceWeight: 0.75,
    minTopic: 3.9,
    minEip: 4.5,
    minFork: 3.9,
    minAuthor: 3.8,
    minEipAuthor: 3.8,
  },
  balanced: {
    label: 'balanced',
    limit: 18,
    relevanceWeight: 1.0,
    minTopic: 2.9,
    minEip: 3.4,
    minFork: 3.0,
    minAuthor: 3.0,
    minEipAuthor: 3.0,
  },
  loose: {
    label: 'loose',
    limit: 28,
    relevanceWeight: 1.2,
    minTopic: 2.1,
    minEip: 2.6,
    minFork: 2.3,
    minAuthor: 2.2,
    minEipAuthor: 2.2,
  },
};

export const MILESTONE_LABELS = {
  earliest: 'Earliest topic',
  latest: 'Most recent topic',
  peak_influence: 'Most influential topic',
  peak_citations: 'Most cited within thread',
  interval: 'Key topic in this period',
};

// Paper visibility limits per layer mode
export const PAPER_LAYER_LIMITS = {
  focus: 200,
  context: 400,
  broad: 1499,
};

// Default influence slider threshold (0 = show all)
export const DEFAULT_MIN_INFLUENCE = 0;

// Timeline zoom extent
export const TIMELINE_ZOOM_EXTENT = [1, 8];

// Network zoom extent
export const NETWORK_ZOOM_EXTENT = [0.15, 5];

// Canvas DPR cap
export const MAX_DPR = 2.0;
