# AGENTS.md

## Graphify — Mandatory

Graphify is a required **skill tool** in this project and the **primary way to navigate and understand the codebase**.

**Whenever you need to search, navigate, understand, or locate anything in the codebase, you MUST invoke the Graphify skill FIRST — as a skill tool call, not as a shell command.**

Do NOT run `graphify` via bash/shell. Invoke it through the skill tool interface provided by the agent framework.

Always read and follow the Graphify skill instructions before performing codebase searches or navigation.

Use Graphify to:

1. Locate relevant files, directories, symbols, functions, classes, types, components, and code paths.
2. Understand how existing functionality is implemented, including relationships, dependencies, usages, and code paths.
3. Determine which files and locations need to be edited.
4. Inspect related or affected code before making changes, including when refactoring, moving code, or investigating bugs.
5. Verify the potential impact of changes when appropriate.

Do not guess file paths, symbols, dependencies, or edit locations when Graphify can determine them.

Do NOT use `grep`, `rg`, `find`, `ag`, shell pipelines, or IDE search to locate code when Graphify can answer the question. These are **last-resort fallbacks only**, permitted only when Graphify explicitly returns no result.

Do not chain bash commands as a workaround to bypass these restrictions. A command pipeline that starts with an allowed command (e.g. `echo`) and appends `grep` or `find` via `&&` or `;` is still a policy violation.

If Graphify is unavailable or cannot answer the question, explicitly acknowledge this before falling back to another search method.

Do not claim to have used Graphify if you did not.

---

This file governs the default development workflow for this repository, with the goal of reducing repetitive communication, reducing rework, and keeping changes aligned with the current project structure.

If this file is inconsistent with the repository's scripts, workflows, or actual code, defer to what is actually executable, and fix the documentation in the relevant change to prevent the rules from continuing to drift.

## 1. Hard Rules

- Respect existing directory boundaries:
  - Backend logic goes primarily in `src/`, `data_provider/`, `api/`, `bot/`
  - Web frontend changes go in `apps/dsa-web/`
  - Desktop changes go in `apps/dsa-desktop/`
  - Deployment and pipeline changes go in `scripts/`, `.github/workflows/`, `docker/`
- Do not run `git commit`, `git tag`, or `git push` without explicit confirmation.
- Use English for commit messages, and do not add `Co-Authored-By`.
- Do not hardcode secrets, accounts, paths, model names, ports, or environment-specific logic.
- Prefer reusing existing modules, configuration entry points, scripts, and tests; do not add parallel implementations.
- Default to stability over "convenient optimization"; refrain from refactoring, abstraction, and infrastructure migration that is not directly needed by the current task.
- When adding a new configuration item, you must also update `.env.example` and the relevant documentation.
- When a change affects user-visible capabilities, CLI/API behavior, deployment methods, notification methods, or report structure, you must update the relevant documentation and `docs/CHANGELOG.md` in parallel.
- When modifying report format, report rendering, or Web UI, the PR description must include screenshots of the affected report / page; prefer before/after comparisons when there are before/after differences; if screenshots are not possible, explain why and provide alternative visual evidence.
- Issue/PR process screenshots, review screenshots, one-time acceptance screenshots, and temporary visual evidence must not be merged into the repository as files; put them in the PR description, PR comments, GitHub attachments, Actions artifacts, or externally accessible evidence links. This does not apply to illustrative diagrams that long-term product documentation genuinely needs, but the filename and documentation semantics must be decoupled from any specific issue/PR number.
- The `[Unreleased]` section of `docs/CHANGELOG.md` uses a **flat format**: each entry on its own line, in the form `- [type] description`, where the type is one of: `新功能`/`改进`/`修复`/`文档`/`测试`/`chore`; **do not add `### category headings` inside `[Unreleased]`** to reduce merge conflicts between concurrent PRs. At release time, the maintainer consolidates and reformats with headings.
- `README.md` is only for home-page-level information such as project positioning, a core capability overview, getting started, main entry points, and sponsorship/cooperation; do not update README unless necessary, to avoid it growing endlessly.
- For more detailed module behavior, page interactions, topic-specific configuration, troubleshooting, field contracts, implementation semantics, and edge conditions, prefer updating the corresponding `docs/*.md` or topic documentation instead of writing it into README.
- When changing one of the bilingual (Chinese/English) docs, evaluate whether the other needs to be synced; if it is not synced, state the reason in the delivery notes.
- Comments, docstrings, and log text should be clear and accurate; English is not strictly required, but they should be consistent with the file's context.

## 2. AI Collaboration Asset Governance

- `AGENTS.md` is the single source of truth for AI collaboration rules in this repository.
- `CLAUDE.md` must be a symlink pointing to `AGENTS.md`, for Claude ecosystem compatibility.
- `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md` are mirrors or layered supplements for GitHub Copilot / Coding Agent; if they conflict with this file, `AGENTS.md` takes precedence.
- Repository collaboration skills are stored in `.claude/skills/`, and analysis artifacts in `.claude/reviews/`; the former can be committed, while the latter is treated as local output by default.
- The root `SKILL.md` and `docs/openclaw-skill-integration.md` are product or external integration documentation, not the source of truth for repository collaboration rules.
- If new `.agents/skills/` or other agent-specific directories are added in the future, first define a single source of truth, then sync via scripts or mirrors; prohibit maintaining multiple synonymous copies manually over the long term.
- When modifying AI collaboration governance assets, run:

```bash
python scripts/check_ai_assets.py
```

## 3. Repository Overview

- Project positioning: a stock intelligent analysis system covering A-shares, Hong Kong stocks, and US stocks.
- Main flow: fetch data -> technical analysis / news retrieval -> LLM analysis -> generate report -> notification push.
- Key entry points:
  - `main.py`: analysis task main entry
  - `server.py`: FastAPI service entry
  - `apps/dsa-web/`: Web frontend
  - `apps/dsa-desktop/`: Electron desktop app
  - `.github/workflows/`: CI, releases, daily tasks
- Core responsibilities:
  - `src/core/`: main flow orchestration
  - `src/services/`: business service layer
  - `src/repositories/`: data access layer
  - `src/reports/`: report generation
  - `src/schemas/`: Schema / data structures
  - `data_provider/`: multi-data-source adapters and fallback
  - `api/`: FastAPI API
  - `bot/`: bot integration
  - `scripts/`: local scripts
  - `.github/scripts/`: GitHub automation scripts
  - `tests/`: pytest tests
  - `docs/`: documentation

## 4. Common Commands

### Running the Application

```bash
python main.py
python main.py --debug
python main.py --dry-run
python main.py --stocks 600519,hk00700,AAPL
python main.py --market-review
python main.py --schedule
python main.py --serve
python main.py --serve-only
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Backend Verification

Preferred: run `./scripts/ci_gate.sh`

- Default: run flake8 / lint on changed files

### Web / Desktop

```bash
cd apps/dsa-web
npm ci
npm run lint
npm run build

cd ../dsa-desktop
npm install
npm run build
```

### PR / CI Evidence

```bash
gh pr view <pr_number>
gh pr checks <pr_number>
gh run view <run_id> --log-failed
```

## 5. Default Workflow

1. First determine the task type: `fix / feat / refactor / docs / chore / test / review`
2. Read the existing implementation, config, tests, scripts, workflows, and documentation before modifying.
3. Identify the change boundaries: backend / API / Web / Desktop / Workflow / Docs / AI collaboration assets.
4. First determine whether it hits a high-risk area: configuration semantics, API / Schema, data source fallback, report structure, authentication, scheduling, release process, desktop startup chain.
5. Make only the minimal changes directly related to the current task; do not sneak in unrelated refactoring.
6. If you find inconsistencies between docs, scripts, and workflow descriptions, trust the actual code and workflows, then decide whether to fix the docs in passing.
7. After making changes, run checks according to the verification matrix below.
8. The final delivery should by default explain:
   - What changed
   - Why it was changed this way
   - Verification status
   - Unverified items
   - Risk points
   - Rollback approach

## 6. Verification Matrix

### CI Coverage Principles

The current repository CI mainly includes:

| Check           | Source                                | Description                                                                                            | Blocking             |
| --------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------------------- |
| `ai-governance` | `.github/workflows/ci.yml`            | Validates the relationship among `AGENTS.md` / `CLAUDE.md` / `.github` instructions / `.claude/skills` | Yes                  |
| `backend-gate`  | `.github/workflows/ci.yml`            | Runs `./scripts/ci_gate.sh`                                                                            | Yes                  |
| `docker-build`  | `.github/workflows/ci.yml`            | Docker build and key module import smoke                                                               | Yes                  |
| `web-gate`      | `.github/workflows/ci.yml`            | Runs `npm run lint` + `npm run build` when frontend changes                                            | Yes (when triggered) |
| `network-smoke` | `.github/workflows/network-smoke.yml` | `pytest -m network` + `scripts/test.sh quick`                                                          | No, observational    |
| `pr-review`     | `.github/workflows/pr-review.yml`     | PR static checks + AI review + auto labeling                                                           | No, auxiliary        |

If the PR already has corresponding CI results, you can cite the CI conclusions directly; if CI does not cover the changed surface, or the local and CI environments differ greatly, you need to supplement local verification and gap notes.

### By Change Surface

- Python backend changes:
  - Scope: `main.py`, `src/`, `data_provider/`, `api/`, `bot/`, `tests/`
  - Default: run flake8 / lint on changed files
  - Minimum: `python -m py_compile <changed_python_files>`
  - If it affects the API, task orchestration, report generation, notification sending, data source fallback, authentication, or scheduling, the delivery notes must state whether the corresponding path was covered.

- Web frontend changes:
  - Scope: `apps/dsa-web/`
  - Default: `cd apps/dsa-web && npm ci && npm run lint && npm run build`
  - If it involves API integration, routing, state management, Markdown/chart rendering, or authentication state, the delivery notes must clearly explain the integration surface and unverified risks.

- Desktop changes:
  - Scope: `apps/dsa-desktop/`, `scripts/run-desktop.ps1`, `scripts/build-desktop*.ps1`, `scripts/build-*.sh`, `docs/desktop-package.md`
  - Default: build the Web first, then the desktop app
  - If full verification is not possible due to platform constraints, clearly state whether the Web build output, Electron build, and Release workflow impact were verified.

- API / Schema / Auth-linked changes:
  - Scope: `api/**`, `src/schemas/**`, `src/services/**`, `apps/dsa-web/**`, `apps/dsa-desktop/**`
  - At minimum cover the corresponding backend verification + affected client build verification.
  - If it involves login, cookies, sessions, polling state, field additions/removals, or enum changes, you must explicitly state the compatibility impact.

- Documentation and governance file changes:
  - Scope: `README.md`, `docs/**`, `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/**`, `.claude/skills/**`
  - Code tests are not required.
  - Confirm that commands, config items, filenames, and workflow names match the actual repository.
  - When changing AI collaboration governance assets, run `python scripts/check_ai_assets.py`.

- Workflow / script / Docker changes:
  - Scope: `.github/**`, `scripts/**`, `docker/**`
  - Run the local verification closest to the changed surface.
  - State in the delivery which pipeline, release path, or deployment path is affected.
  - If Docker / GitHub Actions verification was not run, clearly state why and the potential risks.

- Network or third-party dependency related changes:
  - First run offline or deterministic checks.
  - Prioritize confirming that timeout, retry, fallback, exception messages, and degradation paths still hold.
  - If online verification was not performed, you must clearly state why.

## 7. Stability Guardrails

- Config and run entry points:
  - When modifying `.env` semantics, defaults, CLI arguments, service startup methods, or scheduling semantics, evaluate the impact on local runs, Docker, GitHub Actions, API, Web, and Desktop together.
  - New config should preferably "run without configuration, enhance capabilities with configuration", avoiding stacking switches and mutually exclusive modes.

- Data sources and fallback:
  - When modifying `data_provider/`, pay attention to data source priority, failure degradation, field normalization, caching, and timeout strategies.
  - A single data source failure should not bring down the entire analysis flow, unless the requirement explicitly asks for fail-fast.

- API / Web / Desktop compatibility:
  - When changing API / Schema / auth / report payloads, check compatibility across backend, Web, and Desktop at the same time.
  - By default, prefer appending fields, keeping old fields, or providing a compatibility layer, to avoid silently breaking existing clients.

- Reports / Prompts / Notifications:
  - When modifying report structure, prompts, extractors, notification templates, or bot chains, check whether upstream inputs and downstream consumers remain compatible.
  - A single notification channel failure should not bring down the entire analysis main flow, unless the requirement explicitly asks for fail-fast.
  - When modifying `EXTRACT_PROMPT` in `src/services/image_stock_extractor.py`, include the complete latest prompt in the PR description.

- Workflows / Releases / Packaging:
  - When modifying auto-tagging, Releases, Docker publishing, daily analysis, or desktop packaging flows, evaluate trigger conditions, artifact paths, permission boundaries, and rollback approaches.
  - Auto-tagging remains opt-in by default: version number updates only trigger when a commit title contains `#patch`, `#minor`, or `#major`, unless the requirement explicitly changes the release policy.

## 8. Issue / PR / Skill Workflow

- The repository already has the following skills that can be reused:
  - `.claude/skills/analyze-issue/SKILL.md`
  - `.claude/skills/analyze-pr/SKILL.md`
  - `.claude/skills/fix-issue/SKILL.md`
- If the task is explicitly issue analysis, PR review, or issue fixing, follow the corresponding skill and save the artifacts to `.claude/reviews/`.
- The commands, templates, verification order, and delivery structure in the skills must stay consistent with `AGENTS.md`.
- Before every PR creation/update, PR review, or issue analysis, first sync the latest code baseline: check the workspace status and run `git fetch --all --prune`; if the workspace is clean and the current branch can fast-forward, run `git pull --ff-only`. If there are local changes, a conflict state, untracked risky files, or fast-forward is impossible, do not forcibly switch branches, stash, reset, or overwrite local state; PR review / issue analysis can instead be done against the already-fetched remote PR refs/head, and the reason for not updating the local working tree, the current local HEAD, and the remote baseline used must be clearly recorded in the analysis document; PR creation/update should first explain the difference between the current branch and the target baseline, and ask the user to confirm rebase, merge, or continue on the current branch when necessary.
- Skills should by default prioritize reading CI / workflow evidence before deciding whether to add local verification.
- Aside from the safe fast-forward sync above for PR creation/update and PR review / issue analysis, skills must not by default run operations that change the remote or current branch state, such as `git pull`, `git push`, `git tag`, or `gh pr create`; these operations require user confirmation.
- Default PR review order:
  1. Necessity
  2. Relevance
  3. Title suggestion (`<type>: <change>`, without tool/agent prefixes; not a hard blocker)
  4. Description completeness (against `.github/PULL_REQUEST_TEMPLATE.md`)
  5. Verification evidence
  6. Implementation correctness
  7. Merge decision
- For `fix`-type PRs, you must explain: the original problem, root cause, fix point, and regression risk.
- Merge blocking conditions:
  - Correctness or security issues
  - Blocking CI failed
  - PR description materially contradicts the actual changes
  - Missing rollback plan
  - Repeated unconverged contract drift, patch stacking, or distorted verification evidence

## 8.1 Review Feedback Handling and Patch-Stacking Prohibition

When handling review feedback, you are prohibited from merely appending a local patch at the location the reviewer pointed out and claiming "everything is fixed". You must first re-understand the business contract the reviewer identified, then check all the entry points, config, tests, docs, workflows, and user-visible paths involved in the same semantics.

After receiving review feedback, follow this order:

1. List the original issues the reviewer pointed out one by one.
2. Explain the root cause; do not describe only "which lines were changed".
3. Find all paths affected by the same semantics, such as runtime, API/Web, CLI, diagnostics, workflow, docs, and tests.
4. Fix the complete contract, not just the currently failing test or the current comment line.
5. Add regression tests that cover the reviewer's counterexamples, final entry-point verification, or clearly state the reason verification is not possible.
6. Update the PR body in parallel, ensuring scope, verification results, compatibility, risks, and rollback plan are consistent with the current head.

If you cannot complete the above convergence, do not continue stacking patches and do not claim ready for merge. Proactively state that the current PR needs to be split, closed and redone, or request the maintainer to confirm a new minimal scope.

The following behaviors are treated as low-quality PRs:

- Using broad fallbacks, silent degradation, or `return False/None/[]` to mask unclear contracts.
- Tests mocking out the real risk layer, only proving the local implementation passes.
- Claiming the issue is resolved after CI passes, without covering the counterexamples the reviewer pointed out.
- PR body inconsistent with the actual diff, verification results, or compatibility risks.
- Appending scattered patches after review instead of reconverging the complete semantics.
- The same business semantics behaving inconsistently across runtime, Web/API, docs, workflows, and tests.

CI passing only shows that automated checks passed; it cannot replace human semantic convergence, nor alone prove that the reviewer's counterexamples have been closed.

## 9. Delivery and Release

- Default delivery structure:
  - `What changed`
  - `Why it was changed this way`
  - `Verification status`
  - `Unverified items`
  - `Risk points`
  - `Rollback approach`
- For `docs` tasks, you can directly write `Docs only, tests not run`, but still state whether commands and filenames were verified.
- Auto-tagging is not triggered by default; version number updates only trigger when a commit title contains `#patch`, `#minor`, or `#major`.
- Manual tags must use annotated tags.
- User-visible changes should preferably be merged via PR, with labels and verification notes completed.
