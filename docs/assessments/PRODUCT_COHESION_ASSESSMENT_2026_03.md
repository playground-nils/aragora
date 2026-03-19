# Product Cohesion Assessment — March 2026

> **Purpose:** Ground-truth assessment of Aragora's product cohesion, usability, and PMF readiness.
> This document distinguishes what works end-to-end from what exists as isolated infrastructure.
> **Assessment date:** March 18, 2026
> **Method:** Deep codebase exploration of all user-facing paths, provider integrations, frontend pages, and cross-system wiring.

---

## Executive Summary

Aragora has massive infrastructure depth (210k+ tests, 3,800+ modules, 420+ RBAC permissions) but the **product loop is broken**. No complete user journey exists from sign-up through value delivery. The effective feature completeness for actual product use is **~25%** despite the codebase containing scaffolding for 220+ features.

**Key finding:** The system is an impressive sandbox with a broken product loop. Infrastructure is 90%+ built; the product surface is ~8% functional.

---

## Assessment Framework

Each capability is rated on a 4-level maturity scale:

| Level | Definition |
|-------|-----------|
| **Works E2E** | A user can trigger this, see results, and get value without developer intervention |
| **Works in isolation** | The subsystem functions but isn't wired to other systems or user-facing surfaces |
| **Scaffolding** | Code exists (modules, tests, types) but doesn't execute a real workflow |
| **Stub** | Interface defined, implementation missing or placeholder |

---

## What Actually Works End-to-End

### 1. Inbox Trust Wedge
- **Path:** Gmail ingest → adversarial debate → signed receipt → CLI approval → gmail.modify
- **Status:** Works E2E (the one proving path)
- **Limitation:** Requires manual Gmail OAuth setup, CLI-only approval, single-inbox only

### 2. Pipeline Internals (Ideas → Goals → Actions → Orchestration)
- **Path:** `IdeaToExecutionPipeline` → `GoalDecomposer` → `ActionPlanner` → `UnifiedOrchestrator`
- **Status:** Works in isolation — the internal pipeline executes but no user-facing trigger exists
- **Limitation:** No frontend, no API endpoint exposing the full pipeline to users

### 3. Self-Improvement Loop (Nomic Loop)
- **Path:** assess → plan → implement → verify → commit
- **Status:** Works in isolation — demonstrated in dogfood runs, Ralph V14 benchmark validated
- **Limitation:** Effectiveness unmeasured beyond internal benchmarks. No external validation.

### 4. PR Review via OpenClaw Watch Daemon
- **Path:** Poll GitHub → multi-agent review → post findings as PR comment
- **Status:** Works E2E on aragora's own repo
- **Limitation:** Requires daemon deployment, not self-service

### 5. CLI Quickstart Demo
- **Path:** `aragora quickstart --demo` → runs a canned debate → shows results
- **Status:** Works E2E (2-5 min, verified)
- **Limitation:** Uses demo data, not user's own content or API keys

---

## What Doesn't Work (PMF Gaps)

### Gap 1: No Working User Journey
**Severity: Critical**

There is no path where a new user can: sign up → add their API key → configure a debate → run it against real LLMs → see results. The pieces exist in isolation but are not wired together.

- No user registration/onboarding flow beyond `quickstart --demo`
- No API key management UI
- No "create a debate" user-facing flow
- No results dashboard showing debate outcomes

**Tracked in:** [#1046](https://github.com/synaptent/aragora/issues/1046)

### Gap 2: Provider Routing Not Wired to Arena
**Severity: Critical**

Debates don't call real LLM APIs through the provider routing infrastructure. The Pareto optimizer (PR #724) and 8-model pricing database exist but aren't wired to Arena agent selection. This means the core value proposition — heterogeneous multi-model debate — cannot be experienced by a user.

- `ProviderRouter` exists but `Arena` doesn't call it
- Agent selection doesn't consider cost/quality tradeoffs
- No runtime provider health checking during debates

**Tracked in:** [#813](https://github.com/synaptent/aragora/issues/813)

### Gap 3: Frontend ~8% Functional
**Severity: Critical**

~140 of 149 frontend pages are shells or scaffolding. The pages that render provide minimal interactivity and don't connect to real backend data flows.

- Landing page and demo page work
- Decision-integrity workbench renders but doesn't connect to live data
- Knowledge page, leaderboard, pipeline canvas — all shells
- No settings, onboarding, API key management, or debate creation UI

**Tracked in:** [#1047](https://github.com/synaptent/aragora/issues/1047)

### Gap 4: Knowledge Mound Reads Don't Enrich
**Severity: High**

The Knowledge Mound has 45 adapters ingesting data from various sources. But retrieval is not surfaced — KM content doesn't enrich debate context, search results, or user queries. It's a one-way data sink.

- 45 adapters write to KM
- No retrieval path feeds KM content into debate prompts
- No user-facing search or exploration of accumulated knowledge
- `KnowledgeMoundAdapter` in RLM bridge exists but isn't wired into default Arena flow

**Tracked in:** [#1048](https://github.com/synaptent/aragora/issues/1048)

### Gap 5: OpenClaw Dispatch Incomplete
**Severity: High**

The debate-to-execution bridge exists conceptually (CodeImplementationTask, SpecExtractor, ComputerUseActionBundle, receipt linkage from PR #727) but the execute loop doesn't complete. A debate can produce a decision but that decision can't automatically trigger safe agentic execution.

- Computer-use orchestrator exists but isn't wired to debate outcomes
- No automatic "debate decided → execute via OpenClaw" path
- Policy gates exist but haven't been tested with real execution

**Tracked in:** [#814](https://github.com/synaptent/aragora/issues/814)

### Gap 6: Blockchain/Staking Is Future-State
**Severity: Medium (not blocking PMF)**

ERC-8004 contracts, StakingRegistry, ComputeBudgetManager, ReceiptAnchor, SlashEvent — all exist as modules. Nothing touches a real chain. Staking/slashing is not wired into the debate outcome loop. Agent selection isn't weighted by compute budget.

**Tracked in:** [#816](https://github.com/synaptent/aragora/issues/816)

### Gap 7: Receipt Enforcement Trivially Exempted
**Severity: Medium**

The Decision Integrity Kernel (DIK) was wired across write paths (PRs #1021-#1031). But the exemption mechanism (`read_*`, `list_*`, `get_*`, `health_check`, `metrics`) covers most operations, and feature flags default to False. The gate exists but isn't enforcing.

**Tracked in:** [#812](https://github.com/synaptent/aragora/issues/812) (scale-out)

### Gap 8: Cross-System Wiring Incomplete
**Severity: High**

Subsystems exist as islands. Key missing wiring:

- Debate results don't feed into Knowledge Mound
- Knowledge Mound content doesn't enrich debate context
- Provider routing doesn't inform agent selection
- Settlement hooks don't trigger from real debate outcomes
- RLM compression exists but isn't the default in Arena
- ArenaConfig flags (`enable_rlm`, `enable_staking`) were recently wired but subsystems behind them are incomplete

**Tracked in:** [#1049](https://github.com/synaptent/aragora/issues/1049)

---

## Layer-by-Layer Assessment

| Layer | Built | Functional | Gap |
|-------|-------|-----------|-----|
| Backend infrastructure | 90%+ | 90%+ | Impressive but invisible to users |
| API contracts (OpenAPI) | 3,100+ ops defined | Untested E2E | Frontend can't rely on them |
| Debate engine | 210+ modules | Works in isolation | Not triggered by user-facing flows |
| Knowledge Mound | 45 adapters | Write-only | Retrieval not surfaced |
| Provider routing | Phase 1 shipped | Not wired | Core value prop doesn't work |
| Receipt infrastructure | Wired to 4 paths | Exempted by default | Gate exists but doesn't enforce |
| Frontend pages | 149 defined | ~12 functional | No usable product surface |
| CLI | 40+ commands | Most work | Best user interface currently |
| Self-improvement | Nomic Loop operational | Works internally | Not user-facing |
| Blockchain | Contracts written | Not deployed | Entirely future-state |

---

## PMF-First Priority Reframe

Based on this assessment, the priority order should be:

### Tier 1: Close the Product Loop (Immediate)
1. **Wire provider routing to Arena** — debates must call real LLMs via ProviderRouter
2. **Build one complete user journey** — API key → create debate → run → see results (even CLI-only)
3. **Make KM reads work** — debate context enriched by accumulated knowledge

### Tier 2: Demonstrate the Value Prop (Q2 2026)
4. **OpenClaw dispatch completion** — debate → decision → safe execution → receipt
5. **Frontend for the 5 paths that matter** — not 149 pages, just: debate creation, results, knowledge, settings, receipts
6. **10+ agent coordination** — demonstrate the heterogeneity value at scale

### Tier 3: Enterprise Readiness (After PMF Demonstrated)
7. Pentest and SOC 2 engagement
8. ERC-8004 deployment
9. Cloud marketplace listings
10. Vertical packages

---

## Recommendations

1. **Stop building new infrastructure** — the infrastructure is 90%+ complete. Start wiring it together.
2. **Pick one user persona** (e.g., "developer reviewing PRs") and make the complete journey work.
3. **Measure what users experience**, not what tests pass. 210k tests don't matter if no one can use the product.
4. **Pentest/SOC2 should wait** — certifying a product no one can use is premature investment.
5. **Frontend investment should be surgical** — 5 functional pages > 149 shells.

---

## Related Documents

- [FEATURE_GAP_LIST.md](../FEATURE_GAP_LIST.md) — Capability and productization backlog
- [CANONICAL_GOALS.md](../CANONICAL_GOALS.md) — Foundational thesis and goal definitions
- [NEXT_STEPS_CANONICAL.md](../status/NEXT_STEPS_CANONICAL.md) — Execution order
- [ACTIVE_EXECUTION_ISSUES.md](../status/ACTIVE_EXECUTION_ISSUES.md) — GitHub issue map
- [ROADMAP.md](../../ROADMAP.md) — Product roadmap

---

*This assessment should be refreshed quarterly or after major integration milestones. The next assessment should validate whether the product loop gaps identified here have been closed.*
