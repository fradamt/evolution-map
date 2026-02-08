# Ethereum Research Evolution Map

*An analysis of 2,903 ethresear.ch topics (2017–2026), tracing how ideas became protocol.*

## 1. Executive Summary

From September 2017 to February 2026, the Ethereum research forum accumulated **2,903 topics** — a living record of how one of the most ambitious distributed systems projects evolved in the open.

This analysis identifies **600 influential topics** connected by **1,197 cross-references**, organized into **10 research threads** across **5 eras**, spanning **17 mainnet forks** from Byzantium (2017) through Fusaka (2025).

### Key Findings

- **The forum's center of gravity shifted dramatically.** Early years (2017–2018) were dominated by sharding and Plasma; by 2023–2026, the discourse had moved to PBS, staking economics, and based rollups — reflecting the pivot from execution sharding to a rollup-centric roadmap.
- **Research-to-deployment lag varies widely.** EIP-1559 was discussed on ethresear.ch as early as 2018 and shipped in London (August 2021) — a 3-year cycle. Proposer-builder separation, first formalized in 2021, has its enshrined version (EIP-7732) targeted for Glamsterdam, still unscheduled as of 2026.
- **A small cohort drives outsized impact.** The top 5 authors by influence (vbuterin, JustinDrake, mikeneuder, Nero_eth, aelowsson) created 213 of the included topics — but the community broadened significantly post-2022.

## 2. The Researchers

The ethresear.ch community evolved from a small group of core researchers into a broader ecosystem. Here are the most influential contributors, measured by topic count, citation impact (in-degree from other topics), and community engagement (likes).

### 1. vbuterin

**Active:** 2017–2025 · **Topics:** 120 · **Likes received:** 3270 · **Cited by:** 542 other topics

**Focus areas:** Sharding (37), Proof-of-Stake (25), Economics (13)

**Research threads:** Consensus & PoS, Data Availability & Sharding, MEV, Block Production & Fees

**Most influential topics:**
- [On-chain scaling to potentially ~500 tx/sec through mass tx validation](https://ethresear.ch/t/3477) (2018, influence: 1.00)
- [Plasma Cash: Plasma with much less per-user data checking](https://ethresear.ch/t/1298) (2018, influence: 1.00)
- [Minimal Viable Plasma](https://ethresear.ch/t/426) (2018, influence: 1.00)
- [Sticking to 8192 signatures per slot post-SSF: how and why](https://ethresear.ch/t/17989) (2023, influence: 0.99)
- [Proposer/block builder separation-friendly fee market designs](https://ethresear.ch/t/9725) (2021, influence: 0.99)

**Frequent collaborators:** kladkogex (32), JustinDrake (19), jamesray1 (14), MicahZoltu (13), dankrad (12)

Vitalik's research presence on ethresear.ch is unmatched — spanning every major thread from Casper and sharding through PBS and SSF. His posts often serve as foundational framings that the community then iterates on. His posting volume peaked during the Scaling Wars era (2018) and surged again in the Endgame Architecture era (2023–2026) as the protocol's endgame design crystallized.

### 2. JustinDrake

**Active:** 2017–2025 · **Topics:** 40 · **Likes received:** 1234 · **Cited by:** 268 other topics

**Focus areas:** Sharding (27), Proof-of-Stake (4), Layer 2 (3)

**Research threads:** Consensus & PoS, Cryptography, Data Availability & Sharding

**Most influential topics:**
- [Based rollups—superpowers from L1 sequencing](https://ethresear.ch/t/15016) (2023, influence: 1.00)
- [Based preconfirmations](https://ethresear.ch/t/17353) (2023, influence: 1.00)
- [MEV burn—a simple design](https://ethresear.ch/t/15590) (2023, influence: 1.00)
- [Increase the MAX_EFFECTIVE_BALANCE – a modest proposal](https://ethresear.ch/t/15801) (2023, influence: 0.99)
- [Why enshrine Proposer-Builder Separation? A viable path to ePBS](https://ethresear.ch/t/15710) (2023, influence: 0.99)

**Frequent collaborators:** vbuterin (24), kladkogex (16), jamesray1 (9), jannikluhn (5), skilesare (5)

Justin Drake emerged as the second most prolific researcher, with deep contributions to sharding, data availability, and more recently based rollups and preconfirmations. His work bridges theoretical proposals and practical protocol design, often co-developing ideas that later become EIPs.

### 3. mikeneuder

**Active:** 2023–2025 · **Topics:** 19 · **Likes received:** 636 · **Cited by:** 174 other topics

**Focus areas:** Proof-of-Stake (17), Uncategorized (1), Economics (1)

**Research threads:** MEV, Block Production & Fees, Consensus & PoS, Data Availability & Sharding

**Most influential topics:**
- [Timing Games: Implications and Possible Mitigations](https://ethresear.ch/t/17612) (2023, influence: 1.00)
- [Increase the MAX_EFFECTIVE_BALANCE – a modest proposal](https://ethresear.ch/t/15801) (2023, influence: 0.99)
- [Why enshrine Proposer-Builder Separation? A viable path to ePBS](https://ethresear.ch/t/15710) (2023, influence: 0.99)
- [Unconditional inclusion lists](https://ethresear.ch/t/18500) (2024, influence: 0.99)
- [Execution Tickets](https://ethresear.ch/t/17944) (2023, influence: 0.99)

**Frequent collaborators:** potuz (6), terence (6), fradamt (5), The-CTra1n (4), Nero_eth (3)

Mike Neuder rose to prominence in the 2023–2025 period as a key voice on PBS, inclusion lists, and censorship resistance — topics that define the post-MEV research agenda. His work on ePBS and FOCIL directly influenced Glamsterdam planning.

### 4. fradamt

**Active:** 2021–2025 · **Topics:** 15 · **Likes received:** 380 · **Cited by:** 132 other topics

**Focus areas:** Proof-of-Stake (5), Consensus (5), Networking (2)

**Research threads:** Consensus & PoS, Data Availability & Sharding, MEV, Block Production & Fees

**Most influential topics:**
- [Increase the MAX_EFFECTIVE_BALANCE – a modest proposal](https://ethresear.ch/t/15801) (2023, influence: 0.99)
- [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) (2024, influence: 0.99)
- [Orbit SSF: solo-staking-friendly validator set management for SSF](https://ethresear.ch/t/19928) (2024, influence: 0.97)
- [Payload-timeliness committee (PTC) – an ePBS design](https://ethresear.ch/t/16054) (2023, influence: 0.97)
- [Committee-driven MEV smoothing](https://ethresear.ch/t/10408) (2021, influence: 0.97)

**Frequent collaborators:** soispoke (2), Kapol (2), djrtwo (2), pop (2), dankrad (2)

### 5. Nero_eth

**Active:** 2022–2025 · **Topics:** 22 · **Likes received:** 475 · **Cited by:** 71 other topics

**Focus areas:** Sharding (5), Execution Layer Research (5), Economics (4)

**Research threads:** MEV, Block Production & Fees, Execution & State, Data Availability & Sharding

**Most influential topics:**
- [On Block Sizes, Gas Limits and Scalability](https://ethresear.ch/t/18444) (2024, influence: 0.96)
- [On Increasing the Block Gas Limit](https://ethresear.ch/t/18567) (2024, influence: 0.95)
- [On Attestations, Block Propagation, and Timing Games](https://ethresear.ch/t/20272) (2024, influence: 0.93)
- [Analysis on ''Correlated Attestation Penalties''](https://ethresear.ch/t/19244) (2024, influence: 0.92)
- [Is it worth using MEV-Boost?](https://ethresear.ch/t/19753) (2024, influence: 0.90)

**Frequent collaborators:** tripoli (6), MicahZoltu (4), kladkogex (4), Evan-Kim2028 (4), kevin-hs-sohn (2)

### 6. barnabe

**Active:** 2020–2025 · **Topics:** 11 · **Likes received:** 338 · **Cited by:** 92 other topics

**Focus areas:** Proof-of-Stake (6), Economics (5)

**Research threads:** Consensus & PoS, MEV, Block Production & Fees, Layer 2 & Rollups

**Most influential topics:**
- [Unbundling staking: Towards rainbow staking](https://ethresear.ch/t/18683) (2024, influence: 0.99)
- [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) (2024, influence: 0.99)
- [Unbundling PBS: Towards protocol-enforced proposer commitments (PEPC)](https://ethresear.ch/t/13879) (2022, influence: 0.99)
- [Decoupling throughput from local building](https://ethresear.ch/t/22004) (2025, influence: 0.97)
- [Uncrowdable Inclusion Lists: The Tension between Chain Neutrality, Preconfirmations and Proposer Commitments](https://ethresear.ch/t/19372) (2024, influence: 0.96)

**Frequent collaborators:** The-CTra1n (3), tkstanczak (2), Evan-Kim2028 (2), soispoke (2), Kapol (2)

### 7. aelowsson

**Active:** 2021–2025 · **Topics:** 12 · **Likes received:** 189 · **Cited by:** 68 other topics

**Focus areas:** Proof-of-Stake (10), Economics (2)

**Research threads:** Consensus & PoS, MEV, Block Production & Fees

**Most influential topics:**
- [Properties of issuance level: consensus incentives and variability across potential reward curves](https://ethresear.ch/t/18448) (2024, influence: 0.99)
- [Practical endgame on issuance policy](https://ethresear.ch/t/20747) (2024, influence: 0.94)
- [Circulating Supply Equilibrium for Ethereum and Minimum Viable Issuance during the Proof-of-Stake Era](https://ethresear.ch/t/10954) (2021, influence: 0.94)
- [Reward curve with tempered issuance: EIP research post](https://ethresear.ch/t/19171) (2024, influence: 0.91)
- [FAQ: Ethereum issuance reduction](https://ethresear.ch/t/19675) (2024, influence: 0.88)

**Frequent collaborators:** pa7x1 (2), vbuterin (1), jcschlegel (1), banr1 (1), Ajesiroo (1)

### 8. soispoke

**Active:** 2023–2025 · **Topics:** 12 · **Likes received:** 218 · **Cited by:** 58 other topics

**Focus areas:** Proof-of-Stake (6), Economics (4), Cryptography (1)

**Research threads:** MEV, Block Production & Fees, Consensus & PoS, Layer 2 & Rollups

**Most influential topics:**
- [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) (2024, influence: 0.99)
- [Uncrowdable Inclusion Lists: The Tension between Chain Neutrality, Preconfirmations and Proposer Commitments](https://ethresear.ch/t/19372) (2024, influence: 0.96)
- [Towards Attester-Includer Separation](https://ethresear.ch/t/21306) (2024, influence: 0.90)
- [The more, the less censored: Introducing committee-enforced inclusion sets (COMIS) on Ethereum](https://ethresear.ch/t/18835) (2024, influence: 0.90)
- [Empirical analysis of Builders' Behavioral Profiles (BBPs)](https://ethresear.ch/t/16327) (2023, influence: 0.89)

**Frequent collaborators:** quintuskilbourn (2), Kapol (2), The-CTra1n (2), SilentCicero (1), Nero_eth (1)

### 9. Julian

**Active:** 2024–2025 · **Topics:** 10 · **Likes received:** 215 · **Cited by:** 48 other topics

**Focus areas:** Proof-of-Stake (6), Economics (2), Uncategorized (1)

**Research threads:** Consensus & PoS, MEV, Block Production & Fees, Data Availability & Sharding

**Most influential topics:**
- [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) (2024, influence: 0.99)
- [Uncrowdable Inclusion Lists: The Tension between Chain Neutrality, Preconfirmations and Proposer Commitments](https://ethresear.ch/t/19372) (2024, influence: 0.96)
- [Initial Analysis of Stake Distribution](https://ethresear.ch/t/19014) (2024, influence: 0.93)
- [Prover Killers Killer: You Build it, You Prove it](https://ethresear.ch/t/22308) (2025, influence: 0.87)
- [A Protocol Design View on Statelessness](https://ethresear.ch/t/22060) (2025, influence: 0.86)

**Frequent collaborators:** terence (2), saguillo2000 (2), mikeneuder (1), leobago (1), Po (1)

### 10. barryWhiteHat

**Active:** 2018–2023 · **Topics:** 12 · **Likes received:** 264 · **Cited by:** 38 other topics

**Focus areas:** Layer 2 (5), zk-s[nt]arks (3), Miscellaneous (2)

**Research threads:** Layer 2 & Rollups, Cryptography, Privacy & Identity

**Most influential topics:**
- [Roll_up / roll_back snark side chain ~17000 tps](https://ethresear.ch/t/3675) (2018, influence: 0.98)
- [Spam resistant block creator selection via burn auction](https://ethresear.ch/t/5851) (2019, influence: 0.95)
- [Why you can't build a private uniswap with ZKPs](https://ethresear.ch/t/7754) (2020, influence: 0.95)
- [Against proof of stake for [zk/op]rollup leader election](https://ethresear.ch/t/7698) (2020, influence: 0.94)
- [Batch Deposits for [op/zk] rollup / mixers / MACI](https://ethresear.ch/t/6883) (2020, influence: 0.91)

**Frequent collaborators:** lsankar4033 (4), adlerjohn (3), kladkogex (3), Mikerah (3), vbuterin (2)

### 11. casparschwa

**Active:** 2021–2024 · **Topics:** 3 · **Likes received:** 163 · **Cited by:** 35 other topics

**Focus areas:** Proof-of-Stake (2), Consensus (1)

**Research threads:** Consensus & PoS, MEV, Block Production & Fees

**Most influential topics:**
- [Timing Games: Implications and Possible Mitigations](https://ethresear.ch/t/17612) (2023, influence: 1.00)
- [Endgame Staking Economics: A Case for Targeting](https://ethresear.ch/t/18751) (2024, influence: 1.00)
- [Change fork choice rule to mitigate balancing and reorging attacks](https://ethresear.ch/t/11127) (2021, influence: 0.87)

**Frequent collaborators:** barnabe (2), MicahZoltu (1), Sotfranc (1), PhABC (1), ileuthwehfoi (1)

### 12. asanso

**Active:** 2021–2025 · **Topics:** 7 · **Likes received:** 186 · **Cited by:** 17 other topics

**Focus areas:** Cryptography (7)

**Research threads:** Cryptography, MEV, Block Production & Fees

**Most influential topics:**
- [So you wanna Post-Quantum Ethereum transaction signature](https://ethresear.ch/t/21291) (2024, influence: 0.98)
- [Falcon as an Ethereum Transaction Signature: The Good, the Bad, and the Gnarly](https://ethresear.ch/t/21512) (2025, influence: 0.92)
- [The road to Post-Quantum Ethereum transaction is paved with Account Abstraction (AA)](https://ethresear.ch/t/21783) (2025, influence: 0.81)
- [Introducing Bandersnatch: a fast elliptic curve built over the BLS12-381 scalar field](https://ethresear.ch/t/9957) (2021, influence: 0.80)
- [Anonymous Inclusion Lists (anon-ILs)](https://ethresear.ch/t/19627) (2024, influence: 0.80)

**Frequent collaborators:** mratsim (3), rdubois-crypto (3), CPerezz (2), seresistvanandras (2), JChanceHud (2)

### 13. adlerjohn

**Active:** 2019–2019 · **Topics:** 7 · **Likes received:** 70 · **Cited by:** 35 other topics

**Focus areas:** Layer 2 (4), Cryptography (1), Sharding (1)

**Research threads:** Cryptography, Consensus & PoS, Data Availability & Sharding

**Most influential topics:**
- [Minimal Viable Merged Consensus](https://ethresear.ch/t/5617) (2019, influence: 0.95)
- [On-Chain Non-Interactive Data Availability Proofs](https://ethresear.ch/t/5715) (2019, influence: 0.90)
- [Open Research Questions For Phases 0 to 2](https://ethresear.ch/t/5871) (2019, influence: 0.74)
- [Compact Fraud Proofs for UTXO Chains Without Intermediate State Serialization](https://ethresear.ch/t/5885) (2019, influence: 0.73)
- [Trustless Two-Way Bridges With Side Chains By Halting](https://ethresear.ch/t/5728) (2019, influence: 0.71)

**Frequent collaborators:** vbuterin (2), DZack (1), matt (1), TimDaub (1), kladkogex (1)

### 14. kfichter

**Active:** 2018–2018 · **Topics:** 5 · **Likes received:** 108 · **Cited by:** 28 other topics

**Focus areas:** Layer 2 (5)

**Research threads:** Layer 2 & Rollups

**Most influential topics:**
- [More Viable Plasma](https://ethresear.ch/t/2160) (2018, influence: 0.98)
- [Plasma XT: Plasma Cash with much less per-user data checking](https://ethresear.ch/t/1926) (2018, influence: 0.96)
- [Simple Fast Withdrawals](https://ethresear.ch/t/2128) (2018, influence: 0.96)
- [Reliable Exits of Withheld In-flight Transactions ("Limbo Exits")](https://ethresear.ch/t/1901) (2018, influence: 0.83)
- [Enabling Fast Withdrawals for Faulty Plasma Chains](https://ethresear.ch/t/2909) (2018, influence: 0.70)

**Frequent collaborators:** vbuterin (2), ldct (2), jdkanani (1), sg (1), bharathrao (1)

### 15. cskiraly

**Active:** 2024–2025 · **Topics:** 6 · **Likes received:** 46 · **Cited by:** 35 other topics

**Focus areas:** Networking (4), Sharding (2)

**Research threads:** Data Availability & Sharding, Execution & State

**Most influential topics:**
- [Improving DAS performance with GossipSub Batch Publishing](https://ethresear.ch/t/21713) (2025, influence: 0.87)
- [FullDAS: towards massive scalability with 32MB blocks and beyond](https://ethresear.ch/t/19529) (2024, influence: 0.78)
- [LossyDAS: Lossy, Incremental, and Diagonal Sampling for Data Availability](https://ethresear.ch/t/18963) (2024, influence: 0.75)
- [Is Data Available in the EL Mempool?](https://ethresear.ch/t/22329) (2025, influence: 0.71)
- [Accelerating blob scaling with FullDASv2 (with getBlobs, mempool encoding, and possibly RLC)](https://ethresear.ch/t/22477) (2025, influence: 0.62)

**Frequent collaborators:** Nashatyrev (2), MarcoPolo (2), Evan-Kim2028 (1), pawanjay176 (1), potuz (1)

---

## 3. Research Threads

Each thread traces a line of inquiry from early proposals through protocol deployment. Topics are connected by explicit cross-references — citations that researchers made when building on or responding to prior work.

## 4. Era Analysis

### Early Research (2017–2017)

*Casper basics, stateless clients, early sharding ideas*

**14 included topics**

**What shipped:**
- **Byzantium** (2017-10-16): EIP-100, EIP-140, EIP-196, EIP-197, EIP-198, EIP-211

**Dominant threads:** Execution & State (7), Data Availability & Sharding (2), Consensus & PoS (2), DeFi & Markets (1), MEV, Block Production & Fees (1)

Ethresear.ch launched in September 2017, just weeks before the Byzantium fork brought BN256 precompiles and REVERT to mainnet. The earliest posts read like a brain dump of everything the research team had been thinking about: Casper FFG fundamentals, early sharding designs, and the first sketches of stateless client architectures. The community was small and the discourse was dense — nearly every post was a technical proposal by a core researcher.

Notably, many ideas from this era took years to mature. The proposer/builder separation concept (implicit in early collation proposals), data availability challenges (raised in the context of sharding), and validator economics (Casper deposit mechanics) all planted seeds that would grow into major research threads over the next decade.

**Top topics:**
1. [The Stateless Client Concept](https://ethresear.ch/t/172) by vbuterin (influence: 0.99)
1. [Tradeoffs in Account Abstraction Proposals](https://ethresear.ch/t/263) by vbuterin (influence: 0.95)
1. [Accumulators, scalability of UTXO blockchains, and data availability](https://ethresear.ch/t/176) by JustinDrake (influence: 0.92)
1. [Token sales and shorting](https://ethresear.ch/t/376) by vbuterin (influence: 0.87)
1. [History, state, and asynchronous accumulators in the stateless model](https://ethresear.ch/t/287) by JustinDrake (influence: 0.84)

### Scaling Wars (2018–2018)

*Plasma, sharding execution, VDFs, Casper FFG/CBC debates*

**155 included topics**

**What shipped:**
- **Constantinople** (2019-02-28): EIP-145, EIP-1014, EIP-1052, EIP-1234, EIP-1283

**Dominant threads:** Layer 2 & Rollups (42), Consensus & PoS (31), Data Availability & Sharding (23), Cryptography (14), Execution & State (12)

2018 was ethresear.ch's most prolific year by topic count, driven by the urgent question: how does Ethereum scale? The Scaling Wars played out across two fronts. On-chain, sharding proposals grew increasingly sophisticated — quadratic sharding gave way to super-quadratic designs, cross-shard communication protocols multiplied, and the first data availability schemes appeared.

Off-chain, Plasma variants proliferated: Minimal Viable Plasma, Plasma Cash, Plasma Debit, Plasma Snapp. VDF research (verifiable delay functions) aimed to solve randomness for validator selection. The Casper FFG vs CBC debate continued, with the community gradually converging on FFG as the practical path.

In retrospect, this era's most lasting contribution was the data availability problem formulation. The recognition that data availability — not execution — was the bottleneck for scaling would reshape the entire roadmap by 2020.

**Top topics:**
1. [On-chain scaling to potentially ~500 tx/sec through mass tx validation](https://ethresear.ch/t/3477) by vbuterin (influence: 1.00)
1. [Plasma Cash: Plasma with much less per-user data checking](https://ethresear.ch/t/1298) by vbuterin (influence: 1.00)
1. [Minimal Viable Plasma](https://ethresear.ch/t/426) by vbuterin (influence: 1.00)
1. [Sharding phase 1 spec (RETIRED)](https://ethresear.ch/t/1407) by JustinDrake (influence: 0.99)
1. [Pragmatic signature aggregation with BLS](https://ethresear.ch/t/2105) by JustinDrake (influence: 0.98)

### Eth2 Design (2019–2020)

*Phase 0/1 specs, rollup emergence, beacon chain launch*

**137 included topics**

**What shipped:**
- **Istanbul** (2019-12-08): EIP-152, EIP-1108, EIP-1344, EIP-1884, EIP-2028, EIP-2200
- **Phase 0** (2020-12-01): beacon chain genesis

**Dominant threads:** Consensus & PoS (28), Cryptography (25), Data Availability & Sharding (20), Layer 2 & Rollups (16), Execution & State (15)

The Eth2 Design era (2019–2020) saw the research community transition from exploration to specification. The beacon chain spec (Phase 0) was finalized and launched in December 2020, marking the first time ethresear.ch research shipped as production code. Phase 1 (data sharding) spec work continued, though it would later be superseded by Danksharding.

Two pivotal shifts happened in this era. First, the rollup-centric roadmap emerged: Vitalik's October 2020 analysis of "eth2 as data availability engine" signaled that execution sharding was being deprioritized in favor of rollups as the primary scaling mechanism. Second, MEV awareness grew as Flashbots documented the scale of miner extractable value, setting the stage for the PBS research thread.

**Top topics:**
1. [Minimal anti-collusion infrastructure](https://ethresear.ch/t/5413) by vbuterin (influence: 0.99)
1. [MEV Auction: Auctioning transaction ordering rights as a solution to Miner Extractable Value](https://ethresear.ch/t/6788) by karl (influence: 0.98)
1. [Using polynomial commitments to replace state roots](https://ethresear.ch/t/7095) by vbuterin (influence: 0.97)
1. [Enshrined Eth2 price feeds](https://ethresear.ch/t/7391) by JustinDrake (influence: 0.97)
1. [Alternative proposal for early eth1 <-> eth2 merge](https://ethresear.ch/t/6666) by vbuterin (influence: 0.96)

### Post-Merge Build (2021–2022)

*PBS, EIP-1559, PoW→PoS transition, MEV awareness*

**69 included topics**

**What shipped:**
- **Berlin** (2021-04-15): EIP-2565, EIP-2929, EIP-2718, EIP-2930
- **London** (2021-08-05): EIP-1559, EIP-3198, EIP-3529, EIP-3541, EIP-3554
- **Altair** (2021-10-27): beacon chain genesis
- **The Merge** (2022-09-15): EIP-3675, EIP-4399

**Dominant threads:** MEV, Block Production & Fees (20), Consensus & PoS (19), Cryptography (9), Execution & State (7), Layer 2 & Rollups (6)

The 2021–2022 era was bookended by two landmark deployments: EIP-1559 in London (August 2021) and the Merge itself (September 2022). Research during this period focused on making these transitions safe while laying groundwork for the next phase.

PBS emerged as a major research thread, driven by the MEV crisis. The proposer/builder separation went from theoretical concept to externalized implementation (MEV-Boost) to active enshrined design (ePBS). Fee market research continued with analysis of EIP-1559's behavior in practice and early multidimensional gas proposals. The withdrawal mechanism (EIP-4895) was designed for Shapella, completing the Merge's economic loop.

**Top topics:**
1. [Proposer/block builder separation-friendly fee market designs](https://ethresear.ch/t/9725) by vbuterin (influence: 0.99)
1. [Unbundling PBS: Towards protocol-enforced proposer commitments (PEPC)](https://ethresear.ch/t/13879) by barnabe (influence: 0.99)
1. [MEV-Boost: Merge ready Flashbots Architecture](https://ethresear.ch/t/11177) by thegostep (influence: 0.98)
1. [MEV capturing AMM (McAMM)](https://ethresear.ch/t/13336) by josojo (influence: 0.98)
1. [Shutterized Beacon Chain](https://ethresear.ch/t/12249) by cducrest (influence: 0.98)

### Endgame Architecture (2023–2026)

*ePBS, SSF, based rollups, blobs, PeerDAS, staking economics*

**225 included topics**

**What shipped:**
- **Shapella** (2023-04-12): EIP-3651, EIP-3855, EIP-3860, EIP-4895, EIP-6049
- **Dencun** (2024-03-13): EIP-1153, EIP-4788, EIP-4844, EIP-5656, EIP-6780, EIP-7044
- **Pectra** (2025-05-07): EIP-2537, EIP-2935, EIP-6110, EIP-7002, EIP-7251, EIP-7549
- **Fusaka** (2025-12-03): EIP-7594, EIP-7823, EIP-7825, EIP-7883, EIP-7917, EIP-7918
- **Glamsterdam** (TBD): EIP-7732, EIP-7928

**Dominant threads:** MEV, Block Production & Fees (72), Consensus & PoS (40), Layer 2 & Rollups (36), Data Availability & Sharding (27), Execution & State (23)

The Endgame Architecture era (2023–2026) is defined by protocol maturity. With the Merge complete and blobs live (Dencun, March 2024), research shifted to the "endgame" questions: what does Ethereum look like at steady state?

This era produced the highest topic count, driven by multiple concurrent research frontiers. Staking economics received rigorous treatment (minimum viable issuance, staking ratio targeting). PBS evolved toward ePBS with detailed mechanism design for payload timeliness committees. Inclusion lists and censorship resistance moved from theoretical to concrete (FOCIL, EIP-7805). SSF proposals matured with Orbit SSF. Based rollups and preconfirmations opened a new design space for L1/L2 integration.

Pectra (May 2025) shipped MaxEB (EIP-7251) and in-protocol deposits (EIP-6110), directly influenced by staking economics research. Fusaka (December 2025) delivered PeerDAS (EIP-7594), the first data availability sampling deployment. Glamsterdam, still unscheduled, targets ePBS (EIP-7732) and FOCIL (EIP-7805) — ideas that have been on ethresear.ch for years.

**Top topics:**
1. [Based rollups—superpowers from L1 sequencing](https://ethresear.ch/t/15016) by JustinDrake (influence: 1.00)
1. [Based preconfirmations](https://ethresear.ch/t/17353) by JustinDrake (influence: 1.00)
1. [MEV burn—a simple design](https://ethresear.ch/t/15590) by JustinDrake (influence: 1.00)
1. [Timing Games: Implications and Possible Mitigations](https://ethresear.ch/t/17612) by casparschwa (influence: 1.00)
1. [Endgame Staking Economics: A Case for Targeting](https://ethresear.ch/t/18751) by casparschwa (influence: 1.00)

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
- **Tier 1**: influence ≥ 0.25 or in-degree ≥ 3 (600 topics after adjustment)
- **Tier 2**: referenced by a Tier 1 topic with influence ≥ 0.10
- Final set: **600 topics** from 2,903 total

### Cross-References
Extracted from `post_stream.posts[].link_counts[]` where `internal=true`. Total: 2,620 edges, 1,197 after filtering to included topics.

### Research Threads
Assigned via seed-based pattern matching on topic titles, tags, post content, and author identity. Each topic is assigned to its best-matching thread (minimum score threshold: 1.5).

### EIP Mapping
EIP numbers extracted via regex from topic titles and post content (HTML). Primary EIPs are those mentioned in the title or referenced ≥3 times in the opening post. All other mentions are recorded as secondary references.

## Appendix A: Top 100 Topics by Influence

| # | Topic | Author | Date | Score | In° | Likes | Thread |
|---|-------|--------|------|-------|-----|-------|--------|
| 1 | [Based rollups—superpowers from L1 sequencing](https://ethresear.ch/t/15016) | JustinDrake | 2023-03-10 | 1.00 | 24 | 143 | Layer 2 & Rollups |
| 2 | [On-chain scaling to potentially ~500 tx/sec through mass tx validation](https://ethresear.ch/t/3477) | vbuterin | 2018-09-22 | 1.00 | 20 | 119 | Cryptography |
| 3 | [Based preconfirmations](https://ethresear.ch/t/17353) | JustinDrake | 2023-11-08 | 1.00 | 29 | 85 | Layer 2 & Rollups |
| 4 | [Plasma Cash: Plasma with much less per-user data checking](https://ethresear.ch/t/1298) | vbuterin | 2018-03-04 | 1.00 | 19 | 72 | Layer 2 & Rollups |
| 5 | [MEV burn—a simple design](https://ethresear.ch/t/15590) | JustinDrake | 2023-05-15 | 1.00 | 33 | 69 | MEV, Block Production & Fees |
| 6 | [Minimal Viable Plasma](https://ethresear.ch/t/426) | vbuterin | 2018-01-03 | 1.00 | 11 | 288 | Layer 2 & Rollups |
| 7 | [Timing Games: Implications and Possible Mitigations](https://ethresear.ch/t/17612) | casparschwa | 2023-12-05 | 1.00 | 14 | 75 | MEV, Block Production & Fees |
| 8 | [Endgame Staking Economics: A Case for Targeting](https://ethresear.ch/t/18751) | casparschwa | 2024-02-22 | 1.00 | 13 | 77 | Consensus & PoS |
| 9 | [Sticking to 8192 signatures per slot post-SSF: how and why](https://ethresear.ch/t/17989) | vbuterin | 2023-12-27 | 0.99 | 9 | 241 | Consensus & PoS |
| 10 | [Increase the MAX_EFFECTIVE_BALANCE – a modest proposal](https://ethresear.ch/t/15801) | mikeneuder | 2023-06-06 | 0.99 | 10 | 86 | Consensus & PoS |
| 11 | [Proposer/block builder separation-friendly fee market designs](https://ethresear.ch/t/9725) | vbuterin | 2021-06-04 | 0.99 | 10 | 86 | MEV, Block Production & Fees |
| 12 | [Why enshrine Proposer-Builder Separation? A viable path to ePBS](https://ethresear.ch/t/15710) | mikeneuder | 2023-05-25 | 0.99 | 14 | 63 | MEV, Block Production & Fees |
| 13 | [Unbundling staking: Towards rainbow staking](https://ethresear.ch/t/18683) | barnabe | 2024-02-15 | 0.99 | 22 | 57 | Consensus & PoS |
| 14 | [Fork-Choice enforced Inclusion Lists (FOCIL): A simple committee-based inclusion list proposal](https://ethresear.ch/t/19870) | soispoke | 2024-06-19 | 0.99 | 19 | 58 | Consensus & PoS |
| 15 | [Sharding phase 1 spec (RETIRED)](https://ethresear.ch/t/1407) | JustinDrake | 2018-03-16 | 0.99 | 11 | 62 | Data Availability & Sharding |
| 16 | [Minimal anti-collusion infrastructure](https://ethresear.ch/t/5413) | vbuterin | 2019-05-04 | 0.99 | 11 | 66 | Governance & Standards |
| 17 | [Properties of issuance level: consensus incentives and variability across potential reward curves](https://ethresear.ch/t/18448) | aelowsson | 2024-01-24 | 0.99 | 12 | 62 | Consensus & PoS |
| 18 | [Unconditional inclusion lists](https://ethresear.ch/t/18500) | mikeneuder | 2024-01-30 | 0.99 | 10 | 69 | MEV, Block Production & Fees |
| 19 | [Execution Tickets](https://ethresear.ch/t/17944) | mikeneuder | 2023-12-23 | 0.99 | 28 | 51 | MEV, Block Production & Fees |
| 20 | [Unbundling PBS: Towards protocol-enforced proposer commitments (PEPC)](https://ethresear.ch/t/13879) | barnabe | 2022-10-08 | 0.99 | 19 | 53 | MEV, Block Production & Fees |
| 21 | [The Stateless Client Concept](https://ethresear.ch/t/172) | vbuterin | 2017-10-24 | 0.99 | 18 | 48 | Execution & State |
| 22 | [Dr. changestuff or: how i learned to stop worrying and love mev-burn](https://ethresear.ch/t/17384) | mikeneuder | 2023-11-10 | 0.99 | 12 | 54 | MEV, Block Production & Fees |
| 23 | [Pragmatic signature aggregation with BLS](https://ethresear.ch/t/2105) | JustinDrake | 2018-05-31 | 0.98 | 10 | 55 | Cryptography |
| 24 | [MEV Auction: Auctioning transaction ordering rights as a solution to Miner Extractable Value](https://ethresear.ch/t/6788) | karl | 2020-01-15 | 0.98 | 6 | 92 | MEV, Block Production & Fees |
| 25 | [RSA Accumulators for Plasma Cash history reduction](https://ethresear.ch/t/3739) | vbuterin | 2018-10-08 | 0.98 | 16 | 42 | Layer 2 & Rollups |
| 26 | [Plasma snapp - fully verified plasma chain](https://ethresear.ch/t/3391) | josojo | 2018-09-15 | 0.98 | 10 | 41 | Layer 2 & Rollups |
| 27 | [MEV-Boost: Merge ready Flashbots Architecture](https://ethresear.ch/t/11177) | thegostep | 2021-11-04 | 0.98 | 7 | 53 | MEV, Block Production & Fees |
| 28 | [DRAFT: Position paper on resource pricing](https://ethresear.ch/t/2838) | vbuterin | 2018-08-07 | 0.98 | 11 | 36 | MEV, Block Production & Fees |
| 29 | [A simple and principled way to compute rent fees](https://ethresear.ch/t/1455) | vbuterin | 2018-03-22 | 0.98 | 5 | 67 | Consensus & PoS |
| 30 | [More Viable Plasma](https://ethresear.ch/t/2160) | kfichter | 2018-06-07 | 0.98 | 8 | 39 | Layer 2 & Rollups |
| 31 | [MEV capturing AMM (McAMM)](https://ethresear.ch/t/13336) | josojo | 2022-08-10 | 0.98 | 5 | 59 | MEV, Block Production & Fees |
| 32 | [Shutterized Beacon Chain](https://ethresear.ch/t/12249) | cducrest | 2022-03-24 | 0.98 | 6 | 47 | Consensus & PoS |
| 33 | [How much can we constrain builders without bringing back heavy burdens to proposers?](https://ethresear.ch/t/13808) | vbuterin | 2022-10-01 | 0.98 | 9 | 35 | MEV, Block Production & Fees |
| 34 | [Roll_up / roll_back snark side chain ~17000 tps](https://ethresear.ch/t/3675) | barryWhiteHat | 2018-10-03 | 0.98 | 6 | 47 | Cryptography |
| 35 | [Two-slot proposer/builder separation](https://ethresear.ch/t/10980) | vbuterin | 2021-10-10 | 0.98 | 19 | 28 | MEV, Block Production & Fees |
| 36 | [Native rollups—superpowers from L1 execution](https://ethresear.ch/t/21517) | JustinDrake | 2025-01-20 | 0.98 | 4 | 203 | Layer 2 & Rollups |
| 37 | [So you wanna Post-Quantum Ethereum transaction signature](https://ethresear.ch/t/21291) | asanso | 2024-12-18 | 0.98 | 5 | 56 | Cryptography |
| 38 | [How to hard-fork to save most users' funds in a quantum emergency](https://ethresear.ch/t/18901) | vbuterin | 2024-03-09 | 0.97 | 4 | 106 | Execution & State |
| 39 | [PeerDAS -- a simpler DAS approach using battle-tested p2p components](https://ethresear.ch/t/16541) | djrtwo | 2023-09-04 | 0.97 | 13 | 31 | Data Availability & Sharding |
| 40 | [Faster block/blob propagation in Ethereum](https://ethresear.ch/t/21370) | potuz | 2025-01-03 | 0.97 | 4 | 103 | Data Availability & Sharding |
| 41 | [Burning MEV through block proposer auctions](https://ethresear.ch/t/14029) | domothy | 2022-10-26 | 0.97 | 7 | 38 | MEV, Block Production & Fees |
| 42 | [Whisk: A practical shuffle-based SSLE protocol for Ethereum](https://ethresear.ch/t/11763) | asn | 2022-01-13 | 0.97 | 8 | 32 | Consensus & PoS |
| 43 | [Using polynomial commitments to replace state roots](https://ethresear.ch/t/7095) | vbuterin | 2020-03-10 | 0.97 | 9 | 32 | Cryptography |
| 44 | [Incentives for running full Ethereum nodes](https://ethresear.ch/t/1239) | jpitts | 2018-02-27 | 0.97 | 4 | 68 | — |
| 45 | [Decoupling throughput from local building](https://ethresear.ch/t/22004) | barnabe | 2025-03-25 | 0.97 | 5 | 49 | — |
| 46 | [A minimal sharding protocol that may be worthwhile as a development target now](https://ethresear.ch/t/1650) | vbuterin | 2018-04-07 | 0.97 | 7 | 33 | Data Availability & Sharding |
| 47 | [Ethereum Privacy: The Road to Self-Sovereignty](https://ethresear.ch/t/22115) | pcaversaccio | 2025-04-09 | 0.97 | 4 | 64 | Privacy & Identity |
| 48 | [Enshrined Eth2 price feeds](https://ethresear.ch/t/7391) | JustinDrake | 2020-05-11 | 0.97 | 4 | 59 | Consensus & PoS |
| 49 | [Orbit SSF: solo-staking-friendly validator set management for SSF](https://ethresear.ch/t/19928) | fradamt | 2024-06-28 | 0.97 | 13 | 29 | Consensus & PoS |
| 50 | [Payload-timeliness committee (PTC) – an ePBS design](https://ethresear.ch/t/16054) | mikeneuder | 2023-07-06 | 0.97 | 20 | 27 | MEV, Block Production & Fees |
| 51 | [Committee-driven MEV smoothing](https://ethresear.ch/t/10408) | fradamt | 2021-08-23 | 0.97 | 12 | 27 | MEV, Block Production & Fees |
| 52 | [Relays in a post-ePBS world](https://ethresear.ch/t/16278) | mikeneuder | 2023-08-04 | 0.97 | 8 | 30 | MEV, Block Production & Fees |
| 53 | [Simplified Active Validator Cap and Rotation Proposal](https://ethresear.ch/t/9022) | vbuterin | 2021-03-27 | 0.96 | 6 | 32 | Consensus & PoS |
| 54 | [Alternative proposal for early eth1 <-> eth2 merge](https://ethresear.ch/t/6666) | vbuterin | 2019-12-23 | 0.96 | 5 | 36 | Consensus & PoS |
| 55 | [ReGenesis - resetting Ethereum to reduce the burden of large blockchain and state](https://ethresear.ch/t/7582) | AlexeyAkhunov | 2020-06-24 | 0.96 | 4 | 48 | Execution & State |
| 56 | [No free lunch – a new inclusion list design](https://ethresear.ch/t/16389) | mikeneuder | 2023-08-15 | 0.96 | 14 | 25 | MEV, Block Production & Fees |
| 57 | [On Block Sizes, Gas Limits and Scalability](https://ethresear.ch/t/18444) | Nero_eth | 2024-01-24 | 0.96 | 4 | 48 | MEV, Block Production & Fees |
| 58 | [Bid cancellations considered harmful](https://ethresear.ch/t/15500) | mikeneuder | 2023-05-05 | 0.96 | 10 | 27 | MEV, Block Production & Fees |
| 59 | [Optimizing sparse Merkle trees](https://ethresear.ch/t/3751) | vbuterin | 2018-10-09 | 0.96 | 8 | 25 | Execution & State |
| 60 | [From 4844 to Danksharding: a path to scaling Ethereum DA](https://ethresear.ch/t/18046) | fradamt | 2023-12-28 | 0.96 | 5 | 36 | Data Availability & Sharding |
| 61 | [Plasma XT: Plasma Cash with much less per-user data checking](https://ethresear.ch/t/1926) | kfichter | 2018-05-07 | 0.96 | 7 | 26 | Layer 2 & Rollups |
| 62 | [Simple Fast Withdrawals](https://ethresear.ch/t/2128) | kfichter | 2018-06-03 | 0.96 | 8 | 24 | Layer 2 & Rollups |
| 63 | [MEV-resistant ZK-Rollups with Practical VDE (PVDE)](https://ethresear.ch/t/12677) | zeroknight | 2022-05-20 | 0.96 | 4 | 41 | MEV, Block Production & Fees |
| 64 | [Why Smart Contracts are NOT feasible on Plasma](https://ethresear.ch/t/2598) | johba | 2018-07-18 | 0.96 | 4 | 41 | Layer 2 & Rollups |
| 65 | [Uncrowdable Inclusion Lists: The Tension between Chain Neutrality, Preconfirmations and Proposer Commitments](https://ethresear.ch/t/19372) | Julian | 2024-04-25 | 0.96 | 9 | 25 | Layer 2 & Rollups |
| 66 | [Supporting decentralized staking through more anti-correlation incentives](https://ethresear.ch/t/19116) | vbuterin | 2024-03-26 | 0.96 | 3 | 84 | Consensus & PoS |
| 67 | [Multidimensional EIP 1559](https://ethresear.ch/t/11651) | vbuterin | 2022-01-05 | 0.95 | 3 | 76 | MEV, Block Production & Fees |
| 68 | [Fast (and Slow) L2→L1 Withdrawals](https://ethresear.ch/t/21161) | The-CTra1n | 2024-12-05 | 0.95 | 5 | 33 | Layer 2 & Rollups |
| 69 | [Double-batched Merkle log accumulator](https://ethresear.ch/t/571) | JustinDrake | 2018-01-10 | 0.95 | 10 | 22 | Execution & State |
| 70 | [Plasma EVM 2.0: state-enforceable construction](https://ethresear.ch/t/3025) | 4000D | 2018-08-21 | 0.95 | 5 | 29 | Layer 2 & Rollups |
| 71 | [Minimal Viable Merged Consensus](https://ethresear.ch/t/5617) | adlerjohn | 2019-06-15 | 0.95 | 15 | 20 | Consensus & PoS |
| 72 | [Self-Sovereign Identity and Account Abstraction for Privacy-Preserving cross chain user operations across roll ups](https://ethresear.ch/t/19599) | EugeRe | 2024-05-20 | 0.95 | 6 | 26 | Execution & State |
| 73 | [The eth1 -> eth2 transition](https://ethresear.ch/t/6265) | vbuterin | 2019-10-10 | 0.95 | 4 | 30 | Consensus & PoS |
| 74 | [Spam resistant block creator selection via burn auction](https://ethresear.ch/t/5851) | barryWhiteHat | 2019-07-21 | 0.95 | 5 | 26 | Consensus & PoS |
| 75 | [Minimal VDF randomness beacon](https://ethresear.ch/t/3566) | JustinDrake | 2018-09-26 | 0.95 | 3 | 47 | Consensus & PoS |
| 76 | [On Increasing the Block Gas Limit](https://ethresear.ch/t/18567) | Nero_eth | 2024-02-05 | 0.95 | 3 | 48 | MEV, Block Production & Fees |
| 77 | [Pairwise coordination subsidies: a new quadratic funding design](https://ethresear.ch/t/5553) | vbuterin | 2019-06-04 | 0.95 | 3 | 44 | Governance & Standards |
| 78 | [Strawmanning Based Preconfirmations](https://ethresear.ch/t/19695) | linoscope | 2024-05-31 | 0.95 | 4 | 31 | Layer 2 & Rollups |
| 79 | [Tradeoffs in Account Abstraction Proposals](https://ethresear.ch/t/263) | vbuterin | 2017-11-28 | 0.95 | 5 | 20 | Execution & State |
| 80 | [Why you can't build a private uniswap with ZKPs](https://ethresear.ch/t/7754) | barryWhiteHat | 2020-07-24 | 0.95 | 3 | 39 | Cryptography |
| 81 | [Plasma Debit: Arbitrary-denomination payments in Plasma Cash](https://ethresear.ch/t/2198) | danrobinson | 2018-06-10 | 0.95 | 3 | 36 | Layer 2 & Rollups |
| 82 | [0x03 Withdrawal Credentials: Simple Eth1-triggerable withdrawals](https://ethresear.ch/t/10021) | gakonst | 2021-07-07 | 0.94 | 3 | 39 | Consensus & PoS |
| 83 | [State Provider Models in Ethereum 2.0](https://ethresear.ch/t/6750) | adietrichs | 2020-01-09 | 0.94 | 5 | 24 | Consensus & PoS |
| 84 | [Exploring the proposer/collator split](https://ethresear.ch/t/1632) | benjaminion | 2018-04-06 | 0.94 | 5 | 21 | Data Availability & Sharding |
| 85 | [Practical endgame on issuance policy](https://ethresear.ch/t/20747) | aelowsson | 2024-10-23 | 0.94 | 5 | 23 | Consensus & PoS |
| 86 | [A nearly-trivial-on-zero-inputs 32-bytes-long collision-resistant hash function](https://ethresear.ch/t/5511) | vbuterin | 2019-05-25 | 0.94 | 4 | 24 | Cryptography |
| 87 | [Against proof of stake for [zk/op]rollup leader election](https://ethresear.ch/t/7698) | barryWhiteHat | 2020-07-17 | 0.94 | 7 | 19 | Layer 2 & Rollups |
| 88 | [A model for cumulative committee-based finality](https://ethresear.ch/t/10259) | vbuterin | 2021-08-05 | 0.94 | 3 | 34 | Consensus & PoS |
| 89 | [Packetology: Validator Privacy](https://ethresear.ch/t/7547) | jrhea | 2020-06-16 | 0.94 | 4 | 26 | Privacy & Identity |
| 90 | [ePBS design constraints](https://ethresear.ch/t/18728) | potuz | 2024-02-20 | 0.94 | 6 | 22 | MEV, Block Production & Fees |
| 91 | [Concurrent Block Proposers in Ethereum](https://ethresear.ch/t/18777) | mikeneuder | 2024-02-23 | 0.94 | 10 | 17 | Consensus & PoS |
| 92 | [Ethereum 2.0 Data Model: Actors and Assets](https://ethresear.ch/t/4117) | fubuloubu | 2018-11-04 | 0.94 | 3 | 30 | — |
| 93 | [Circulating Supply Equilibrium for Ethereum and Minimum Viable Issuance during the Proof-of-Stake Era](https://ethresear.ch/t/10954) | aelowsson | 2021-10-07 | 0.94 | 6 | 17 | Consensus & PoS |
| 94 | [First and second-price auctions and improved transaction-fee markets](https://ethresear.ch/t/2410) | vbuterin | 2018-07-02 | 0.94 | 3 | 27 | MEV, Block Production & Fees |
| 95 | [Block Arrivals, Home Stakers & Bumping the blob count](https://ethresear.ch/t/21096) | samcm | 2024-11-27 | 0.94 | 3 | 34 | Data Availability & Sharding |
| 96 | [Log(coins)-sized proofs of inclusion and exclusion for RSA accumulators](https://ethresear.ch/t/3839) | vbuterin | 2018-10-17 | 0.94 | 7 | 17 | Cryptography |
| 97 | [Liquid solo validating](https://ethresear.ch/t/12779) | JustinDrake | 2022-06-03 | 0.93 | 3 | 31 | Consensus & PoS |
| 98 | [Explanation of DAICOs](https://ethresear.ch/t/465) | vbuterin | 2018-01-06 | 0.93 | 2 | 185 | Governance & Standards |
| 99 | [2FA zk-rollups using SGX](https://ethresear.ch/t/14462) | JustinDrake | 2022-12-21 | 0.93 | 2 | 100 | Cryptography |
| 100 | [A local-node-favoring delta to the scaling roadmap](https://ethresear.ch/t/22368) | vbuterin | 2025-05-19 | 0.93 | 2 | 89 | MEV, Block Production & Fees |

## Appendix B: Fork Timeline with Topic Cross-References

| Fork | Date | EIPs | Related Topics |
|------|------|------|----------------|
| Genesis | 2015-07-30 | — | — |
| Homestead | 2016-03-14 | 2, 7, 8 | — |
| DAO Fork | 2016-07-20 | — | — |
| Tangerine Whistle | 2016-10-18 | 150 | [A ZK-EVM specification - Part 2](https://ethresear.ch/t/13903) |
| Spurious Dragon | 2016-11-22 | 155, 160, 161, 170 | — |
| Byzantium | 2017-10-16 | 100, 140, 196, 197, 198, 211 | [BLS Signatures in Solidity](https://ethresear.ch/t/7919); [A minimum-viable KZG polynomial commitme...](https://ethresear.ch/t/7675) |
| Constantinople | 2019-02-28 | 145, 1014, 1052, 1234, 1283 | — |
| Istanbul | 2019-12-08 | 152, 1108, 1344, 1884, 2028, 2200 | [BLS Signatures in Solidity](https://ethresear.ch/t/7919) |
| Berlin | 2021-04-15 | 2565, 2929, 2718, 2930 | [Block-Level Warming](https://ethresear.ch/t/21452); [State Lock Auctions: Towards Collaborati...](https://ethresear.ch/t/18558); [Delayed Execution and Free DA](https://ethresear.ch/t/22265) |
| London | 2021-08-05 | 1559, 3198, 3529, 3541, 3554 | [MEV burn—a simple design](https://ethresear.ch/t/15590); [Endgame Staking Economics: A Case for Ta...](https://ethresear.ch/t/18751); [Fork-Choice enforced Inclusion Lists (FO...](https://ethresear.ch/t/19870); [Native rollups—superpowers from L1 execu...](https://ethresear.ch/t/21517); [On Block Sizes, Gas Limits and Scalabili...](https://ethresear.ch/t/18444) |
| Phase 0 | 2020-12-01 | — | — |
| Altair | 2021-10-27 | — | — |
| The Merge | 2022-09-15 | 3675, 4399 | — |
| Shapella | 2023-04-12 | 3651, 3855, 3860, 4895, 6049 | — |
| Dencun | 2024-03-13 | 1153, 4788, 4844, 5656, 6780, 7044 | [On Block Sizes, Gas Limits and Scalabili...](https://ethresear.ch/t/18444); [From 4844 to Danksharding: a path to sca...](https://ethresear.ch/t/18046); [On Increasing the Block Gas Limit](https://ethresear.ch/t/18567); [EIP-4844 Fee Market Analysis](https://ethresear.ch/t/15078); [Big blocks, blobs, and reorgs](https://ethresear.ch/t/19674) |
| Pectra | 2025-05-07 | 2537, 2935, 6110, 7002, 7251, 7549 | [Fork-Choice enforced Inclusion Lists (FO...](https://ethresear.ch/t/19870); [Self-Sovereign Identity and Account Abst...](https://ethresear.ch/t/19599); [ePBS design constraints](https://ethresear.ch/t/18728); [Block Arrivals, Home Stakers & Bumping t...](https://ethresear.ch/t/21096); [BLS Signatures in Solidity](https://ethresear.ch/t/7919) |
| Fusaka | 2025-12-03 | 7594, 7823, 7825, 7883, 7917, 7918 | [Improving column propagation with cell-c...](https://ethresear.ch/t/22298) |
| Glamsterdam | TBD | 7732, 7928 | [Block-level Access Lists (BALs)](https://ethresear.ch/t/22331); [Payload Chunking](https://ethresear.ch/t/23008); [An Ethereum Prover Market Proposal](https://ethresear.ch/t/22834) |
