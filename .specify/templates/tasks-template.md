# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)

```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 3.1: Setup & Quality Gates

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools (required by constitution)
- [ ] T004 [P] Configure code coverage tools (80% line, 90% critical path required)
- [ ] T005 [P] Set up performance monitoring and benchmarking tools

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

- [ ] T006 [P] Contract test POST /api/users in tests/contract/test_users_post.py
- [ ] T007 [P] Contract test GET /api/users/{id} in tests/contract/test_users_get.py
- [ ] T008 [P] Integration test user registration in tests/integration/test_registration.py
- [ ] T009 [P] Integration test auth flow in tests/integration/test_auth.py
- [ ] T010 [P] Performance test API response times (<200ms p95) in tests/performance/
- [ ] T011 [P] Accessibility test UI components in tests/accessibility/

## Phase 3.3: Core Implementation (ONLY after tests are failing)

- [ ] T012 [P] User model in src/models/user.py
- [ ] T013 [P] UserService CRUD in src/services/user_service.py
- [ ] T014 [P] CLI --create-user in src/cli/user_commands.py
- [ ] T015 POST /api/users endpoint with <200ms response time
- [ ] T016 GET /api/users/{id} endpoint with <200ms response time
- [ ] T017 Input validation with user-friendly error messages
- [ ] T018 Error handling and structured logging (observability requirement)

## Phase 3.4: Integration & Observability

- [ ] T019 Connect UserService to DB with connection monitoring
- [ ] T020 Auth middleware with security logging
- [ ] T021 Request/response logging with metrics collection
- [ ] T022 CORS and security headers
- [ ] T023 [P] Monitoring dashboards for system health
- [ ] T024 [P] Alert configuration for performance degradation

## Phase 3.5: Quality Assurance & Polish

- [ ] T025 [P] Unit tests for validation in tests/unit/test_validation.py
- [ ] T026 [P] Code quality review and refactoring
- [ ] T027 [P] Performance optimization to meet benchmarks
- [ ] T028 [P] Accessibility compliance verification
- [ ] T029 [P] Update documentation with API specs and usage examples
- [ ] T030 [P] User experience testing and feedback integration
- [ ] T031 Run complete test suite and verify coverage thresholds
- [ ] T032 Final constitutional compliance audit

## Dependencies

- Setup & Quality Gates (T001-T005) before everything
- Tests (T006-T011) before implementation (T012-T018)
- T012 blocks T013, T019
- T020 blocks T022
- Implementation before integration (T012-T018 before T019-T024)
- Integration before QA (T019-T024 before T025-T032)

## Parallel Example

```
# Launch T006-T011 together (constitutional test requirements):
Task: "Contract test POST /api/users in tests/contract/test_users_post.py"
Task: "Contract test GET /api/users/{id} in tests/contract/test_users_get.py"
Task: "Integration test registration in tests/integration/test_registration.py"
Task: "Integration test auth in tests/integration/test_auth.py"
Task: "Performance test API response times (<200ms p95) in tests/performance/"
Task: "Accessibility test UI components in tests/accessibility/"
```

## Notes

- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts

## Task Generation Rules

_Applied during main() execution_

1. **From Contracts**:
   - Each contract file → contract test task [P]
   - Each endpoint → implementation task
2. **From Data Model**:
   - Each entity → model creation task [P]
   - Relationships → service layer tasks
3. **From User Stories**:

   - Each story → integration test [P]
   - Quickstart scenarios → validation tasks

4. **Ordering**:
   - Setup → Tests → Models → Services → Endpoints → Polish
   - Dependencies block parallel execution

## Validation Checklist

_GATE: Checked by main() before returning_

- [ ] All contracts have corresponding tests
- [ ] All entities have model tasks
- [ ] All tests come before implementation
- [ ] Constitutional requirements addressed:
  - [ ] Code quality and linting tasks included
  - [ ] Test coverage requirements specified (80% line, 90% critical path)
  - [ ] Performance benchmark tasks included (<200ms API, <100ms UI)
  - [ ] User experience consistency tasks included
  - [ ] Observability tasks included (logging, monitoring, metrics)
  - [ ] Accessibility testing tasks included
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task
