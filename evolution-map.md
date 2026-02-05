# Ethereum Research Evolution Map

*An analysis of 2,903 ethresear.ch topics (2017–2026), tracing how ideas became protocol.*

## 1. Executive Summary

From September 2017 to February 2026, the Ethereum research forum accumulated **2,903 topics** — a living record of how one of the most ambitious distributed systems projects evolved in the open.

This analysis identifies **550 influential topics** connected by **1,007 cross-references**, organized into **11 research threads** across **5 eras**, spanning **12 mainnet forks** from Byzantium (2017) through Fusaka (2025).

### Key Findings

- **The forum's center of gravity shifted dramatically.** Early years (2017–2018) were dominated by sharding and Plasma; by 2023–2026, the discourse had moved to PBS, staking economics, and based rollups — reflecting the pivot from execution sharding to a rollup-centric roadmap.
- **Research-to-deployment lag varies widely.** EIP-1559 was discussed on ethresear.ch as early as 2018 and shipped in London (August 2021) — a 3-year cycle. Proposer-builder separation, first formalized in 2021, has its enshrined version (EIP-7732) targeted for Glamsterdam, still unscheduled as of 2026.
- **A small cohort drives outsized impact.** The top 5 authors by influence (vbuterin, JustinDrake, mikeneuder, Nero_eth, aelowsson) created 233 of the included topics — but the community broadened significantly post-2022.

## 2. The Researchers

The ethresear.ch community evolved from a small group of core researchers into a broader ecosystem. Here are the most influential contributors, measured by topic count, citation impact (in-degree from other topics), and community engagement (likes).

### 1. vbuterin

**Active:** 2017–2026 · **Topics:** 145 · **Likes received:** 3587 · **Cited by:** 542 other topics

**Focus areas:** Sharding (44), Proof-of-Stake (29), Economics (19)

**Research threads:** Sharding & Data Availability, Consensus & Finality, Plasma & L2 Scaling

**Most influential topics:**
- [Minimal Viable Plasma](https://ethresear.ch/t/426) (2018, influence: 0.80)
- [On-chain scaling to potentially ~500 tx/sec through mass tx validation](https://ethresear.ch/t/3477) (2018, influence: 0.66)
- [Plasma Cash: Plasma with much less per-user data checking](https://ethresear.ch/t/1298) (2018, influence: 0.65)
- [Sticking to 8192 signatures per slot post-SSF: how and why](https://ethresear.ch/t/17989) (2023, influence: 0.60)
- [Explanation of DAICOs](https://ethresear.ch/t/465) (2018, influence: 0.56)

**Frequent collaborators:** kladkogex (38), JustinDrake (20), dankrad (16), jamesray1 (16), denett (15)

Vitalik's research presence on ethresear.ch is unmatched — spanning every major thread from Casper and sharding through PBS and SSF. His posts often serve as foundational framings that the community then iterates on. His posting volume peaked during the Scaling Wars era (2018) and surged again in the Endgame Architecture era (2023–2026) as the protocol's endgame design crystallized.

### 2. JustinDrake

**Active:** 2017–2025 · **Topics:** 41 · **Likes received:** 1092 · **Cited by:** 250 other topics

**Focus areas:** Sharding (29), Layer 2 (3), zk-s[nt]arks (2)

**Research threads:** Sharding & Data Availability, Consensus & Finality, State & Execution Layer

**Most influential topics:**
- [MEV burn—a simple design](https://ethresear.ch/t/15590) (2023, influence: 0.64)
- [Based rollups—superpowers from L1 sequencing](https://ethresear.ch/t/15016) (2023, influence: 0.64)
- [Based preconfirmations](https://ethresear.ch/t/17353) (2023, influence: 0.63)
- [Sharding phase 1 spec (RETIRED)](https://ethresear.ch/t/1407) (2018, influence: 0.52)
- [Native rollups—superpowers from L1 execution](https://ethresear.ch/t/21517) (2025, influence: 0.49)

**Frequent collaborators:** vbuterin (26), kladkogex (18), jamesray1 (9), skilesare (5), MaxC (5)

Justin Drake emerged as the second most prolific researcher, with deep contributions to sharding, data availability, and more recently based rollups and preconfirmations. His work bridges theoretical proposals and practical protocol design, often co-developing ideas that later become EIPs.

### 3. mikeneuder

**Active:** 2023–2025 · **Topics:** 15 · **Likes received:** 532 · **Cited by:** 154 other topics

**Focus areas:** Proof-of-Stake (14), Uncategorized (1)

**Research threads:** PBS, MEV & Block Production, Inclusion Lists & Censorship Resistance, Sharding & Data Availability

**Most influential topics:**
- [Execution Tickets](https://ethresear.ch/t/17944) (2023, influence: 0.56)
- [Increase the MAX_EFFECTIVE_BALANCE – a modest proposal](https://ethresear.ch/t/15801) (2023, influence: 0.49)
- [Why enshrine Proposer-Builder Separation? A viable path to ePBS](https://ethresear.ch/t/15710) (2023, influence: 0.46)
- [Payload-timeliness committee (PTC) – an ePBS design](https://ethresear.ch/t/16054) (2023, influence: 0.44)
- [Unconditional inclusion lists](https://ethresear.ch/t/18500) (2024, influence: 0.42)

**Frequent collaborators:** potuz (5), fradamt (5), The-CTra1n (4), terence (4), Pintail (2)

Mike Neuder rose to prominence in the 2023–2025 period as a key voice on PBS, inclusion lists, and censorship resistance — topics that define the post-MEV research agenda. His work on ePBS and FOCIL directly influenced Glamsterdam planning.

### 4. Nero_eth

**Active:** 2022–2025 · **Topics:** 20 · **Likes received:** 490 · **Cited by:** 65 other topics

**Focus areas:** Execution Layer Research (5), Economics (4), Proof-of-Stake (4)

**Research threads:** PBS, MEV & Block Production, Fee Markets & EIP-1559, Consensus & Finality

**Most influential topics:**
- [On Block Sizes, Gas Limits and Scalability](https://ethresear.ch/t/18444) (2024, influence: 0.35)
- [Analysis on ''Correlated Attestation Penalties''](https://ethresear.ch/t/19244) (2024, influence: 0.34)
- [ERC721 Extension for zk-SNARKs](https://ethresear.ch/t/13237) (2022, influence: 0.34)
- [On Increasing the Block Gas Limit](https://ethresear.ch/t/18567) (2024, influence: 0.33)
- [Cumulative, Non-Expiring Inclusion Lists](https://ethresear.ch/t/16520) (2023, influence: 0.31)

**Frequent collaborators:** tripoli (6), MicahZoltu (5), kladkogex (4), benaadams (3), Evan-Kim2028 (3)

### 5. aelowsson

**Active:** 2021–2025 · **Topics:** 12 · **Likes received:** 183 · **Cited by:** 67 other topics

**Focus areas:** Proof-of-Stake (9), Economics (3)

**Research threads:** Issuance & Staking Economics, PBS, MEV & Block Production, Consensus & Finality

**Most influential topics:**
- [Properties of issuance level: consensus incentives and variability across potential reward curves](https://ethresear.ch/t/18448) (2024, influence: 0.41)
- [Circulating Supply Equilibrium for Ethereum and Minimum Viable Issuance during the Proof-of-Stake Era](https://ethresear.ch/t/10954) (2021, influence: 0.33)
- [Reward curve with tempered issuance: EIP research post](https://ethresear.ch/t/19171) (2024, influence: 0.33)
- [FAQ: Ethereum issuance reduction](https://ethresear.ch/t/19675) (2024, influence: 0.31)
- [Burn incentives in MEV pricing auctions](https://ethresear.ch/t/19856) (2024, influence: 0.30)

**Frequent collaborators:** pa7x1 (2), vbuterin (1), jcschlegel (1), banr1 (1), Ajesiroo (1)

### 6. fradamt

**Active:** 2021–2024 · **Topics:** 7 · **Likes received:** 143 · **Cited by:** 62 other topics

**Focus areas:** Consensus (3), Economics (1), Sharding (1)

**Research threads:** Consensus & Finality, Sharding & Data Availability, PBS, MEV & Block Production

**Most influential topics:**
- [Committee-driven MEV smoothing](https://ethresear.ch/t/10408) (2021, influence: 0.39)
- [View-merge as a replacement for proposer boost](https://ethresear.ch/t/13739) (2022, influence: 0.39)
- [Orbit SSF: solo-staking-friendly validator set management for SSF](https://ethresear.ch/t/19928) (2024, influence: 0.38)
- [From 4844 to Danksharding: a path to scaling Ethereum DA](https://ethresear.ch/t/18046) (2023, influence: 0.32)
- [A simple Single Slot Finality protocol](https://ethresear.ch/t/14920) (2023, influence: 0.30)

**Frequent collaborators:** samueldashadrach (1), pmcgoohan (1), casparschwa (1), djrtwo (1), pop (1)

### 7. barnabe

**Active:** 2020–2025 · **Topics:** 5 · **Likes received:** 197 · **Cited by:** 54 other topics

**Focus areas:** Economics (3), Proof-of-Stake (2)

**Research threads:** Inclusion Lists & Censorship Resistance, Consensus & Finality, Fee Markets & EIP-1559

**Most influential topics:**
- [Unbundling staking: Towards rainbow staking](https://ethresear.ch/t/18683) (2024, influence: 0.51)
- [Unbundling PBS: Towards protocol-enforced proposer commitments (PEPC)](https://ethresear.ch/t/13879) (2022, influence: 0.48)
- [Decoupling throughput from local building](https://ethresear.ch/t/22004) (2025, influence: 0.31)
- [Fun and games with inclusion lists](https://ethresear.ch/t/16557) (2023, influence: 0.30)
- [EIP 1559 simulations](https://ethresear.ch/t/7280) (2020, influence: 0.27)

**Frequent collaborators:** The-CTra1n (1), 0xkydo (1), maniou-T (1), alonmuroch (1), Evan-Kim2028 (1)

### 8. barryWhiteHat

**Active:** 2018–2023 · **Topics:** 12 · **Likes received:** 264 · **Cited by:** 38 other topics

**Focus areas:** Layer 2 (5), zk-s[nt]arks (3), Miscellaneous (2)

**Research threads:** Plasma & L2 Scaling, ZK Proofs & SNARKs/STARKs, Privacy & Identity

**Most influential topics:**
- [Roll_up / roll_back snark side chain ~17000 tps](https://ethresear.ch/t/3675) (2018, influence: 0.37)
- [Against proof of stake for [zk/op]rollup leader election](https://ethresear.ch/t/7698) (2020, influence: 0.33)
- [Why you can't build a private uniswap with ZKPs](https://ethresear.ch/t/7754) (2020, influence: 0.33)
- [Spam resistant block creator selection via burn auction](https://ethresear.ch/t/5851) (2019, influence: 0.33)
- [Understanding sidechains](https://ethresear.ch/t/8045) (2020, influence: 0.31)

**Frequent collaborators:** lsankar4033 (4), adlerjohn (3), kladkogex (3), Mikerah (3), vbuterin (2)

### 9. soispoke

**Active:** 2023–2025 · **Topics:** 7 · **Likes received:** 149 · **Cited by:** 42 other topics

**Focus areas:** Proof-of-Stake (3), Economics (2), Cryptography (1)

**Research threads:** Consensus & Finality, Inclusion Lists & Censorship Resistance, PBS, MEV & Block Production

**Most influential topics:**
- [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) (2024, influence: 0.48)
- [The more, the less censored: Introducing committee-enforced inclusion sets (COMIS) on Ethereum](https://ethresear.ch/t/18835) (2024, influence: 0.28)
- [Game-theoretic Model for MEV-boost Auctions (MMA) 🥊](https://ethresear.ch/t/16206) (2023, influence: 0.28)
- [Empirical analysis of Builders' Behavioral Profiles (BBPs)](https://ethresear.ch/t/16327) (2023, influence: 0.27)
- [Towards Attester-Includer Separation](https://ethresear.ch/t/21306) (2024, influence: 0.25)

**Frequent collaborators:** Kapol (2), quintuskilbourn (1), SilentCicero (1), Nero_eth (1), Pintail (1)

### 10. kladkogex

**Active:** 2018–2021 · **Topics:** 14 · **Likes received:** 277 · **Cited by:** 11 other topics

**Focus areas:** Layer 2 (3), Proof-of-Stake (2), EVM (2)

**Research threads:** Consensus & Finality, Plasma & L2 Scaling, Sharding & Data Availability

**Most influential topics:**
- [Hashgraph Consensus Timing Vulnerability](https://ethresear.ch/t/2120) (2018, influence: 0.33)
- [EVM performance](https://ethresear.ch/t/2791) (2018, influence: 0.31)
- [Using ICOs to fund science](https://ethresear.ch/t/920) (2018, influence: 0.31)
- [Running Deep Learning on EVM](https://ethresear.ch/t/899) (2018, influence: 0.31)
- [Plasma Cash without any blockchain at all](https://ethresear.ch/t/1974) (2018, influence: 0.27)

**Frequent collaborators:** vbuterin (5), MaxC (3), ldct (3), rumkin (3), kfichter (3)

### 11. casparschwa

**Active:** 2021–2024 · **Topics:** 3 · **Likes received:** 163 · **Cited by:** 35 other topics

**Focus areas:** Proof-of-Stake (2), Consensus (1)

**Research threads:** Issuance & Staking Economics, Consensus & Finality, PBS, MEV & Block Production

**Most influential topics:**
- [Endgame Staking Economics: A Case for Targeting](https://ethresear.ch/t/18751) (2024, influence: 0.37)
- [Timing Games: Implications and Possible Mitigations](https://ethresear.ch/t/17612) (2023, influence: 0.35)
- [Change fork choice rule to mitigate balancing and reorging attacks](https://ethresear.ch/t/11127) (2021, influence: 0.22)

**Frequent collaborators:** barnabe (2), MicahZoltu (1), Sotfranc (1), PhABC (1), ileuthwehfoi (1)

### 12. adlerjohn

**Active:** 2019–2019 · **Topics:** 8 · **Likes received:** 75 · **Cited by:** 36 other topics

**Focus areas:** Layer 2 (4), Cryptography (1), Sharding (1)

**Research threads:** Sharding & Data Availability, Plasma & L2 Scaling

**Most influential topics:**
- [Minimal Viable Merged Consensus](https://ethresear.ch/t/5617) (2019, influence: 0.42)
- [On-Chain Non-Interactive Data Availability Proofs](https://ethresear.ch/t/5715) (2019, influence: 0.31)
- [Trustless Two-Way Bridges With Side Chains By Halting](https://ethresear.ch/t/5728) (2019, influence: 0.26)
- [Compact Fraud Proofs for UTXO Chains Without Intermediate State Serialization](https://ethresear.ch/t/5885) (2019, influence: 0.26)
- [Building Scalable Decentralized Payment Systems - Request for Feedback](https://ethresear.ch/t/5312) (2019, influence: 0.26)

**Frequent collaborators:** vbuterin (2), DZack (1), matt (1), TimDaub (1), kladkogex (1)

### 13. kfichter

**Active:** 2018–2018 · **Topics:** 6 · **Likes received:** 114 · **Cited by:** 29 other topics

**Focus areas:** Layer 2 (6)

**Research threads:** Plasma & L2 Scaling

**Most influential topics:**
- [More Viable Plasma](https://ethresear.ch/t/2160) (2018, influence: 0.43)
- [Plasma XT: Plasma Cash with much less per-user data checking](https://ethresear.ch/t/1926) (2018, influence: 0.37)
- [Simple Fast Withdrawals](https://ethresear.ch/t/2128) (2018, influence: 0.37)
- [Reliable Exits of Withheld In-flight Transactions ("Limbo Exits")](https://ethresear.ch/t/1901) (2018, influence: 0.26)
- [Basic Mass Exits for Plasma MVP](https://ethresear.ch/t/3316) (2018, influence: 0.25)

**Frequent collaborators:** vbuterin (2), tasd (2), ldct (2), jdkanani (1), sg (1)

### 14. josojo

**Active:** 2018–2022 · **Topics:** 7 · **Likes received:** 160 · **Cited by:** 19 other topics

**Focus areas:** Layer 2 (2), zk-s[nt]arks (2), Proof-of-Stake (1)

**Research threads:** Plasma & L2 Scaling, Consensus & Finality, PBS, MEV & Block Production

**Most influential topics:**
- [Plasma snapp - fully verified plasma chain](https://ethresear.ch/t/3391) (2018, influence: 0.42)
- [MEV capturing AMM (McAMM)](https://ethresear.ch/t/13336) (2022, influence: 0.38)
- [Batch auctions with uniform clearing price on plasma](https://ethresear.ch/t/2554) (2018, influence: 0.28)
- [Building a decentralized exchange using snarks](https://ethresear.ch/t/3928) (2018, influence: 0.26)
- [Plasma is plasma :)](https://ethresear.ch/t/2195) (2018, influence: 0.26)

**Frequent collaborators:** MihailoBjelic (2), mkoeppelmann (2), kfichter (2), denett (2), keyvank (2)

### 15. cskiraly

**Active:** 2024–2025 · **Topics:** 6 · **Likes received:** 46 · **Cited by:** 35 other topics

**Focus areas:** Networking (4), Sharding (2)

**Research threads:** Sharding & Data Availability

**Most influential topics:**
- [FullDAS: towards massive scalability with 32MB blocks and beyond](https://ethresear.ch/t/19529) (2024, influence: 0.36)
- [LossyDAS: Lossy, Incremental, and Diagonal Sampling for Data Availability](https://ethresear.ch/t/18963) (2024, influence: 0.27)
- [Improving DAS performance with GossipSub Batch Publishing](https://ethresear.ch/t/21713) (2025, influence: 0.25)
- [Accelerating blob scaling with FullDASv2 (with getBlobs, mempool encoding, and possibly RLC)](https://ethresear.ch/t/22477) (2025, influence: 0.21)
- [Is Data Available in the EL Mempool?](https://ethresear.ch/t/22329) (2025, influence: 0.20)

**Frequent collaborators:** Nashatyrev (2), MarcoPolo (2), Evan-Kim2028 (1), pawanjay176 (1), potuz (1)

---

## 3. Research Threads

Each thread traces a line of inquiry from early proposals through protocol deployment. Topics are connected by explicit cross-references — citations that researchers made when building on or responding to prior work.

### Consensus & Finality

**87 topics** · 2017–2025 · Top authors: vbuterin, JustinDrake, kladkogex, djrtwo, nrryuya

**EIPs discussed:** [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559), [EIP-7251](https://eips.ethereum.org/EIPS/eip-7251), [EIP-7547](https://eips.ethereum.org/EIPS/eip-7547), [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)

The Proof-of-Stake thread is the bedrock of ethresear.ch. The forum launched in September 2017 with Casper as the central research question: how to replace proof-of-work with a provably secure proof-of-stake protocol. Early posts explored Casper FFG (the finality gadget) and Casper CBC (the correct-by-construction variant), with Vitalik and Justin Drake as the primary architects.

The thread tracks the full arc from theoretical Casper designs through the beacon chain spec (Phase 0, launched December 2020) to the Merge itself (September 2022). Key inflection points include the pivot from Casper CBC to pure FFG+LMD-GHOST, the decision to separate the beacon chain from execution (leading to the Merge architecture), and the post-Merge focus on validator set management and attestation optimization.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [Sticking to 8192 signatures per slot post-SSF: how and why](https://ethresear.ch/t/17989) | vbuterin | 2023 | 0.60 | EIP-6914, EIP-7251, EIP-7549 |
| [Unbundling staking: Towards rainbow staking](https://ethresear.ch/t/18683) | barnabe | 2024 | 0.51 | EIP-6110, EIP-7251, EIP-7547 |
| [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) | soispoke | 2024 | 0.48 | EIP-1559, EIP-3074, EIP-7547, EIP-7702 |
| [Orbit SSF: solo-staking-friendly validator set management for SSF](https://ethresear.ch/t/19928) | fradamt | 2024 | 0.38 | EIP-7251 |
| [Alternative proposal for early eth1 <-> eth2 merge](https://ethresear.ch/t/6666) | vbuterin | 2019 | 0.37 | — |
| [Latest Casper Basics. Tear it apart](https://ethresear.ch/t/151) | virgil | 2017 | 0.37 | — |
| [Enshrined Eth2 price feeds](https://ethresear.ch/t/7391) | JustinDrake | 2020 | 0.36 | — |
| [RANDAO beacon exploitability analysis, round 2](https://ethresear.ch/t/1980) | vbuterin | 2018 | 0.36 | — |

### Sharding & Data Availability

**90 topics** · 2017–2025 · Top authors: vbuterin, JustinDrake, kladkogex, musalbas, cskiraly

**EIPs discussed:** [EIP-4488](https://eips.ethereum.org/EIPS/eip-4488), [EIP-4844](https://eips.ethereum.org/EIPS/eip-4844), [EIP-7623](https://eips.ethereum.org/EIPS/eip-7623), [EIP-7691](https://eips.ethereum.org/EIPS/eip-7691)

Sharding dominated ethresear.ch's first two years. The original vision was *execution sharding* — running the EVM across many parallel chains. This evolved through a series of increasingly sophisticated proposals: quadratic sharding, super-quadratic sharding, cross-shard transactions, and ultimately the realization that data availability was the core primitive to get right.

By 2020, the pivot to *data availability sharding* was underway, culminating in Danksharding and its pragmatic first step, proto-danksharding (EIP-4844), which shipped in Cancun (March 2024). The thread continues through PeerDAS (EIP-7594), which shipped in Fusaka (December 2025), implementing distributed data availability sampling via data columns.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [Sharding phase 1 spec (RETIRED)](https://ethresear.ch/t/1407) | JustinDrake | 2018 | 0.52 | EIP-101 |
| [Pragmatic signature aggregation with BLS](https://ethresear.ch/t/2105) | JustinDrake | 2018 | 0.45 | — |
| [A simple and principled way to compute rent fees](https://ethresear.ch/t/1455) | vbuterin | 2018 | 0.44 | — |
| [Faster block/blob propagation in Ethereum](https://ethresear.ch/t/21370) | potuz | 2025 | 0.41 | EIP-7870, EIP-7934 |
| [PeerDAS -- a simpler DAS approach using battle-tested p2p components](https://ethresear.ch/t/16541) | djrtwo | 2023 | 0.40 | — |
| [FullDAS: towards massive scalability with 32MB blocks and beyond](https://ethresear.ch/t/19529) | cskiraly | 2024 | 0.36 | EIP-4844 |
| [A minimal sharding protocol that may be worthwhile as a development target now](https://ethresear.ch/t/1650) | vbuterin | 2018 | 0.36 | — |
| [Cross-shard contract yanking](https://ethresear.ch/t/1450) | vbuterin | 2018 | 0.36 | — |

### Plasma & L2 Scaling

**86 topics** · 2018–2026 · Top authors: vbuterin, kfichter, kladkogex, ldct, danrobinson

**EIPs discussed:** [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559), [EIP-7547](https://eips.ethereum.org/EIPS/eip-7547)

The Plasma thread captures one of Ethereum's most dramatic pivots. In 2018, Plasma was the primary L2 scaling solution — Minimal Viable Plasma, Plasma Cash, and Plasma Debit generated enormous discussion. But fundamental data availability challenges led to the rise of rollups by 2019–2020.

The thread traces this transition through optimistic rollups, zk-rollups, and eventually the rollup-centric roadmap that defines Ethereum today. Recent developments include *based rollups* (sequenced by L1 proposers) and *native rollups* — ideas that may eventually dissolve the L1/L2 boundary.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [Minimal Viable Plasma](https://ethresear.ch/t/426) | vbuterin | 2018 | 0.80 | — |
| [Plasma Cash: Plasma with much less per-user data checking](https://ethresear.ch/t/1298) | vbuterin | 2018 | 0.65 | — |
| [Based rollups—superpowers from L1 sequencing](https://ethresear.ch/t/15016) | JustinDrake | 2023 | 0.64 | EIP-1559, EIP-4844 |
| [Native rollups—superpowers from L1 execution](https://ethresear.ch/t/21517) | JustinDrake | 2025 | 0.49 | EIP-1559, EIP-7623, EIP-7862, EIP-7864 |
| [RSA Accumulators for Plasma Cash history reduction](https://ethresear.ch/t/3739) | vbuterin | 2018 | 0.46 | — |
| [Cross-rollup NFT wrapper and migration ideas](https://ethresear.ch/t/10507) | vbuterin | 2021 | 0.44 | — |
| [More Viable Plasma](https://ethresear.ch/t/2160) | kfichter | 2018 | 0.43 | — |
| [Plasma snapp - fully verified plasma chain](https://ethresear.ch/t/3391) | josojo | 2018 | 0.42 | — |

### Fee Markets & EIP-1559

**15 topics** · 2018–2025 · Top authors: vbuterin, Nero_eth, MicahZoltu, barnabe, villanuevawill

**EIPs discussed:** [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559), [EIP-4488](https://eips.ethereum.org/EIPS/eip-4488), [EIP-4844](https://eips.ethereum.org/EIPS/eip-4844), [EIP-7600](https://eips.ethereum.org/EIPS/eip-7600), [EIP-7623](https://eips.ethereum.org/EIPS/eip-7623), [EIP-7691](https://eips.ethereum.org/EIPS/eip-7691)

Fee market research on ethresear.ch predates EIP-1559 and continues well beyond it. The thread began with analysis of first-price auction inefficiencies and gas price volatility, leading to the base fee mechanism that shipped in London (August 2021). But the bigger story is the evolution toward *multidimensional* resource pricing.

EIP-4844 introduced a separate blob gas market in Cancun, and research continues on further resource dimensions (state access, computation, bandwidth). The thread connects directly to EIP-8037 (state growth metering), still in development, which would add a third gas dimension.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [DRAFT: Position paper on resource pricing](https://ethresear.ch/t/2838) | vbuterin | 2018 | 0.44 | EIP-1559 |
| [Multidimensional EIP 1559](https://ethresear.ch/t/11651) | vbuterin | 2022 | 0.39 | EIP-1559, EIP-4337 |
| [A local-node-favoring delta to the scaling roadmap](https://ethresear.ch/t/22368) | vbuterin | 2025 | 0.38 | EIP-4444, EIP-7701 |
| [First and second-price auctions and improved transaction-fee markets](https://ethresear.ch/t/2410) | vbuterin | 2018 | 0.36 | EIP-1559 |
| [On Block Sizes, Gas Limits and Scalability](https://ethresear.ch/t/18444) | Nero_eth | 2024 | 0.35 | EIP-145, EIP-150, EIP-160, EIP-1052 |
| [On Increasing the Block Gas Limit](https://ethresear.ch/t/18567) | Nero_eth | 2024 | 0.33 | EIP-1559, EIP-4444, EIP-4488, EIP-4844 |
| [Make EIP 1559 more like an AMM curve](https://ethresear.ch/t/9082) | vbuterin | 2021 | 0.31 | EIP-1559 |
| [State Providers, Relayers - Bring Back the Mempool](https://ethresear.ch/t/5647) | villanuevawill | 2019 | 0.30 | — |

### PBS, MEV & Block Production

**52 topics** · 2018–2025 · Top authors: mikeneuder, terence, aelowsson, Nero_eth, pmcgoohan

**EIPs discussed:** [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559), [EIP-2930](https://eips.ethereum.org/EIPS/eip-2930), [EIP-4844](https://eips.ethereum.org/EIPS/eip-4844), [EIP-7002](https://eips.ethereum.org/EIPS/eip-7002), [EIP-7251](https://eips.ethereum.org/EIPS/eip-7251), [EIP-7547](https://eips.ethereum.org/EIPS/eip-7547)

Proposer-builder separation emerged from the MEV crisis of 2021. As MEV extraction became systematic, researchers recognized that block building and block proposing needed to be separated to preserve validator decentralization. The thread tracks the evolution from external PBS (via MEV-Boost and Flashbots) to enshrined PBS (ePBS).

Key developments include the original PBS proposal, MEV burn mechanisms (returning MEV value to the protocol), payload timeliness committees, and the ongoing debate about inclusion lists as a complement to ePBS. EIP-7732 (ePBS) is targeted for Glamsterdam, making this one of the longest-running research-to-deployment pipelines on ethresear.ch.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [MEV burn—a simple design](https://ethresear.ch/t/15590) | JustinDrake | 2023 | 0.64 | EIP-1559 |
| [Execution Tickets](https://ethresear.ch/t/17944) | mikeneuder | 2023 | 0.56 | EIP-1559, EIP-7547 |
| [Two-slot proposer/builder separation](https://ethresear.ch/t/10980) | vbuterin | 2021 | 0.49 | EIP-1559 |
| [Proposer/block builder separation-friendly fee market designs](https://ethresear.ch/t/9725) | vbuterin | 2021 | 0.48 | EIP-1559 |
| [Unbundling PBS: Towards protocol-enforced proposer commitments (PEPC)](https://ethresear.ch/t/13879) | barnabe | 2022 | 0.48 | EIP-1559 |
| [Why enshrine Proposer-Builder Separation? A viable path to ePBS](https://ethresear.ch/t/15710) | mikeneuder | 2023 | 0.46 | — |
| [Payload-timeliness committee (PTC) – an ePBS design](https://ethresear.ch/t/16054) | mikeneuder | 2023 | 0.44 | — |
| [Dr. changestuff or: how i learned to stop worrying and love mev-burn](https://ethresear.ch/t/17384) | mikeneuder | 2023 | 0.40 | EIP-1559 |

### Issuance & Staking Economics

**11 topics** · 2018–2024 · Top authors: aelowsson, vbuterin, jgm, econoar, casparschwa

**EIPs discussed:** [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559)

The issuance and staking economics thread gained momentum post-Merge, when Ethereum's monetary policy became a live research question. Core debates include the optimal staking ratio, minimum viable issuance (reducing ETH inflation to the minimum needed for security), and the effects of liquid staking derivatives.

Anders Elowsson, Caspar Schwarz-Schilling, and Barnabé Monnot are the primary contributors, producing detailed quantitative analyses of reward curves and staking equilibria. EIP-7251 (MaxEB increase, shipped in Pectra) emerged partly from this thread's work on validator consolidation economics.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [Increase the MAX_EFFECTIVE_BALANCE – a modest proposal](https://ethresear.ch/t/15801) | mikeneuder | 2023 | 0.49 | EIP-4844, EIP-7002, EIP-7251 |
| [Properties of issuance level: consensus incentives and variability across potential reward curves](https://ethresear.ch/t/18448) | aelowsson | 2024 | 0.41 | — |
| [A signaling theory model of cryptocurrency issuance and value](https://ethresear.ch/t/1081) | vbuterin | 2018 | 0.38 | — |
| [Endgame Staking Economics: A Case for Targeting](https://ethresear.ch/t/18751) | casparschwa | 2024 | 0.37 | EIP-1556, EIP-1559, EIP-4844, EIP-7002 |
| [Circulating Supply Equilibrium for Ethereum and Minimum Viable Issuance during the Proof-of-Stake Era](https://ethresear.ch/t/10954) | aelowsson | 2021 | 0.33 | EIP-1559 |
| [Reward curve with tempered issuance: EIP research post](https://ethresear.ch/t/19171) | aelowsson | 2024 | 0.33 | — |
| [FAQ: Ethereum issuance reduction](https://ethresear.ch/t/19675) | aelowsson | 2024 | 0.31 | EIP-1559 |
| [The economic incentives of staking in Serenity](https://ethresear.ch/t/4157) | econoar | 2018 | 0.31 | — |

### Inclusion Lists & Censorship Resistance

**13 topics** · 2017–2025 · Top authors: vbuterin, soispoke, mikeneuder, Nero_eth, terence

**EIPs discussed:** [EIP-7805](https://eips.ethereum.org/EIPS/eip-7805)

Inclusion lists address censorship resistance — ensuring that even a compromised or extractive builder cannot indefinitely exclude valid transactions. The thread tracks the evolution from simple CR-lists through unconditional inclusion lists to the FOCIL (Fork-Choice Enforced Inclusion Lists) proposal.

Mike Neuder and Francesco (fradamt) are the primary researchers, with contributions examining the interaction between inclusion lists, PBS, and the fork-choice rule. EIP-7805 (FOCIL) is a leading candidate for Glamsterdam, making this an active research-to-deployment pipeline.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [Minimal anti-collusion infrastructure](https://ethresear.ch/t/5413) | vbuterin | 2019 | 0.45 | — |
| [Unconditional inclusion lists](https://ethresear.ch/t/18500) | mikeneuder | 2024 | 0.42 | EIP-1559, EIP-7547 |
| [No free lunch – a new inclusion list design](https://ethresear.ch/t/16389) | mikeneuder | 2023 | 0.39 | EIP-6493 |
| [How much can we constrain builders without bringing back heavy burdens to proposers?](https://ethresear.ch/t/13808) | vbuterin | 2022 | 0.38 | EIP-2718 |
| [Cumulative, Non-Expiring Inclusion Lists](https://ethresear.ch/t/16520) | Nero_eth | 2023 | 0.31 | — |
| [Fun and games with inclusion lists](https://ethresear.ch/t/16557) | barnabe | 2023 | 0.30 | EIP-1559 |
| [Censorship rejection through "suspicion scores"](https://ethresear.ch/t/305) | vbuterin | 2017 | 0.29 | — |
| [One-bit-per-attester inclusion lists](https://ethresear.ch/t/19797) | vbuterin | 2024 | 0.27 | EIP-7547 |

### Based Sequencing & Preconfirmations

**5 topics** · 2023–2025 · Top authors: linoscope, The-CTra1n, diego, JustinDrake, mikeneuder


Based sequencing and preconfirmations represent a frontier research area that gained traction in 2023–2024. "Based rollups" are rollups that use L1 proposers as their sequencer, inheriting L1's liveness and censorship resistance guarantees. Preconfirmations extend this with fast commitments from proposers about future block contents.

Justin Drake is the primary architect of this research direction, which connects to PBS (proposers making commitments) and the broader question of Ethereum's role as a settlement layer. No EIPs have shipped yet, but the area is actively explored for future forks.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [Based preconfirmations](https://ethresear.ch/t/17353) | JustinDrake | 2023 | 0.63 | — |
| [Strawmanning Based Preconfirmations](https://ethresear.ch/t/19695) | linoscope | 2024 | 0.29 | — |
| [Based Preconfirmations with Multi-round MEV-Boost](https://ethresear.ch/t/20091) | linoscope | 2024 | 0.27 | EIP-1559, EIP-4337 |
| [PEPC-DVT: PEPC with no changes to the consensus protocol](https://ethresear.ch/t/16514) | diego | 2023 | 0.26 | EIP-712 |
| [Preconfirmation Fair Exchange](https://ethresear.ch/t/21891) | The-CTra1n | 2025 | 0.22 | — |

### ZK Proofs & SNARKs/STARKs

**28 topics** · 2018–2023 · Top authors: vbuterin, barryWhiteHat, bobbinth, AlexandreBelling, JustinDrake

**EIPs discussed:** [EIP-1108](https://eips.ethereum.org/EIPS/eip-1108), [EIP-2028](https://eips.ethereum.org/EIPS/eip-2028), [EIP-4844](https://eips.ethereum.org/EIPS/eip-4844)

Zero-knowledge proof research on ethresear.ch spans the theoretical foundations (PLONK, STARKs, recursive proofs) and practical applications (zk-rollups, private transactions, proof-of-identity). Barry WhiteHat was an early champion, with posts on Semaphore, MACI, and various mixer designs.

The thread connects to multiple deployment paths: zk-rollups as L2 scaling (zkSync, Scroll, Polygon zkEVM), BLS12-381 precompiles (EIP-2537, shipped in Pectra), and the long-term vision of ZK-proving the entire EVM state transition to enable fully trustless light clients.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [On-chain scaling to potentially ~500 tx/sec through mass tx validation](https://ethresear.ch/t/3477) | vbuterin | 2018 | 0.66 | — |
| [2FA zk-rollups using SGX](https://ethresear.ch/t/14462) | JustinDrake | 2022 | 0.38 | EIP-7212 |
| [Roll_up / roll_back snark side chain ~17000 tps](https://ethresear.ch/t/3675) | barryWhiteHat | 2018 | 0.37 | — |
| [ERC721 Extension for zk-SNARKs](https://ethresear.ch/t/13237) | Nero_eth | 2022 | 0.34 | EIP-1271, EIP-4337, EIP-5564 |
| [Why you can't build a private uniswap with ZKPs](https://ethresear.ch/t/7754) | barryWhiteHat | 2020 | 0.33 | — |
| [Using GKR inside a SNARK to reduce the cost of hash verification down to 3 constraints](https://ethresear.ch/t/7550) | AlexandreBelling | 2020 | 0.32 | — |
| [Hash-based VDFs, MIMC and STARKs](https://ethresear.ch/t/2337) | vbuterin | 2018 | 0.31 | — |
| [Batch Deposits for [op/zk] rollup / mixers / MACI](https://ethresear.ch/t/6883) | barryWhiteHat | 2020 | 0.29 | — |

### State & Execution Layer

**29 topics** · 2017–2025 · Top authors: vbuterin, JustinDrake, AlexeyAkhunov, lithp, gballet

**EIPs discussed:** [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559), [EIP-7701](https://eips.ethereum.org/EIPS/eip-7701), [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702), [EIP-7928](https://eips.ethereum.org/EIPS/eip-7928)

State and execution layer research addresses Ethereum's growing state size and the viability of stateless execution. The thread covers Verkle trees (EIP-6800, targeted for Glamsterdam), state expiry mechanisms, history expiry, and portal networks for distributed state access.

This thread has one of the longest research-to-deployment timelines. Stateless client proposals date to 2017 (among the very first ethresear.ch posts), and the Verkle transition has been discussed since 2020. The execution layer's conservative upgrade approach means state structure changes require extensive testing and coordination across all clients.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [The Stateless Client Concept](https://ethresear.ch/t/172) | vbuterin | 2017 | 0.49 | EIP-648 |
| [Double-batched Merkle log accumulator](https://ethresear.ch/t/571) | JustinDrake | 2018 | 0.36 | — |
| [Binary trie format](https://ethresear.ch/t/7621) | gballet | 2020 | 0.36 | EIP-2930 |
| [State-minimised executions](https://ethresear.ch/t/748) | JustinDrake | 2018 | 0.34 | — |
| [History, state, and asynchronous accumulators in the stateless model](https://ethresear.ch/t/287) | JustinDrake | 2017 | 0.33 | — |
| [A cryptoeconomic accumulator for state-minimised contracts](https://ethresear.ch/t/385) | JustinDrake | 2017 | 0.31 | — |
| [Resurrection-conflict-minimized state bounding, take 2](https://ethresear.ch/t/8739) | vbuterin | 2021 | 0.30 | EIP-2930 |
| [Common classes of contracts and how they would handle ongoing storage maintenance fees ("rent")](https://ethresear.ch/t/4441) | vbuterin | 2018 | 0.29 | — |

### Privacy & Identity

**13 topics** · 2018–2025 · Top authors: vbuterin, Mikerah, barryWhiteHat, EugeRe, kladkogex

**EIPs discussed:** [EIP-7212](https://eips.ethereum.org/EIPS/eip-7212), [EIP-7701](https://eips.ethereum.org/EIPS/eip-7701), [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)

The privacy thread covers both technical mechanisms (mixers, ring signatures, stealth addresses) and identity systems (MACI for anti-collusion voting, zk-passport for citizenship proofs). Barry WhiteHat and the Applied ZK team were early contributors.

While privacy features haven't shipped as core protocol changes, the research influenced application-layer tools (Tornado Cash, Semaphore) and the growing interest in account abstraction (EIP-7702) as a pathway to better privacy at the wallet level.

| Topic | Author | Year | Influence | EIPs |
|-------|--------|------|-----------|------|
| [Ethereum Privacy: The Road to Self-Sovereignty](https://ethresear.ch/t/22115) | pcaversaccio | 2025 | 0.32 | EIP-7503 |
| [Self-Sovereign Identity and Account Abstraction for Privacy-Preserving cross chain user operations across roll ups](https://ethresear.ch/t/19599) | EugeRe | 2024 | 0.32 | EIP-1271, EIP-4337, EIP-6492, EIP-7562 |
| [Cryptoeconomic "ring signatures"](https://ethresear.ch/t/966) | vbuterin | 2018 | 0.31 | — |
| [Open problem: improving stealth addresses](https://ethresear.ch/t/7438) | vbuterin | 2020 | 0.31 | — |
| [Anonymous reputation risking and burning](https://ethresear.ch/t/3926) | barryWhiteHat | 2018 | 0.29 | — |
| [Semaphore RLN, rate limiting nullifier for spam prevention in anonymous p2p setting](https://ethresear.ch/t/5009) | barryWhiteHat | 2019 | 0.28 | — |
| [Proof of Validator: A simple anonymous credential scheme for Ethereum's DHT](https://ethresear.ch/t/16454) | asn | 2023 | 0.27 | — |
| [MACI with mostly-off-chain "happy path"](https://ethresear.ch/t/19527) | vbuterin | 2024 | 0.26 | — |

## 4. Era Analysis

### Genesis (2017–2017)

*Casper basics, stateless clients, early sharding ideas*

**19 included topics**

**What shipped:**
- **Byzantium** (2017-10-16): EIP-100, EIP-140, EIP-196, EIP-197, EIP-198, EIP-211

**Dominant threads:** State & Execution Layer (6), Sharding & Data Availability (5), Consensus & Finality (4), Inclusion Lists & Censorship Resistance (1)

Ethresear.ch launched in September 2017, just weeks before the Byzantium fork brought BN256 precompiles and REVERT to mainnet. The earliest posts read like a brain dump of everything the research team had been thinking about: Casper FFG fundamentals, early sharding designs, and the first sketches of stateless client architectures. The community was small and the discourse was dense — nearly every post was a technical proposal by a core researcher.

Notably, many ideas from this era took years to mature. The proposer/builder separation concept (implicit in early collation proposals), data availability challenges (raised in the context of sharding), and validator economics (Casper deposit mechanics) all planted seeds that would grow into major research threads over the next decade.

**Top topics:**
1. [The Stateless Client Concept](https://ethresear.ch/t/172) by vbuterin (influence: 0.49)
1. [Latest Casper Basics. Tear it apart](https://ethresear.ch/t/151) by virgil (influence: 0.37)
1. [Proposal: Change Ether currency symbol from Ξ to ⧫](https://ethresear.ch/t/120) by virgil (influence: 0.35)
1. [Tradeoffs in Account Abstraction Proposals](https://ethresear.ch/t/263) by vbuterin (influence: 0.35)
1. [History, state, and asynchronous accumulators in the stateless model](https://ethresear.ch/t/287) by JustinDrake (influence: 0.33)

### Scaling Wars (2018–2018)

*Plasma, sharding execution, VDFs, Casper FFG/CBC debates*

**173 included topics**

**What shipped:**
- **Constantinople** (2019-02-28): EIP-145, EIP-1014, EIP-1052, EIP-1234, EIP-1283

**Dominant threads:** Plasma & L2 Scaling (47), Sharding & Data Availability (34), Consensus & Finality (30), State & Execution Layer (8), ZK Proofs & SNARKs/STARKs (7)

2018 was ethresear.ch's most prolific year by topic count, driven by the urgent question: how does Ethereum scale? The Scaling Wars played out across two fronts. On-chain, sharding proposals grew increasingly sophisticated — quadratic sharding gave way to super-quadratic designs, cross-shard communication protocols multiplied, and the first data availability schemes appeared.

Off-chain, Plasma variants proliferated: Minimal Viable Plasma, Plasma Cash, Plasma Debit, Plasma Snapp. VDF research (verifiable delay functions) aimed to solve randomness for validator selection. The Casper FFG vs CBC debate continued, with the community gradually converging on FFG as the practical path.

In retrospect, this era's most lasting contribution was the data availability problem formulation. The recognition that data availability — not execution — was the bottleneck for scaling would reshape the entire roadmap by 2020.

**Top topics:**
1. [Minimal Viable Plasma](https://ethresear.ch/t/426) by vbuterin (influence: 0.80)
1. [On-chain scaling to potentially ~500 tx/sec through mass tx validation](https://ethresear.ch/t/3477) by vbuterin (influence: 0.66)
1. [Plasma Cash: Plasma with much less per-user data checking](https://ethresear.ch/t/1298) by vbuterin (influence: 0.65)
1. [Explanation of DAICOs](https://ethresear.ch/t/465) by vbuterin (influence: 0.56)
1. [Sharding phase 1 spec (RETIRED)](https://ethresear.ch/t/1407) by JustinDrake (influence: 0.52)

### Eth2 Design (2019–2020)

*Phase 0/1 specs, rollup emergence, beacon chain launch*

**141 included topics**

**What shipped:**
- **Istanbul** (2019-12-08): EIP-152, EIP-1108, EIP-1344, EIP-1884, EIP-2028, EIP-2200
- **Phase 0** (2020-12-01): beacon chain genesis

**Dominant threads:** Sharding & Data Availability (30), Consensus & Finality (22), ZK Proofs & SNARKs/STARKs (16), Plasma & L2 Scaling (13), State & Execution Layer (7)

The Eth2 Design era (2019–2020) saw the research community transition from exploration to specification. The beacon chain spec (Phase 0) was finalized and launched in December 2020, marking the first time ethresear.ch research shipped as production code. Phase 1 (data sharding) spec work continued, though it would later be superseded by Danksharding.

Two pivotal shifts happened in this era. First, the rollup-centric roadmap emerged: Vitalik's October 2020 analysis of "eth2 as data availability engine" signaled that execution sharding was being deprioritized in favor of rollups as the primary scaling mechanism. Second, MEV awareness grew as Flashbots documented the scale of miner extractable value, setting the stage for the PBS research thread.

**Top topics:**
1. [Minimal anti-collusion infrastructure](https://ethresear.ch/t/5413) by vbuterin (influence: 0.45)
1. [Minimal Viable Merged Consensus](https://ethresear.ch/t/5617) by adlerjohn (influence: 0.42)
1. [Alternative proposal for early eth1 <-> eth2 merge](https://ethresear.ch/t/6666) by vbuterin (influence: 0.37)
1. [Using polynomial commitments to replace state roots](https://ethresear.ch/t/7095) by vbuterin (influence: 0.37)
1. [Enshrined Eth2 price feeds](https://ethresear.ch/t/7391) by JustinDrake (influence: 0.36)

### Post-Merge Build (2021–2022)

*PBS, EIP-1559, PoW→PoS transition, MEV awareness*

**60 included topics**

**What shipped:**
- **Berlin** (2021-04-15): EIP-2565, EIP-2929, EIP-2718, EIP-2930
- **London** (2021-08-05): EIP-1559, EIP-3198, EIP-3529, EIP-3541, EIP-3554
- **Altair** (2021-10-27): beacon chain genesis
- **The Merge** (2022-09-15): EIP-3675, EIP-4399

**Dominant threads:** Consensus & Finality (13), PBS, MEV & Block Production (12), Plasma & L2 Scaling (10), Fee Markets & EIP-1559 (4), ZK Proofs & SNARKs/STARKs (3)

The 2021–2022 era was bookended by two landmark deployments: EIP-1559 in London (August 2021) and the Merge itself (September 2022). Research during this period focused on making these transitions safe while laying groundwork for the next phase.

PBS emerged as a major research thread, driven by the MEV crisis. The proposer/builder separation went from theoretical concept to externalized implementation (MEV-Boost) to active enshrined design (ePBS). Fee market research continued with analysis of EIP-1559's behavior in practice and early multidimensional gas proposals. The withdrawal mechanism (EIP-4895) was designed for Shapella, completing the Merge's economic loop.

**Top topics:**
1. [Two-slot proposer/builder separation](https://ethresear.ch/t/10980) by vbuterin (influence: 0.49)
1. [Proposer/block builder separation-friendly fee market designs](https://ethresear.ch/t/9725) by vbuterin (influence: 0.48)
1. [Unbundling PBS: Towards protocol-enforced proposer commitments (PEPC)](https://ethresear.ch/t/13879) by barnabe (influence: 0.48)
1. [Cross-rollup NFT wrapper and migration ideas](https://ethresear.ch/t/10507) by vbuterin (influence: 0.44)
1. [Committee-driven MEV smoothing](https://ethresear.ch/t/10408) by fradamt (influence: 0.39)

### Endgame Architecture (2023–2026)

*ePBS, SSF, based rollups, blobs, PeerDAS, staking economics*

**157 included topics**

**What shipped:**
- **Shapella** (2023-04-12): EIP-3651, EIP-3855, EIP-3860, EIP-4895, EIP-6049
- **Dencun** (2024-03-13): EIP-1153, EIP-4788, EIP-4844, EIP-5656, EIP-6780, EIP-7044
- **Pectra** (2025-05-07): EIP-2537, EIP-2935, EIP-6110, EIP-7002, EIP-7251, EIP-7549
- **Fusaka** (2025-12-03): EIP-7594, EIP-7823, EIP-7825, EIP-7883, EIP-7917, EIP-7918
- **Glamsterdam** (TBD): EIP-7732, EIP-7928

**Dominant threads:** PBS, MEV & Block Production (37), Sharding & Data Availability (19), Consensus & Finality (18), Plasma & L2 Scaling (16), Inclusion Lists & Censorship Resistance (10)

The Endgame Architecture era (2023–2026) is defined by protocol maturity. With the Merge complete and blobs live (Dencun, March 2024), research shifted to the "endgame" questions: what does Ethereum look like at steady state?

This era produced the highest topic count, driven by multiple concurrent research frontiers. Staking economics received rigorous treatment (minimum viable issuance, staking ratio targeting). PBS evolved toward ePBS with detailed mechanism design for payload timeliness committees. Inclusion lists and censorship resistance moved from theoretical to concrete (FOCIL, EIP-7805). SSF proposals matured with Orbit SSF. Based rollups and preconfirmations opened a new design space for L1/L2 integration.

Pectra (May 2025) shipped MaxEB (EIP-7251) and in-protocol deposits (EIP-6110), directly influenced by staking economics research. Fusaka (December 2025) delivered PeerDAS (EIP-7594), the first data availability sampling deployment. Glamsterdam, still unscheduled, targets ePBS (EIP-7732) and FOCIL (EIP-7805) — ideas that have been on ethresear.ch for years.

**Top topics:**
1. [MEV burn—a simple design](https://ethresear.ch/t/15590) by JustinDrake (influence: 0.64)
1. [Based rollups—superpowers from L1 sequencing](https://ethresear.ch/t/15016) by JustinDrake (influence: 0.64)
1. [Based preconfirmations](https://ethresear.ch/t/17353) by JustinDrake (influence: 0.63)
1. [Sticking to 8192 signatures per slot post-SSF: how and why](https://ethresear.ch/t/17989) by vbuterin (influence: 0.60)
1. [Execution Tickets](https://ethresear.ch/t/17944) by mikeneuder (influence: 0.56)

## 5. Methodology

### Data Source
All 2,903 topics from ethresear.ch were scraped via the Discourse API, including full post content, cross-references (link_counts), view/like counts, tags, and participant lists.

### Influence Score
Each topic receives a composite score:
```
influence = 0.30 × norm(in_degree)
         + 0.25 × norm(likes)
         + 0.20 × norm(log(views))
         + 0.15 × norm(posts_count)
         + 0.10 × prolific_author
```
Where `norm()` is min-max normalization across all topics, and `prolific_author` is 1.0 if the author has 5+ included topics.

### Topic Filtering
- **Tier 1**: influence ≥ 0.25 or in-degree ≥ 3 (550 topics after adjustment)
- **Tier 2**: referenced by a Tier 1 topic with influence ≥ 0.10
- Final set: **550 topics** from 2,903 total

### Cross-References
Extracted from `post_stream.posts[].link_counts[]` where `internal=true`. Total: 2,620 edges, 1,007 after filtering to included topics.

### Research Threads
Assigned via seed-based pattern matching on topic titles, tags, post content, and author identity. Each topic is assigned to its best-matching thread (minimum score threshold: 1.5).

### EIP Mapping
EIP numbers extracted via regex from topic titles and post content (HTML). Primary EIPs are those mentioned in the title or referenced ≥3 times in the opening post. All other mentions are recorded as secondary references.

## Appendix A: Top 100 Topics by Influence

| # | Topic | Author | Date | Score | In° | Likes | Thread |
|---|-------|--------|------|-------|-----|-------|--------|
| 1 | [Minimal Viable Plasma](https://ethresear.ch/t/426) | vbuterin | 2018-01-03 | 0.80 | 11 | 288 | Plasma & L2 Scaling |
| 2 | [On-chain scaling to potentially ~500 tx/sec through mass tx validation](https://ethresear.ch/t/3477) | vbuterin | 2018-09-22 | 0.66 | 20 | 119 | ZK Proofs & SNARKs/STARKs |
| 3 | [Plasma Cash: Plasma with much less per-user data checking](https://ethresear.ch/t/1298) | vbuterin | 2018-03-04 | 0.65 | 19 | 72 | Plasma & L2 Scaling |
| 4 | [MEV burn—a simple design](https://ethresear.ch/t/15590) | JustinDrake | 2023-05-15 | 0.64 | 33 | 69 | PBS, MEV & Block Production |
| 5 | [Based rollups—superpowers from L1 sequencing](https://ethresear.ch/t/15016) | JustinDrake | 2023-03-10 | 0.64 | 24 | 143 | Plasma & L2 Scaling |
| 6 | [Based preconfirmations](https://ethresear.ch/t/17353) | JustinDrake | 2023-11-08 | 0.63 | 29 | 85 | Based Sequencing & Preconfirmations |
| 7 | [Sticking to 8192 signatures per slot post-SSF: how and why](https://ethresear.ch/t/17989) | vbuterin | 2023-12-27 | 0.60 | 9 | 241 | Consensus & Finality |
| 8 | [Explanation of DAICOs](https://ethresear.ch/t/465) | vbuterin | 2018-01-06 | 0.56 | 2 | 185 | — |
| 9 | [Execution Tickets](https://ethresear.ch/t/17944) | mikeneuder | 2023-12-23 | 0.56 | 28 | 51 | PBS, MEV & Block Production |
| 10 | [Sharding phase 1 spec (RETIRED)](https://ethresear.ch/t/1407) | JustinDrake | 2018-03-16 | 0.52 | 11 | 62 | Sharding & Data Availability |
| 11 | [Unbundling staking: Towards rainbow staking](https://ethresear.ch/t/18683) | barnabe | 2024-02-15 | 0.51 | 22 | 57 | Consensus & Finality |
| 12 | [Native rollups—superpowers from L1 execution](https://ethresear.ch/t/21517) | JustinDrake | 2025-01-20 | 0.49 | 4 | 203 | Plasma & L2 Scaling |
| 13 | [The Stateless Client Concept](https://ethresear.ch/t/172) | vbuterin | 2017-10-24 | 0.49 | 18 | 48 | State & Execution Layer |
| 14 | [Increase the MAX_EFFECTIVE_BALANCE – a modest proposal](https://ethresear.ch/t/15801) | mikeneuder | 2023-06-06 | 0.49 | 10 | 86 | Issuance & Staking Economics |
| 15 | [Two-slot proposer/builder separation](https://ethresear.ch/t/10980) | vbuterin | 2021-10-10 | 0.49 | 19 | 28 | PBS, MEV & Block Production |
| 16 | [Proposer/block builder separation-friendly fee market designs](https://ethresear.ch/t/9725) | vbuterin | 2021-06-04 | 0.48 | 10 | 86 | PBS, MEV & Block Production |
| 17 | [Unbundling PBS: Towards protocol-enforced proposer commitments (PEPC)](https://ethresear.ch/t/13879) | barnabe | 2022-10-08 | 0.48 | 19 | 53 | PBS, MEV & Block Production |
| 18 | [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) | soispoke | 2024-06-19 | 0.48 | 19 | 58 | Consensus & Finality |
| 19 | [Why enshrine Proposer-Builder Separation? A viable path to ePBS](https://ethresear.ch/t/15710) | mikeneuder | 2023-05-25 | 0.46 | 14 | 63 | PBS, MEV & Block Production |
| 20 | [RSA Accumulators for Plasma Cash history reduction](https://ethresear.ch/t/3739) | vbuterin | 2018-10-08 | 0.46 | 16 | 42 | Plasma & L2 Scaling |
| 21 | [Minimal anti-collusion infrastructure](https://ethresear.ch/t/5413) | vbuterin | 2019-05-04 | 0.45 | 11 | 66 | Inclusion Lists & Censorship Resistance |
| 22 | [Pragmatic signature aggregation with BLS](https://ethresear.ch/t/2105) | JustinDrake | 2018-05-31 | 0.45 | 10 | 55 | Sharding & Data Availability |
| 23 | [Cross-rollup NFT wrapper and migration ideas](https://ethresear.ch/t/10507) | vbuterin | 2021-09-06 | 0.44 | 1 | 101 | Plasma & L2 Scaling |
| 24 | [DRAFT: Position paper on resource pricing](https://ethresear.ch/t/2838) | vbuterin | 2018-08-07 | 0.44 | 11 | 36 | Fee Markets & EIP-1559 |
| 25 | [A simple and principled way to compute rent fees](https://ethresear.ch/t/1455) | vbuterin | 2018-03-22 | 0.44 | 5 | 67 | Sharding & Data Availability |
| 26 | [Payload-timeliness committee (PTC) – an ePBS design](https://ethresear.ch/t/16054) | mikeneuder | 2023-07-06 | 0.44 | 20 | 27 | PBS, MEV & Block Production |
| 27 | [More Viable Plasma](https://ethresear.ch/t/2160) | kfichter | 2018-06-07 | 0.43 | 8 | 39 | Plasma & L2 Scaling |
| 28 | [How to hard-fork to save most users' funds in a quantum emergency](https://ethresear.ch/t/18901) | vbuterin | 2024-03-09 | 0.43 | 4 | 106 | — |
| 29 | [Plasma snapp - fully verified plasma chain](https://ethresear.ch/t/3391) | josojo | 2018-09-15 | 0.42 | 10 | 41 | Plasma & L2 Scaling |
| 30 | [Unconditional inclusion lists](https://ethresear.ch/t/18500) | mikeneuder | 2024-01-30 | 0.42 | 10 | 69 | Inclusion Lists & Censorship Resistance |
| 31 | [Minimal Viable Merged Consensus](https://ethresear.ch/t/5617) | adlerjohn | 2019-06-15 | 0.42 | 15 | 20 | — |
| 32 | [Properties of issuance level: consensus incentives and variability across potential reward curves](https://ethresear.ch/t/18448) | aelowsson | 2024-01-24 | 0.41 | 12 | 62 | Issuance & Staking Economics |
| 33 | [Faster block/blob propagation in Ethereum](https://ethresear.ch/t/21370) | potuz | 2025-01-03 | 0.41 | 4 | 103 | Sharding & Data Availability |
| 34 | [Dr. changestuff or: how i learned to stop worrying and love mev-burn](https://ethresear.ch/t/17384) | mikeneuder | 2023-11-10 | 0.40 | 12 | 54 | PBS, MEV & Block Production |
| 35 | [PeerDAS -- a simpler DAS approach using battle-tested p2p components](https://ethresear.ch/t/16541) | djrtwo | 2023-09-04 | 0.40 | 13 | 31 | Sharding & Data Availability |
| 36 | [Committee-driven MEV smoothing](https://ethresear.ch/t/10408) | fradamt | 2021-08-23 | 0.39 | 12 | 27 | PBS, MEV & Block Production |
| 37 | [No free lunch – a new inclusion list design](https://ethresear.ch/t/16389) | mikeneuder | 2023-08-15 | 0.39 | 14 | 25 | Inclusion Lists & Censorship Resistance |
| 38 | [Multidimensional EIP 1559](https://ethresear.ch/t/11651) | vbuterin | 2022-01-05 | 0.39 | 3 | 76 | Fee Markets & EIP-1559 |
| 39 | [View-merge as a replacement for proposer boost](https://ethresear.ch/t/13739) | fradamt | 2022-09-21 | 0.39 | 16 | 12 | — |
| 40 | [Optimizing sparse Merkle trees](https://ethresear.ch/t/3751) | vbuterin | 2018-10-09 | 0.39 | 8 | 25 | — |
| 41 | [How much can we constrain builders without bringing back heavy burdens to proposers?](https://ethresear.ch/t/13808) | vbuterin | 2022-10-01 | 0.38 | 9 | 35 | Inclusion Lists & Censorship Resistance |
| 42 | [A signaling theory model of cryptocurrency issuance and value](https://ethresear.ch/t/1081) | vbuterin | 2018-02-14 | 0.38 | 1 | 71 | Issuance & Staking Economics |
| 43 | [2FA zk-rollups using SGX](https://ethresear.ch/t/14462) | JustinDrake | 2022-12-21 | 0.38 | 2 | 100 | ZK Proofs & SNARKs/STARKs |
| 44 | [A local-node-favoring delta to the scaling roadmap](https://ethresear.ch/t/22368) | vbuterin | 2025-05-19 | 0.38 | 2 | 89 | Fee Markets & EIP-1559 |
| 45 | [Orbit SSF: solo-staking-friendly validator set management for SSF](https://ethresear.ch/t/19928) | fradamt | 2024-06-28 | 0.38 | 13 | 29 | Consensus & Finality |
| 46 | [MEV capturing AMM (McAMM)](https://ethresear.ch/t/13336) | josojo | 2022-08-10 | 0.38 | 5 | 59 | PBS, MEV & Block Production |
| 47 | [Plasma XT: Plasma Cash with much less per-user data checking](https://ethresear.ch/t/1926) | kfichter | 2018-05-07 | 0.37 | 7 | 26 | Plasma & L2 Scaling |
| 48 | [Simple Fast Withdrawals](https://ethresear.ch/t/2128) | kfichter | 2018-06-03 | 0.37 | 8 | 24 | Plasma & L2 Scaling |
| 49 | [Alternative proposal for early eth1 <-> eth2 merge](https://ethresear.ch/t/6666) | vbuterin | 2019-12-23 | 0.37 | 5 | 36 | Consensus & Finality |
| 50 | [Whisk: A practical shuffle-based SSLE protocol for Ethereum](https://ethresear.ch/t/11763) | asn | 2022-01-13 | 0.37 | 8 | 32 | — |
| 51 | [Endgame Staking Economics: A Case for Targeting](https://ethresear.ch/t/18751) | casparschwa | 2024-02-22 | 0.37 | 13 | 77 | Issuance & Staking Economics |
| 52 | [Using polynomial commitments to replace state roots](https://ethresear.ch/t/7095) | vbuterin | 2020-03-10 | 0.37 | 9 | 32 | — |
| 53 | [Roll_up / roll_back snark side chain ~17000 tps](https://ethresear.ch/t/3675) | barryWhiteHat | 2018-10-03 | 0.37 | 6 | 47 | ZK Proofs & SNARKs/STARKs |
| 54 | [Latest Casper Basics. Tear it apart](https://ethresear.ch/t/151) | virgil | 2017-10-17 | 0.37 | 0 | 48 | Consensus & Finality |
| 55 | [FullDAS: towards massive scalability with 32MB blocks and beyond](https://ethresear.ch/t/19529) | cskiraly | 2024-05-11 | 0.36 | 15 | 7 | Sharding & Data Availability |
| 56 | [Enshrined Eth2 price feeds](https://ethresear.ch/t/7391) | JustinDrake | 2020-05-11 | 0.36 | 4 | 59 | Consensus & Finality |
| 57 | [Minimal VDF randomness beacon](https://ethresear.ch/t/3566) | JustinDrake | 2018-09-26 | 0.36 | 3 | 47 | — |
| 58 | [Double-batched Merkle log accumulator](https://ethresear.ch/t/571) | JustinDrake | 2018-01-10 | 0.36 | 10 | 22 | State & Execution Layer |
| 59 | [A minimal sharding protocol that may be worthwhile as a development target now](https://ethresear.ch/t/1650) | vbuterin | 2018-04-07 | 0.36 | 7 | 33 | Sharding & Data Availability |
| 60 | [Cross-shard contract yanking](https://ethresear.ch/t/1450) | vbuterin | 2018-03-21 | 0.36 | 12 | 6 | Sharding & Data Availability |
| 61 | [Plasma Debit: Arbitrary-denomination payments in Plasma Cash](https://ethresear.ch/t/2198) | danrobinson | 2018-06-10 | 0.36 | 3 | 36 | Plasma & L2 Scaling |
| 62 | [Supporting decentralized staking through more anti-correlation incentives](https://ethresear.ch/t/19116) | vbuterin | 2024-03-26 | 0.36 | 3 | 84 | — |
| 63 | [Improving front running resistance of x*y=k market makers](https://ethresear.ch/t/1281) | vbuterin | 2018-03-02 | 0.36 | 2 | 52 | — |
| 64 | [Binary trie format](https://ethresear.ch/t/7621) | gballet | 2020-07-01 | 0.36 | 2 | 15 | State & Execution Layer |
| 65 | [The eth1 -> eth2 transition](https://ethresear.ch/t/6265) | vbuterin | 2019-10-10 | 0.36 | 4 | 30 | — |
| 66 | [First and second-price auctions and improved transaction-fee markets](https://ethresear.ch/t/2410) | vbuterin | 2018-07-02 | 0.36 | 3 | 27 | Fee Markets & EIP-1559 |
| 67 | [RANDAO beacon exploitability analysis, round 2](https://ethresear.ch/t/1980) | vbuterin | 2018-05-11 | 0.36 | 11 | 11 | Consensus & Finality |
| 68 | [Pairwise coordination subsidies: a new quadratic funding design](https://ethresear.ch/t/5553) | vbuterin | 2019-06-04 | 0.36 | 3 | 44 | — |
| 69 | [RNG exploitability analysis assuming pure RANDAO-based main chain](https://ethresear.ch/t/1825) | vbuterin | 2018-04-24 | 0.36 | 10 | 6 | Consensus & Finality |
| 70 | [Beacon chain Casper mini-spec](https://ethresear.ch/t/2760) | vbuterin | 2018-07-31 | 0.35 | 7 | 13 | Consensus & Finality |
| 71 | [Proposal: Change Ether currency symbol from Ξ to ⧫](https://ethresear.ch/t/120) | virgil | 2017-10-05 | 0.35 | 0 | 36 | — |
| 72 | [Simplified Active Validator Cap and Rotation Proposal](https://ethresear.ch/t/9022) | vbuterin | 2021-03-27 | 0.35 | 6 | 32 | Consensus & Finality |
| 73 | [Timing Games: Implications and Possible Mitigations](https://ethresear.ch/t/17612) | casparschwa | 2023-12-05 | 0.35 | 14 | 75 | PBS, MEV & Block Production |
| 74 | [ReGenesis - resetting Ethereum to reduce the burden of large blockchain and state](https://ethresear.ch/t/7582) | AlexeyAkhunov | 2020-06-24 | 0.35 | 4 | 48 | — |
| 75 | [Bid cancellations considered harmful](https://ethresear.ch/t/15500) | mikeneuder | 2023-05-05 | 0.35 | 10 | 27 | PBS, MEV & Block Production |
| 76 | [Tradeoffs in Account Abstraction Proposals](https://ethresear.ch/t/263) | vbuterin | 2017-11-28 | 0.35 | 5 | 20 | — |
| 77 | [Concurrent Block Proposers in Ethereum](https://ethresear.ch/t/18777) | mikeneuder | 2024-02-23 | 0.35 | 10 | 17 | — |
| 78 | [On Block Sizes, Gas Limits and Scalability](https://ethresear.ch/t/18444) | Nero_eth | 2024-01-24 | 0.35 | 4 | 48 | Fee Markets & EIP-1559 |
| 79 | [Execution & Consensus Client Bootnodes](https://ethresear.ch/t/14588) | pcaversaccio | 2023-01-10 | 0.34 | 0 | 62 | — |
| 80 | [Analysis on ''Correlated Attestation Penalties''](https://ethresear.ch/t/19244) | Nero_eth | 2024-04-09 | 0.34 | 2 | 50 | Consensus & Finality |
| 81 | [Cross Shard Locking Scheme - (1)](https://ethresear.ch/t/1269) | MaxC | 2018-03-01 | 0.34 | 6 | 13 | Sharding & Data Availability |
| 82 | [Relays in a post-ePBS world](https://ethresear.ch/t/16278) | mikeneuder | 2023-08-04 | 0.34 | 8 | 30 | PBS, MEV & Block Production |
| 83 | [State-minimised executions](https://ethresear.ch/t/748) | JustinDrake | 2018-01-17 | 0.34 | 8 | 5 | State & Execution Layer |
| 84 | [A model for cumulative committee-based finality](https://ethresear.ch/t/10259) | vbuterin | 2021-08-05 | 0.34 | 3 | 34 | Consensus & Finality |
| 85 | [MEV Auction: Auctioning transaction ordering rights as a solution to Miner Extractable Value](https://ethresear.ch/t/6788) | karl | 2020-01-15 | 0.34 | 6 | 92 | PBS, MEV & Block Production |
| 86 | [ERC721 Extension for zk-SNARKs](https://ethresear.ch/t/13237) | Nero_eth | 2022-08-04 | 0.34 | 1 | 47 | ZK Proofs & SNARKs/STARKs |
| 87 | [Why Smart Contracts are NOT feasible on Plasma](https://ethresear.ch/t/2598) | johba | 2018-07-18 | 0.34 | 4 | 41 | Plasma & L2 Scaling |
| 88 | [Uncrowdable Inclusion Lists: The Tension between Chain Neutrality, Preconfirmations and Proposer Commitments](https://ethresear.ch/t/19372) | Julian | 2024-04-25 | 0.33 | 9 | 25 | Plasma & L2 Scaling |
| 89 | [A general framework of overhead and finality time in sharding, and a proposal](https://ethresear.ch/t/1638) | vbuterin | 2018-04-07 | 0.33 | 8 | 15 | Sharding & Data Availability |
| 90 | [Circulating Supply Equilibrium for Ethereum and Minimum Viable Issuance during the Proof-of-Stake Era](https://ethresear.ch/t/10954) | aelowsson | 2021-10-07 | 0.33 | 6 | 17 | Issuance & Staking Economics |
| 91 | [Improving the UX of rent with a sleeping+waking mechanism](https://ethresear.ch/t/1480) | vbuterin | 2018-03-23 | 0.33 | 7 | 15 | — |
| 92 | [Trustless Bitcoin Bridge Creation with Witness Encryption](https://ethresear.ch/t/11953) | leohio | 2022-02-06 | 0.33 | 2 | 38 | Plasma & L2 Scaling |
| 93 | [On Increasing the Block Gas Limit](https://ethresear.ch/t/18567) | Nero_eth | 2024-02-05 | 0.33 | 3 | 48 | Fee Markets & EIP-1559 |
| 94 | [Cross-rollup DEX with smart contracts only on the destination side](https://ethresear.ch/t/8778) | vbuterin | 2021-02-28 | 0.33 | 0 | 37 | Plasma & L2 Scaling |
| 95 | [Against proof of stake for [zk/op]rollup leader election](https://ethresear.ch/t/7698) | barryWhiteHat | 2020-07-17 | 0.33 | 7 | 19 | Plasma & L2 Scaling |
| 96 | [Why you can't build a private uniswap with ZKPs](https://ethresear.ch/t/7754) | barryWhiteHat | 2020-07-24 | 0.33 | 3 | 39 | ZK Proofs & SNARKs/STARKs |
| 97 | [Reward curve with tempered issuance: EIP research post](https://ethresear.ch/t/19171) | aelowsson | 2024-04-01 | 0.33 | 9 | 15 | Issuance & Staking Economics |
| 98 | [Hashgraph Consensus Timing Vulnerability](https://ethresear.ch/t/2120) | kladkogex | 2018-06-02 | 0.33 | 0 | 46 | — |
| 99 | [So you wanna Post-Quantum Ethereum transaction signature](https://ethresear.ch/t/21291) | asanso | 2024-12-18 | 0.33 | 5 | 56 | — |
| 100 | [Prediction markets for content curation DAOs](https://ethresear.ch/t/1312) | vbuterin | 2018-03-06 | 0.33 | 2 | 31 | — |

## Appendix B: Fork Timeline with Topic Cross-References

| Fork | Date | EIPs | Related Topics |
|------|------|------|----------------|
| Byzantium | 2017-10-16 | 100, 140, 196, 197, 198, 211 | [BLS Signatures in Solidity](https://ethresear.ch/t/7919) |
| Constantinople | 2019-02-28 | 145, 1014, 1052, 1234, 1283 | — |
| Istanbul | 2019-12-08 | 152, 1108, 1344, 1884, 2028, 2200 | [BLS Signatures in Solidity](https://ethresear.ch/t/7919); [Ethereum 9¾: Send ERC20 privately using ...](https://ethresear.ch/t/6217) |
| Berlin | 2021-04-15 | 2565, 2929, 2718, 2930 | [Block-Level Warming](https://ethresear.ch/t/21452); [State Lock Auctions: Towards Collaborati...](https://ethresear.ch/t/18558) |
| London | 2021-08-05 | 1559, 3198, 3529, 3541, 3554 | [MEV burn—a simple design](https://ethresear.ch/t/15590); [Native rollups—superpowers from L1 execu...](https://ethresear.ch/t/21517); [Fork-Choice enforced Inclusion Lists (FO...](https://ethresear.ch/t/19870); [Multidimensional EIP 1559](https://ethresear.ch/t/11651); [Endgame Staking Economics: A Case for Ta...](https://ethresear.ch/t/18751) |
| Phase 0 | 2020-12-01 | — | — |
| Altair | 2021-10-27 | — | — |
| The Merge | 2022-09-15 | 3675, 4399 | — |
| Shapella | 2023-04-12 | 3651, 3855, 3860, 4895, 6049 | — |
| Dencun | 2024-03-13 | 1153, 4788, 4844, 5656, 6780, 7044 | [On Block Sizes, Gas Limits and Scalabili...](https://ethresear.ch/t/18444); [On Increasing the Block Gas Limit](https://ethresear.ch/t/18567); [From 4844 to Danksharding: a path to sca...](https://ethresear.ch/t/18046); [Big blocks, blobs, and reorgs](https://ethresear.ch/t/19674); [SubnetDAS - an intermediate DAS approach](https://ethresear.ch/t/17169) |
| Pectra | 2025-05-07 | 2537, 2935, 6110, 7002, 7251, 7549 | [Fork-Choice enforced Inclusion Lists (FO...](https://ethresear.ch/t/19870); [Self-Sovereign Identity and Account Abst...](https://ethresear.ch/t/19599); [ePBS design constraints](https://ethresear.ch/t/18728); [BLS Signatures in Solidity](https://ethresear.ch/t/7919); [The road to Post-Quantum Ethereum transa...](https://ethresear.ch/t/21783) |
| Fusaka | 2025-12-03 | 7594, 7823, 7825, 7883, 7917, 7918 | — |
| Glamsterdam | TBD | 7732, 7928 | [Block-level Access Lists (BALs)](https://ethresear.ch/t/22331); [Payload Chunking](https://ethresear.ch/t/23008) |
