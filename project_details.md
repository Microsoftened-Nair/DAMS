# **Project Specification: Dual-Phase Autonomous Multi-Agent SDLC**

## **1\. System Overview & Core Philosophy**

This system is a **tech-agnostic, dual-phase, autonomous multi-agent software engineering framework**. It mirrors high-performing human engineering organizations by separating initial system scaffolding (**Phase 1: Greenfield Build**) from ongoing maintenance (**Phase 2: Event-Driven Issue-to-PR Maintenance**).

### **Core Architectural Pillars**

> 1. **Dual-Speed Lifecycle Split:** Phase 1 uses synchronous, high-speed, in-memory IPC with direct messaging between agents. Phase 2 transitions exclusively to an asynchronous, event-driven state machine powered by GitHub Issues, Pull Requests, and Webhooks.  
> 2. **Cleanroom / Double-Blind Software Engineering:** In Phase 1, the Coder Agent and Tester Agent operate under double-blind isolation. The Coder has no access to test source code or tester intent, and the Tester has no access to application source code. Test failure logs pass through an AST sanitizer before reaching the Coder to prevent test-overfitting.  
> 3. **Tech-Agnostic Dynamic Contract (agent\_manifest.json):** System runtime commands (build, lint, typecheck, test, run) are never guessed or hardcoded into agent system prompts. The Architect Agent generates a root manifest that downstream agents consume dynamically.  
> 4. **Bare-Metal Host Isolation:** The system operates directly on the local file system without Docker container overhead, using **Git Worktrees** for asynchronous concurrent task isolation, directory-scoped virtual environments, and dynamic port allocation.  
> 5. **Multimodal Visual & Structural QA:** Interface testing pairs Playwright DOM bounding-box math (to detect physical spatial collisions) with Vision-Language Model (VLM) screenshot critique (to evaluate layout, hierarchy, and responsive scaling).  
> 6. **Deterministic Safety Guardrails:** Full autonomy to merge into main is constrained by strict mathematical invariants: test assertion monotonicity (![][image1]), diff size limits, automated post-merge rollbacks, and a 3-attempt circuit breaker with Architect arbitration.

## **2\. Dynamic Execution Manifest Schema (agent\_manifest.json)**

At project inception (Phase 1 start), the Architect Agent generates agent\_manifest.json at the repository root. Every downstream agent reads this file to execute commands:  
{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "AgentManifest",  
  "type": "object",  
  "required": \["manifest\_version", "project\_name", "runtime", "commands", "contracts"\],  
  "properties": {  
    "manifest\_version": { "type": "string" },  
    "project\_name": { "type": "string" },  
    "runtime": {  
      "type": "object",  
      "required": \["language", "version", "package\_manager", "ui\_type"\],  
      "properties": {  
        "language": { "type": "string" },  
        "version": { "type": "string" },  
        "package\_manager": { "type": "string" },  
        "ui\_type": { "type": "string", "enum": \["cli", "web", "desktop", "library", "service"\] }  
      }  
    },  
    "commands": {  
      "type": "object",  
      "required": \["install", "build", "lint", "test\_unit", "dev\_server"\],  
      "properties": {  
        "install": { "type": "string" },  
        "build": { "type": "string" },  
        "lint": { "type": "string" },  
        "typecheck": { "type": "string" },  
        "test\_unit": { "type": "string" },  
        "test\_integration": { "type": "string" },  
        "dev\_server": { "type": "string" }  
      }  
    },  
    "contracts": {  
      "type": "object",  
      "required": \["entry\_point", "specs\_dir", "source\_dir", "test\_dir", "port\_variable"\],  
      "properties": {  
        "entry\_point": { "type": "string" },  
        "specs\_dir": { "type": "string" },  
        "source\_dir": { "type": "string" },  
        "test\_dir": { "type": "string" },  
        "port\_variable": { "type": "string" }  
      }  
    }  
  }  
}

## **3\. Phase 1: Greenfield Build Workflow & Protocol**

### **Step-by-Step Synchronous Loop**

> 1. **Goal Ingestion & Architecture:** The user provides a project request. The Architect Agent creates docs/specs/spec.md, breaks the requirements into atomic task units (![][image2]), and writes agent\_manifest.json.  
> 2. **Contract Broadcast:** For Unit ![][image3], the Architect broadcasts the contract (I/O schemas, API endpoints, CLI parameters) to the Coder and Tester simultaneously.  
> 3. **Double-Blind Execution:**  
   * **Coder Agent:** Reads docs/specs/, agent\_manifest.json, and writes logic in src/. It cannot see tests/.  
   * **Tester Agent:** Reads docs/specs/, agent\_manifest.json, and writes black-box tests in tests/. It cannot see src/.  
> 4. **Deterministic Pre-Gate:** The orchestrator executes lint and typecheck commands from agent\_manifest.json. If this fails, stdout/stderr is returned directly to the Coder without invoking the Tester.  
> 5. **Test Execution & Log Sanitization:** The orchestrator executes test\_unit.  
   * **Pass:** If exit code is 0, the orchestrator advances to Unit ![][image4].  
   * **Fail:** The orchestrator passes raw test logs through the AST Sanitizer Gate, stripping test line numbers, test file paths, and internal assertion lines before sending diagnostic feedback to the Coder.  
> 6. **Visual QA Gate (UI Projects Only):** If runtime.ui\_type is web or desktop:  
   * The dev server is spawned using dynamic port binding (PORT=$RANDOM\_PORT).  
   * Playwright calculates bounding boxes (getBoundingClientRect()) to check for DOM element collisions.  
   * Viewport screenshots (1920x1080 desktop, 375x812 mobile) are passed to the Tester VLM to check for clipping, overlap, and visual balance.  
> 7. **3-Attempt Arbitration Protocol:** If Coder and Tester exchange feedback 3 times without a passing build, an arbitration event triggers:  
   * Coder and Tester send their respective interpretations to the Architect.  
   * The Architect evaluates the ambiguity, issues an authoritative ruling, updates docs/specs/spec.md, and resets the iteration counter.  
> 8. **Phase Transition:** Once all units pass and main is tagged v1.0.0-baseline, Phase 1 ends. In-memory IPC channels are terminated.

## **4\. Phase 2: Asynchronous GitHub Maintenance Workflow**

Execution operates exclusively through GitHub event triggers using gh CLI commands and Git Worktrees.  
\+------------------+         \+------------------+         \+------------------+  
| Synthetic User   |         |   Triage Agent   |         |    Fix Coder     |  
|                  |         |                  |         |                  |  
| 1\. Random seed   |         | 1\. De-dupe check |         | 1\. Git Worktree  |  
|    exploration   |-------\> | 2\. Isolated      |-------\> | 2\. Add failing   |  
| 2\. Capture logs  |  Issue  |    reproduction  |  Spec   |    regression    |  
| 3\. gh issue create         | 3\. Fix spec      |         | 3\. Implement fix |  
\+------------------+         \+------------------+         \+--------+---------+  
                                                                   |  
                                                                   | Push & PR  
                                                                   v  
\+------------------+         \+------------------+         \+------------------+  
|   Main Branch    |         | Maintainer Agent |         | Reviewer Critic  |  
|                  |         |                  |         |                  |  
| Stable baseline  | \<------ | 1\. Assertions    | \<------ | 1\. Read-only     |  
| production code  |  Merge  |    monotonicity  |  Sign   |    diff review   |  
|                  |         | 2\. Auto-squash   |   off   | 2\. Policy audit  |  
\+------------------+         \+------------------+         \+------------------+

### **Role Breakdown & Command Protocols**

#### **1\. Synthetic User**

> * **Task:** Autonomous exploratory testing using headless Playwright or CLI fuzzing.  
> * **Output:** Creates structured GitHub issues:  
>   gh issue create \--title "bug: \[Component\] Short Description" \--body "$STRUCTURED\_BUG\_REPORT"

#### **2\. Triage Agent**

> * **Task:** Ingests issues.opened events. Checks for duplicates via semantic similarity search. Reproduces the bug in a temporary workspace and posts a fix spec as an issue comment.  
> * **Command:**  
>   gh issue comment $ISSUE\_ID \--body "$FIX\_SPECIFICATION"

#### **3\. Fix Coder Agent**

> * **Task:** Spawns an isolated Git Worktree, writes a failing regression test, implements the fix in src/, verifies tests pass, and pushes the branch.  
> * **Commands:**  
>   git worktree add .worktrees/fix-issue-$ISSUE\_ID \-b fix/issue-$ISSUE\_ID  
>   cd .worktrees/fix-issue-$ISSUE\_ID  
>   \# ... implements fix and regression test ...  
>   git commit \-m "fix(\#$ISSUE\_ID): resolve application defect"  
>   git push origin fix/issue-$ISSUE\_ID

#### **4\. Reviewer Critic Agent**

> * **Task:** Performs read-only inspection of the branch diff. Verifies that no existing tests were deleted, checks code style, and opens/approves the PR.  
> * **Commands:**  
>   gh pr create \--title "fix: resolve issue \#$ISSUE\_ID" \--body "Closes \#$ISSUE\_ID\\n\\n\#\#\# Changes\\n$SUMMARY" \--head fix/issue-$ISSUE\_ID  
>   gh pr review $PR\_ID \--approve \--body "Diff verified. Test monotonicity preserved."

#### **5\. Maintainer Agent**

> * **Task:** Evaluates pre-merge invariants and auto-merges approved PRs. Performs immediate post-merge entry point health check on main.  
> * **Commands:**  
>   gh pr merge $PR\_ID \--squash \--delete-branch  
>   \# If post-merge health check fails:  
>   git checkout main && git pull  
>   git revert HEAD \--no-edit  
>   git push origin main  
>   gh issue create \--title "CRITICAL: Reverted PR \#$PR\_ID" \--body "Post-merge health check failed."

## **5\. Agent Personalities & System Prompts (SOUL.md)**

System prompt profiles deployed to \~/.hermes/profiles/\<role\>/SOUL.md:

### **Architect Agent (architect/SOUL.md)**

\# Role: System Architect  
You design software architectures, establish interface contracts, generate build manifests, and referee ambiguous specifications.

\#\# Constraints & Rules:  
1\. Deconstruct user requests into an ordered sequence of atomic implementation specs.  
2\. Emit \`agent\_manifest.json\` at the repo root defining exact build, lint, test, and run commands.  
3\. Specifications must explicitly define JSON schemas, route signatures, error responses, and boundary rules.  
4\. Do NOT write application source code or unit test code.  
5\. In arbitration mode, evaluate Coder and Tester arguments, issue a binding clarification, and update \`docs/specs/spec.md\`.

### **Coder Agent (coder/SOUL.md)**

\# Role: Implementation Engineer  
You implement application logic in accordance with strict interface specifications.

\#\# Constraints & Rules:  
1\. You have access ONLY to \`src/\`, configuration manifests, and \`docs/specs/\`. The \`tests/\` directory is strictly hidden from your view.  
2\. Implement one specification unit at a time.  
3\. If sanitized test failure diagnostics are provided, resolve the underlying bug in \`src/\`. Never attempt to guess test source code.  
4\. If a specification is contradictory or ambiguous, submit an explicit Arbitration Request targeting the Architect.  
5\. Do not install global dependencies; use only local tools defined in \`agent\_manifest.json\`.

### **Tester Agent (tester/SOUL.md)**

\# Role: Black-Box Verification & Multimodal QA Engineer  
You create independent validation suites and verify software functionality strictly through public interfaces and visual inspection.

\#\# Constraints & Rules:  
1\. You have access ONLY to \`tests/\`, \`docs/specs/\`, and running binaries/ports. You are strictly BLIND to \`src/\`.  
2\. Write unit and integration tests based strictly on the Architect's specification contracts.  
3\. For UI tasks, evaluate layout integrity using both Playwright bounding box math and visual screenshot review.  
4\. Report contract failures using clean external schemas (expected vs. actual behaviors, status codes, stdout/stderr).

### **Triage Agent (triage/SOUL.md)**

\# Role: Bug Triage & Localization Specialist  
You review bug reports, eliminate duplicate tickets, and formulate precise fix requirements.

\#\# Constraints & Rules:  
1\. Ingest newly filed GitHub Issues and run deduplication searches across active issues.  
2\. Reproduce reported failures in a clean environment.  
3\. Pinpoint probable failure components using stack traces and repository symbols without rewriting code.  
4\. Post structured fix plans as issue comments, defining expected inputs, outputs, and edge cases.

### **Reviewer Critic Agent (reviewer/SOUL.md)**

\# Role: Code Review Critic  
You perform read-only evaluations of Pull Request diffs.

\#\# Constraints & Rules:  
1\. You hold STRICT READ-ONLY access. Do not write or modify code directly.  
2\. Verify that every PR includes a new regression test reproducing the underlying bug.  
3\. Validate that existing tests remain unchanged and overall test count is non-decreasing.  
4\. Reject diffs that contain dead code, broken naming conventions, security vulnerabilities, or scope creep.

### **Maintainer Agent (maintainer/SOUL.md)**

\# Role: Release & Merge Gatekeeper  
You maintain branch integrity and manage pull request merges into \`main\`.

\#\# Constraints & Rules:  
1\. Merge pull requests ONLY if:  
   \- CI status is 100% GREEN.  
   \- Reviewer Critic has approved the diff.  
   \- Test assertion monotonicity is preserved (zero tests deleted/skipped).  
   \- Diff does not exceed maximum allowable changes (\< 500 lines modified).  
2\. Execute merges via squash-merge: \`gh pr merge \<PR\_ID\> \--squash \--delete-branch\`.  
3\. If post-merge entry point health checks fail on \`main\`, execute immediate rollback: \`git revert HEAD \--no-edit\`.

## **6\. Deterministic Safety Invariants & Circuit Breakers**

> 1. **Test Assertion Monotonicity Gate:**  
>    A pull request is rejected automatically if:  
>    ![][image5]  
> 2. **Diff Size Ceiling:** Pull requests modifying ![][image6] lines or ![][image7] files are automatically blocked from autonomous merge and assigned @human-review.  
> 3. **Automated Post-Merge Rollback:** If the application entry point crashes or returns HTTP 5xx during an immediate post-merge health check on main, the Maintainer Agent immediately executes git revert HEAD \--no-edit, pushes to main, and re-opens the issue.  
> 4. **Iteration Circuit Breaker:** Any Phase 1 or Phase 2 task cycling between Coder and Tester/Reviewer more than **3 times** without reaching a passing state triggers a circuit breaker, freezing the task and escalating to human review or Architect arbitration.

## **7\. Directory Structure Template**

/home/user/project\_root/  
├── agent\_manifest.json          \# Generated by Architect at Phase 1 start  
├── docs/  
│   └── specs/  
│       ├── spec.md              \# System specification and task queue  
│       └── arbitration.log      \# History of Architect arbitration decisions  
├── src/                         \# Application source code (Coder access only)  
├── tests/                       \# Black-box test suite (Tester access only)  
│   ├── unit/  
│   ├── integration/  
│   └── visual\_artifacts/        \# Screenshots & Playwright bounding box diffs  
├── .worktrees/                  \# Phase 2 isolated git worktrees  
│   ├── fix-issue-101/  
│   └── fix-issue-104/  
└── .github/  
    └── workflows/               \# GitHub Actions for CI status triggers

## **8\. Summary of Agent Access Permissions**

| Agent Role | File System Access | Network / CLI Permissions | Isolation Strategy |
| :---- | :---- | :---- | :---- |
| **Architect** | Read/Write docs/, Write agent\_manifest.json | Read-only CLI | None (Global spec author) |
| **Coder** | Read/Write src/, Read docs/, agent\_manifest.json | Local dev server execution | Hidden from tests/ tree |
| **Tester** | Read/Write tests/, Read docs/, agent\_manifest.json | Playwright, VLM, test runners | Hidden from src/ tree |
| **Triage** | Read-only repo access | gh issue, local test runner | Ephemeral worktree workspace |
| **Fix Coder** | Read/Write src/ & tests/ on issue branch | git, local test runner | Git Worktree (.worktrees/fix-issue-$ID) |
| **Reviewer** | Read-only git diff access | gh pr, gh issue | Read-only, no code write tools |
| **Maintainer** | Read-only repo access | gh pr merge, git revert | Admin merge authority bounded by invariants |

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHsAAAAaCAYAAACXbyOAAAADXUlEQVR4Xu2YWahNYRTHlylCMpM8KZIQQry4x1iUIRlSUjwYUsqDUJIhoYTMZUryIKWQiOSSJBIeZMxQyIsh8mCK/9/6Tr6znH3OPfvse7dz+n717569/vuetdf5vv1NIoFAIBAIBAKBQCBdVkB3oZ/QL+gxdBNq4/wh0BPn8Z6n0DTnxWUsdBv6LPq9b9x1jfObQXeg756/yXmVTuq1s2F/QC+t4XEFmmKDZXJLtKAe1nCshbbbYJWQWu2TRRPvtYaDve0Z1NgaZdBedKR4YA2P81A/G6wCUq19j2hjT7KGYwR0zAbLZIZozq3WcLQQnT6qkVRr5zz8FWptDccGaI4NlskB0YLHWcPBue2QDVYJqdXOOYOJL1nDg/NLVxssE64Pvoj24nxsgWbaYJWQWu0LRRt7mTUcnURXh5a20FIbrCO9RXOetYbHPaiDdz1PdE1xXXTh0sTzKok4tSfGSdHkA63hmA1tNrHd0CnolYnXlSWiOaM6S3fohnfdH6qFmkItoRfQcs+vJEqtPVEeQp8keqV9AepjgyAj8Rt7n2jBg63hWA3N966Hi+bK9vbD0NW/dkVRau2Jcg56b4OORRK9YsxIdGOzd3JBxy1bPvhWsmC+sRYe4lyWwsM01xdHTaxYTjIGGmCDHl2gWVI490Solw16FHuOUmvvCR2EToh+7yrRjh5rW5aBvonO3Vk6Q9ug/RL9xmckurHPiBa00hoO/qj83yNQcxfj38WiDcl9aBT8kT6Izn0+xXL2FfXfWcODe1veM9caDnYW+vet4VHsOUqtfT3UTfREjVtgskui11hFqRFNxCH9kehp2fScO/4lI9GNzUI/iq4HouAugHt35uPhAo9s2euzP0A+OF/Xig7rlmI52YGfQ6et4cEtJjvDUGs4+Ja9FX0Joij2HKSU2ttBUyV3t3RNdIRpMDLQaxv04J79uA2WQSPRH3mQu+apnyXpnHFJ+jl2QGvcZ3ZadqZWoh2hQciIHtJHMV50zk+KjdACaJjocLYz1/5D0jnjkvRzcOs70n3mFMOONEF0Wql3uEjg/MZTN64umdiHCwwOlx1NPC6jRedBX+ty7kg+Z1ySfg6umTj9ZA9gOOVelOg1QYMzSurpBKgAaeTMx//yHIFAIBAIBCqQ3wxlzCvd4IX3AAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAaCAYAAABctMd+AAABSElEQVR4Xu2UvyuFYRTHv5RNspDNj9EmWTGYDBjYpHQN9+73xmowWMiAQSFlkzIpZTApBka/En8AykbE93Qedd+v9+pxbXo/9anb9zyde95zn/cCGRm/ZYae03f6Qa/oCW0I9R56HWp25oaOhloU1uiN3muhjCM6omEMw/DJVrUQqKO3tFYLMazAmw9pIdBLtzWMxfb4Quu1EJijExrG0AGf+lALZZzSFg1jyMObl7QQaKJnknXTY7or+TfsgDXv0kJgnM5rSDZpUUPlgj6j8k04oJ0akjv4E/zIPn3UMFCgCxqSdvoEH2iK7qDCTeunr/Ddf9FMF+ka0p9oku7RHG2F/yapzY0++G2xFV3C38axxIkkW/SBTsNfsLQBqsb+Jmzfy3QJ3rwxcaJK2uBT18D3vU4H4Ov9M4N0I3y2W2TrnIV/WcZ/5RPLrTrpYkZu3gAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAaCAYAAAAqjnX1AAABoklEQVR4Xu2VPShFYRjHH8omWYhBPjLIoCQTcQeDDBjYpMTAqIjBYlAsZPBRColBSZlIGUyKgdFXorChbET8n5731rn/zr3dW9cRnV/96vZ/Tvc85z3Pe16RkJCQ/80oPIOf8AtewmOY4+q18MrV9Jpr2OFqgaINfcA7Lng4hO0cBkmb2EotcMGRBW9gJheCZF6syVYuOBrgBodBo3P2BrO54JiA3RwGSZnYKh5wwcMJLOAwSPrFmhzmgiMPnlJWA4/gNuWpkgsHOfRDb6RNVnPB0QWnOASrcIhDohxWceiYgzvwngt+nMNXib9z92Elh+BWbEUTUQebOfQQkSSb3IXPHDoG4DSHoBS+iD1YH9wS/y9DvaSpyQh8F5vNKPlwBi6J/wr3iL2qXlgsNrM/2qTSKLa79dVfiJ0unTFXxLIGn+CI2Ic++iCFcNLjOtykrMhdq0QkhSZTRY9PnUcd/lmxJnWnMsms5AOH6aBEbBUzxOZxGTaJ3ZBJpslHDtNBC1xxv3XX65iMizXNJGpyDO6JnXSLYv/7K1RI/O9vSMif5Bu8wE/z+z19yQAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADUAAAAZCAYAAACRiGY9AAACsElEQVR4Xu2WWYhOYRjH/9aEQQxliZFkuzFKIfLdcCPlanIjLoQbKa4saS4UV3IhUcqSrSTZs2UmihCuZCtZkiX7cof5/+d5zznveWfO8X3faKLOr371Pc/7zpn3Ped5F6CgoOB/YQWdR2tpHzqDHqfT/U5kMr1Cr9E7dA3tkuphzzhAb9HbdBetSfXoJK7S34FnaE+vz0j6gS5y8UB6n26IewDd6E26GzZZxQfpJa9Pp9FEH9CXsK+wnHb1O5AdsD4++sLfaX8XN8BeyLC4BzDe5eZ4uTaU6Ek6K8h3hMu0Lkx66K2/oceCfAk2YE1GHKXv41ZDX+sn7KXkMgr2iS/Q2UFbNag86sKkxwjY4PcE+XqX3+ziJ/Rp0hzzmV4Pk1mMoXvpRXRscvr7VfQcbIGfhZVNxFTY4LXofSa5/H4XqxQfJs0x7+jzMPknxsIerDdezeTO061I1tEm+grJ2tAzNfidLo6Y4PLaKcUvtF13QqX7MUyWyzgku00la24i0hvDaNhgt7m45OK8SWnd6fdfn1SEBqkS0prrFbSVgxa3BvjIxVnlp/+jvM4lkVV+b2E7a9UMoI2ww3FJqqV9dOh+QbKDRaiUvrnfQ2GD35c0txJtFFtcrAk9S5pjtFHcCJPloLNiI71Ll9Lu6eZMGmEDW+/lervcYy/3mp7yYqGzR/0WuvgI/Zo0t9ID7ZduLv1gp/o92KGph1TCAnoCVnIR02ADibZqoXPGn6RYTX/AqkNEh+/wuAcwxeXmerlM+tJ1sC+jk92/0lSCNgjdIua7WANshl2B/DubzqpPdLGLB9MXdG3cw54VXZP0W9VyGra75qKFr4ukLov6MtVOxmcIPQw7PLWgNShdTEP01ptgA9fLXJlqNQbRQ7DKkdth5ZzLTLoMlZdZQUFBQcE/Qwuws5SLRV1tgQAAAABJRU5ErkJggg==>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAZCAYAAABQDyyRAAABeElEQVR4Xu2VvStGcRTHv14jQkkmGSRSBotS5GVh8T8YhJ1JyIZSRJRSpKQMBoPBy2hQwiJKDAZmJWXie5znee79nTyee6/udj/1GZ5zTvee3/md7gMkJMRHPp2id/SKHtM2pyJmFugiLUj97qSvtCFTESPl9A06BT8bdM7Efuihh7TLxKPSSL9oq4nLVFZNLEM93YTeVbfJhaWMfkJH3p+KldIHBHi23NE2PUGA4j+Yh05BXKdndMKpyIGMcYeeIlojcv9b8JqQabQ7FQFporvQRsLsyCB9pGP0GdrEB+3wF4WhhR5Bd6TE5CzN9B3eElbRfWgTN+miMMgDZqEflCEn8zsr9MAGyRq0iRqbyEYlnaHXdJgWuumsyGmXbBA6GWmg1iYsFdDPqIxrlBa56ZxM0wuaZ+K99N7EHOQLNgk9sSxPsZsOTDV08Zbh7Yvswy0dSBf5kaJxegk9cdQX+6mje/SFPtFz2udU+JA/ihGEH3VCQsK/+QZ7FT8ghsUJrwAAAABJRU5ErkJggg==>