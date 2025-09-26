# Implementation Plan: Customer & Invoice Localisation + Printable Invoices & Core Management Modules

**Branch**: `003-customer-nsupport-only` | **Date**: 2025-09-25 | **Spec**: specs/003-customer-nsupport-only/spec.md
**Input**: Feature specification from `/specs/003-customer-nsupport-only/spec.md`

## Execution Flow (/plan command scope)

```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:

- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

Add customer management (Indian mobile validation, duplicate warning), inventory management, printable/downloadable INR-formatted invoices (HTML + PDF on-demand), and settings module (GST rate, branding). Ensure performance (validation p95 <300ms, PDF p95 <2s) and audit logging of invoice downloads.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy (async), Alembic, Pydantic, Axios, Next.js, Tailwind, PDF generation lib (We will evaluate: WeasyPrint vs. wkhtmltopdf vs. Playwright print-to-PDF; choose Playwright HTML print for fidelity & existing Chromium runtime)  
**Storage**: PostgreSQL (prod), SQLite for tests  
**Testing**: pytest (unit, integration, performance), frontend component/integration tests (future)  
**Target Platform**: Web application (backend API + Next.js frontend)  
**Project Type**: web  
**Performance Goals**: Validation <300ms p95; PDF generation <2s p95; duplicate warning lookup <50ms; audit logging overhead <50ms p95  
**Constraints**: Indian mobile format only; INR currency only; invoices immutable snapshots; on-demand PDF (no persistent files)  
**Scale/Scope**: Initial deployment (<50k customers, <200k invoices/year), moderate concurrency (<30 RPS API typical)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

**Quality Standards**:

- [x] Code quality standards: Pylint/ruff + black (backend); ESLint + prettier (frontend) – to reinforce consistency.
- [x] Linting and formatting tools specified (above) integrated in CI.
- [x] Code review: All PRs require 1 reviewer; tasks referencing requirement IDs in commit messages.

**Testing Requirements**:

- [x] TDD: Contract & integration tests authored before endpoint/service logic.
- [x] Coverage thresholds: backend retains ≥80% line, ≥90% for invoice/customer services.
- [x] Integration tests: One per acceptance scenario + duplicate warning + soft-deleted invoice download denial.

**User Experience**:

- [x] Consistent form patterns: shared field components (mobile, address) with inline validation.
- [x] Error handling: standardized API envelope already present; frontend interceptor unwraps; field-level messages map from validation codes.
- [x] Accessibility: WCAG 2.1 AA for printable/invoice views (semantic sections, aria labels for print buttons).

**Performance Benchmarks**:

- [x] Targets: validation 300ms p95; PDF 2s p95; duplicate lookup 50ms p95; audit log overhead 50ms p95.
- [x] Resource monitoring: metrics counters + duration histograms (existing observability config) with new labels (pdf_generate, invoice_download).
- [x] Regression strategy: performance tests (invoice creation already exists) + add PDF generation perf test.

**Observability**:

- [x] Metrics: Add counters/histograms for customer_create, duplicate_warning, pdf_generate, invoice_print.
- [x] Alerting: Configure threshold alerts (future ops doc) – placeholder; instrumentation delivered now.
- [x] Docs: Update `docs/api/invoices.md` and add `docs/api/customers.md` with metrics reference.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)

```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 2 (web application) – backend + frontend already present; extend existing directories.

## Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:

   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with decisions:

1. PDF Generation: Use Playwright (headless Chromium) print-to-PDF to leverage existing styling; fallback library evaluation documented.
2. Duplicate Mobile Lookup: Simple index scan on normalized mobile with case of exact 10-digit string; no fuzzy; add DB index.
3. INR Formatting: Use custom utility (already partial logic for numbers) – add Indian digit grouping function (2-2-3 pattern) server-side for PDF and rely on client formatting for UI.
4. Address Simplicity: Single line + city only; no pin code yet to reduce validation complexity.
5. Audit Logging: Use existing database table (create new `invoice_download_audit`); asynchronous insertion via background task to keep latency low.
6. Caching PDF: In-memory LRU (max 100 entries or 5 minutes TTL) – optional; flag in settings for enable/disable.

## Phase 1: Design & Contracts

_Prerequisites: research.md complete_

1. **Extract entities from feature spec** → `data-model.md`:

   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:

   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:

   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:

   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/\*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach

_This section describes what the /tasks command will do - DO NOT execute during /plan_

**Task Generation Strategy**:

- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P]
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:

- TDD order: Tests before implementation
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

_These phases are beyond the scope of the /plan command_

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

_Fill ONLY if Constitution Check has violations that must be justified_

| Violation                  | Why Needed         | Simpler Alternative Rejected Because |
| -------------------------- | ------------------ | ------------------------------------ |
| [e.g., 4th project]        | [current need]     | [why 3 projects insufficient]        |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient]  |

## Progress Tracking

_This checklist is updated during execution flow_

**Phase Status**:

- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---

_Based on Constitution v2.1.1 - See `/memory/constitution.md`_
