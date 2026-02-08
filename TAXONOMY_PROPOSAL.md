# Research Category Taxonomy — Proposal

## Design Goals

1. **Universal**: Works for topics, EIPs, and papers equally well
2. **Hierarchical**: category + optional subcategory
3. **Complete**: Every protocol-relevant entity gets a category
4. **Balanced**: No category too large (>150 entities) or too small (<10)
5. **Distinct colors**: Each category has a clear, distinguishable color

## Taxonomy

### 1. `consensus` — Consensus & PoS
**Color**: `#e63946` (Red)
PoS protocol design, fork choice, finality, validator mechanics, staking economics.

| Subcategory | Examples |
|---|---|
| `finality` | Casper FFG, SSF, 3SF, finality gadgets, ebb-and-flow |
| `fork_choice` | LMD-GHOST, reorgs, balancing attacks, three attacks |
| `validator` | Committees, attestations, slashing, rainbow staking |
| `issuance` | Rewards, penalties, MVI, staking ratio, yield curves |

### 2. `scaling` — Scaling & Data Availability
**Color**: `#457b9d` (Steel Blue)
Block space, data layer, sharding, erasure coding.

| Subcategory | Examples |
|---|---|
| `sharding` | Original shard chains, cross-shard communication |
| `data_availability` | DAS, PeerDAS, data columns, erasure coding |
| `blobs` | EIP-4844, proto-danksharding, blob gas market |

### 3. `layer2` — Layer 2 & Rollups
**Color**: `#2a9d8f` (Teal)
Off-chain scaling, rollups, bridges, preconfirmations.

| Subcategory | Examples |
|---|---|
| `plasma` | Plasma variants, exits, state channels |
| `optimistic` | Optimistic rollups, fraud proofs, dispute games |
| `zk_rollup` | ZK rollups, validity proofs, proof aggregation |
| `bridge` | Cross-chain, interop, XCLAIM |
| `based` | Based rollups, preconfirmations, based sequencing |

### 4. `mev` — MEV & Block Production
**Color**: `#f4a261` (Orange)
Transaction ordering, builder markets, censorship resistance.

| Subcategory | Examples |
|---|---|
| `pbs` | Proposer-builder separation, ePBS, relays, MEV-Boost |
| `extraction` | Sandwich attacks, frontrunning, Flash Boys 2.0, order flow |
| `censorship` | Inclusion lists, FOCIL, censorship resistance |
| `timing` | Timing games, auction design, slot auctions |

### 5. `fee_markets` — Fee Markets & Gas
**Color**: `#e9c46a` (Gold)
Resource pricing, gas mechanics, EIP-1559, multidimensional fees.

| Subcategory | Examples |
|---|---|
| `eip1559` | Base fee, dynamic pricing, burn mechanism |
| `multidim` | Multidimensional gas, blob fee market |
| `gas` | Gas pricing, opcodes costs, intrinsic gas |

### 6. `execution` — Execution & State
**Color**: `#606c38` (Olive)
EVM, state management, account abstraction, networking.

| Subcategory | Examples |
|---|---|
| `evm` | Opcodes, EOF, precompiles, EVM improvements |
| `state` | Verkle trees, stateless, state expiry, trie design |
| `account` | Account abstraction, ERC-4337, EIP-7702 |
| `networking` | devp2p, gossipsub, portal network |

### 7. `cryptography` — Cryptography
**Color**: `#4361ee` (Royal Blue)
Proof systems, commitments, signatures — foundational crypto.

| Subcategory | Examples |
|---|---|
| `zk_proofs` | SNARKs, STARKs, PLONK, Groth16, recursive proofs |
| `commitments` | KZG, IPA, FRI, polynomial commitments |
| `signatures` | BLS, aggregate sigs, threshold sigs, post-quantum |
| `primitives` | Hash functions, accumulators, Merkle trees |

### 8. `defi` — DeFi & Markets
**Color**: `#7209b7` (Purple)
Market microstructure, AMMs, economic analysis.

| Subcategory | Examples |
|---|---|
| `amm` | AMMs, LVR, impermanent loss, Uniswap |
| `lending` | Lending protocols, stablecoins, liquidations |
| `analysis` | Token economics, mechanism design, empirical market studies |

### 9. `privacy` — Privacy & Identity
**Color**: `#9d4edd` (Magenta)
Private transactions, identity, credentials.

| Subcategory | Examples |
|---|---|
| `mixing` | Tornado, stealth addresses, RLN |
| `identity` | MACI, Semaphore, ZK-passport, credentials |

### 10. `security` — Security & Analysis
**Color**: `#a4161a` (Dark Red)
Attacks, formal verification, smart contract security, measurement.

| Subcategory | Examples |
|---|---|
| `attacks` | Protocol attacks, DoS, consensus attacks |
| `contracts` | Smart contract vulnerabilities, formal verification, auditing |
| `measurement` | Empirical analysis, blockchain data studies, network measurement |

### 11. `governance` — Governance & Social
**Color**: `#bc6c25` (Brown)
On-chain governance, DAOs, meta-protocol processes.

| Subcategory | Examples |
|---|---|
| `governance` | Voting, signaling, DAOs, quadratic funding |
| `meta` | Hardfork meta EIPs, process EIPs, standards |

## Coverage Analysis

### Current vs Proposed

| Entity Type | Current Coverage | Proposed Coverage |
|---|---|---|
| Topics (600 main) | 474/600 (79%) | ~560/600 (93%) |
| EIPs (885) | 147/885 (17%) | ~550/885 (62%) |
| Papers (651) | 0/651 (0%) | ~490/651 (75%) |

Note: 365 "Moved" ERCs (EIP→ERC redirects with `title=None`) are excluded. Papers with relevance_score < 10 are mostly "blockchain for X" and stay uncategorized — this is correct behavior.

## Key Design Decisions

1. **SSF merged into `consensus`** (subcategory `finality`) — not a standalone thread
2. **"Inclusion Lists" merged into `mev`** (subcategory `censorship`) — tightly coupled
3. **"Based preconf" merged into `layer2`** (subcategory `based`) — it's about L2 sequencing
4. **"Issuance" merged into `consensus`** (subcategory `issuance`) — closely related to validator economics
5. **New "cryptography" category** — catches ZK papers, commitment schemes, signature research
6. **New "defi" category** — catches AMM/DEX/market microstructure papers
7. **New "security" category** — catches smart contract analysis, attack papers
8. **New "governance" category** — catches governance, DAOs, mechanism design
9. **Subcategories are optional** — entities get a primary category always, subcategory when detectable
10. **One level of hierarchy** — deeper nesting adds complexity without much benefit

## Color Palette

11 colors, designed for distinguishability on both dark and light backgrounds:

```
consensus:    #e63946  (Red)
scaling:      #457b9d  (Steel Blue)
layer2:       #2a9d8f  (Teal)
mev:          #f4a261  (Orange)
fee_markets:  #e9c46a  (Gold)
execution:    #606c38  (Olive)
cryptography: #4361ee  (Royal Blue)
defi:         #7209b7  (Purple)
privacy:      #9d4edd  (Magenta)
security:     #a4161a  (Dark Red)
governance:   #bc6c25  (Brown)
```

## Migration from Current System

The current 11 threads map cleanly:
- `pos_casper` → `consensus`
- `sharding_da` → `scaling`
- `plasma_l2` → `layer2`
- `pbs_mev` → `mev`
- `fee_markets` → `fee_markets` (unchanged)
- `state_execution` → `execution`
- `zk_proofs` → `cryptography`
- `privacy_identity` → `privacy`
- `issuance_economics` → `consensus` (subcategory `issuance`)
- `inclusion_lists` → `mev` (subcategory `censorship`)
- `based_preconf` → `layer2` (subcategory `based`)

The 3 merged threads (issuance, inclusion lists, based preconf) had the fewest topics (15, 17, 12) and are closely related to their new parents.
