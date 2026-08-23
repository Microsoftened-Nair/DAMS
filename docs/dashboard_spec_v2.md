# Specification v2: Multi-Agent Command Center & Observability Dashboard

Revised from dashboard_prompt.txt after feasibility review against the DAMS
codebase (src/dams/). Changes from v1 marked [MOD] / [DEFER] / [ADD].

## 1. Executive Overview & Objectives

Real-time web platform to monitor, inspect, and control the dual-phase
autonomous multi-agent SDLC framework. Provides operational authority:
in-browser project creation, spec management, pipeline observability,
guardrail monitoring, and human-in-the-loop overrides.

Core objectives:
- Project lifecycle management (launch, edit specs, trigger phases)
- Global pipeline command & control (pause/resume, force arbitration,
  manual merge override, circuit breaker reset)
- Observability (agent status, session costs, event stream, logs)
- Phase isolation verification (cleanroom views, sanitizer audit)
- Safety invariant monitoring with signed human overrides

## 2. System Architecture

+-----------------------------------------------------------------------------------+
|                        DAMS Orchestrator (Python)                                 |
|   Phase1Orchestrator | Phase2Pipeline | controller.py                             |
+-----------------------------------------------------------------------------------+
        ^                                       ^                    ^
        | WebSocket (commands)                  | REST               | in-process
        v                                       v                    v
+------------------------+    +----------------------------------+   +--------------------+
| Dashboard Backend      |--->| Local System Access              |   | Event Bus          |
| FastAPI + uvicorn      |<---| (git, gh CLI, hermes CLI spawns, |   | (.dams/events.jsonl|
| src/dams/dashboard/    |    |  profile state.db polling)       |   |  append-only)      |
+------------------------+    +----------------------------------+   +--------------------+
        |
        | JSON telemetry over WS
        v
+-----------------------------------------------------------------------------------+
|              Interactive Web Command Center UI                                    |
|  (Next.js 14 App Router + Tailwind + shadcn/ui + Recharts + xterm.js)             |
+-----------------------------------------------------------------------------------+

[MOD] Backend is Python/FastAPI, not Node.js — native access to orchestrator
classes, single language, no cross-process bridge. Runs via `dams.py serve-ui`.

[ADD] Event bus: every orchestrator action (gate pass/fail, arbitration,
merge, rollback, spawn) appends to <root>/.dams/events.jsonl — the dashboard's
source of truth for history, and roadmap item "audit trail" addressed early.

## 3. Project Launcher & SDLC Management

### 3.1 In-Browser Project Launcher Wizard
- Project name/description + core functional prompt
- Runtime dropdowns: language, package manager, ui_type (mirrors manifest schema)
- [MOD] Model Allocation Matrix: per-role model selection applied at LAUNCH
  time (written to profile configs before spawn). Mid-run hot-swap deferred —
  agents are one-shot processes; see DEFER list.
- One-click launch → spawns Phase1Orchestrator as a managed background job

### 3.2 Spec Center & Backlog
- Split-pane markdown editor for docs/specs/spec.md (rendered + source),
  auto-save, guarded: edits during active unit loop prompt for confirmation
- Kanban board [MOD] columns matching real orchestrator states:
  Backlog | In Progress (coder/tester loop) | Gates Failed | Arbitration | Passed
- Drag-drop reordering writes unit order back to spec.md headings
- Milestones view: tags (v1.0.0-baseline), release log, manual P1→P2 trigger

## 4. Agent Fleet Grid

Card grid, one card per role. [MOD] Fix Coder shown as "Coder (worktree)"
state of the coder role — there are 6 profiles, not 7 agents.

Per card: role name, model/provider, current status (from live process scan
of `hermes --profile <role>` + events.jsonl), last session id, files domain.

Card actions [MOD]:
- View recent sessions (read-only transcript links into profile DBs)
- Queue instruction for NEXT round of this role (injection into running
  one-shot agents is impossible; queueing is honest and useful)

## 5. Operational Modules

### 5.1 Cleanroom Ispection
- Double-blind split view: Coder pane (tests tree blurred + BLIND DOMAIN
  badge) vs Tester pane (src blurred + badge) — rendered from filesystem
- Sanitizer inspector: toggle raw test log vs sanitized output, diff
  highlighting stripped paths/lines/assertions
- Visual QA canvas: bounding-box overlays, desktop/mobile screenshot panels
  (active only for web/desktop ui_type projects)

### 5.2 Phase 2 Maintenance Explorer
- Issue & triage kanban with dedup confidence and fix-spec links
- Worktree inspector: .worktrees/ tree view + per-worktree test status
- Pre-merge invariant checklist:
  [x] Test monotonicity (ΔTests ≥ 0)
  [x] Diff ceiling (<500 lines)
  [x] Reviewer approval
  [ ] CI status — [MOD] renders "not configured" until CI integration exists
- Post-merge health monitor with git revert trigger button

## 6. Terminal & Emergency Command Center

- Multi-tab terminal: global feed + per-role logs (parsed from events.jsonl
  and profile agent.log tails); severity filter incl. SANITIZED; regex search
- Embedded PTY terminal (xterm.js + WS) scoped to project root or a chosen
  worktree
- Global controls:
  - PAUSE/RESUME pipeline (SIGSTOP/SIGCONT on daemon pid + .dams/pause flag
    checked between agent rounds)  [MOD: global-only, no per-agent freeze]
  - Force arbitration (escalate current unit to Architect now)
  - Manual override & merge (bypasses guardrails, requires typed operator
    signature, logged to immutable audit file)
  - Reset circuit breaker

## 7. Visual Design System (unchanged from v1)

Obsidian Glassmorphism dark cyberpunk theme: #090D16/#0F172A base, glass
cards rgba(30,41,59,0.7) blur(12px), accents Electric Emerald #10B981 /
Violet #8B5CF6 / Amber #F59E0B / Crimson #EF4444 / Cyan #06B6D4 with glow
filters. Inter/JetBrains Mono, tabular metrics, Framer Motion pulses/gauges/
particle flow graph/spring modals. Responsive: ≥1440px 3-column, 1024–1439px
collapsible + Cmd+J drawer, ≤1023px stacked tabs + FAB (pause/arbitration).

## 8. Manifest Inspector

Live parsed agent_manifest.json with draft-07 validation badge against
MANIFEST_SCHEMA, read-only in v1 ([MOD]: direct editing risks mid-run
contract drift; edit-via-Architect workflow comes later).

## 9. [ADD] Cost & Audit Panel

- Token/cost aggregation per role, per unit, per PR — sourced from profile
  state.db session_model_usage tables (poll every 30s)
- Immutable event stream viewer filtering by role/event/severity
- Export: JSON/CSV of full run history

## 10. Security

[ADD] Token-gated auth on the backend from day one (DAMS_CONTROL_TOKEN in
.dams/, required as Bearer header; UI prompts once). The dashboard can kill
processes and force merges — it must never be unauthenticated on a network.
Secrets (.env contents) are never exposed through any endpoint.

## Deferred to v2 (data source does not exist yet)

- Live token-by-token context-fill gauges (needs streaming agent mode)
- Per-agent freeze (global pause covers the real need)
- Hot model swap mid-run (config applies at next launch)
- Direct manifest editing
- CI status integration
- Instruction injection into RUNNING agents (queue-for-next-round instead)
