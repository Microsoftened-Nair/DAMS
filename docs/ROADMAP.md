# DAMS — Improvement Roadmap

Captured 2026-08-23 after the wordstats autonomous test run. Ranked by impact
on real-world usefulness.

## 1. Human interaction layer (HIGHEST PRIORITY)
- No way to intervene mid-run ("stop, do it this way instead")
- Needed: observability dashboard + control centre (approve plans, redirect
  arbitration, review builds) — user is preparing a spec prompt for this
- Without visibility/control, no team trusts autonomous code generation

## 2. Code quality ceiling
- Passing tests ≠ good software; no review for perf-at-scale, security
  posture, maintainability, API design taste
- Output is spec-compliant, not senior-engineer-grade

## 3. Single-repo naivety
- Phase 1 assumes greenfield only; no existing-codebase support
- No CI integration (GitHub Actions results feeding back into loop)
- No monorepo/multi-repo, feature flags, DB migrations, human pre-merge review
- Branching model too simple for real teams

## 4. Trust & accountability
- No audit trail beyond scattered profile session DBs
- Arbitration rulings not signed/explainable to stakeholders
- No cost tracking (token spend per unit/PR invisible)
- Secrets risk: agents run with full .env access; prompt injection via a
  crafted bug report could exfiltrate keys → scope agent env access

## 5. Reliability engineering
- Known failures needing manual diagnosis in tests: manifest non-compliance
  (fixed w/ retry), env-dependent gate failures (fixed via env normalization),
  empty-repo push (fixed w/ commit-before-tag + sanity check)
- Need: self-healing for common failure classes, root-cause retries,
  health metrics instead of human log-reading

## 6. Ecosystem integration
- No Jira/Linear/Slack hooks
- No multi-model routing (cheap model for triage/synthetic-user, strong for
  architect); vLLM candidate for fallback/cheap roles
- No parallel unit execution (units are sequential today)
- No caching of agent work between runs

## Deferred tool decisions
- Ponytail: ADOPTED (coder/reviewer prompts, SOUL.md + orchestrator injection)
- GSD (get-shit-done): skip framework, cherry-pick ideas — plan-checker gate
  before execution, wave execution (parallel units), state files for resume,
  PR body standards
- vLLM: revisit when there's a real cost signal; fallback/cheap-role serving

## Suggested order
dashboard (1) → cumulative regression testing between units (2/3) →
CI feedback loop → cost/audit dashboards (4) → multi-repo (3)
