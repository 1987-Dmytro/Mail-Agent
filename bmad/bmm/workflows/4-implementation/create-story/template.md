# Story {{epic_num}}.{{story_num}}: {{story_title}}

Status: drafted

## Story

As a {{role}},
I want {{action}},
so that {{benefit}}.

## Acceptance Criteria

1. [Add acceptance criteria from epics/PRD]
2. [Add more acceptance criteria as needed]

### Standard Quality & Security Criteria (Auto-included)

These criteria apply to ALL stories unless explicitly not applicable:

- **Input Validation**: All user inputs and external data validated before processing (type checking, range validation, sanitization)
- **Security Review**: No hardcoded secrets, credentials in environment variables, parameterized queries for database operations, rate limiting implemented where applicable
- **Code Quality**: No deprecated APIs used, comprehensive type hints/annotations, structured logging for debugging, error handling with proper exception types

## Definition of Done (DoD)

Before marking this story as "review-ready", verify ALL items are complete:

- [ ] **All acceptance criteria implemented and verified**
  - Each AC has corresponding implementation
  - Manual verification completed for each AC

- [ ] **Unit tests implemented and passing (NOT stubs)**
  - Tests cover business logic for all AC
  - No placeholder tests with `pass` statements
  - Coverage target: 80%+ for new code

- [ ] **Integration tests implemented and passing (NOT stubs)**
  - Tests cover end-to-end workflows
  - Real database/API interactions (test environment)
  - No placeholder tests with `pass` statements

- [ ] **Documentation complete**
  - README sections updated if applicable
  - Architecture docs updated if new patterns introduced
  - API documentation generated/updated

- [ ] **Security review passed**
  - No hardcoded credentials or secrets
  - Input validation present for all user inputs
  - SQL queries parameterized (no string concatenation)

- [ ] **Code quality verified**
  - No deprecated APIs used
  - Type hints present (Python) or TypeScript types (JS/TS)
  - Structured logging implemented
  - Error handling comprehensive

- [ ] **All task checkboxes updated**
  - Completed tasks marked with [x]
  - File List section updated with created/modified files
  - Completion Notes added to Dev Agent Record

## Tasks / Subtasks

**IMPORTANT**: Follow new task ordering pattern from Epic 2 retrospective:
- Task 1: Core implementation + unit tests (interleaved, not separate)
- Task 2: Integration tests (implemented DURING development, not after)
- Task 3: Documentation + security review
- Task 4: Final validation

### Task 1: Core Implementation + Unit Tests (AC: #)

- [ ] **Subtask 1.1**: Implement core functionality
  - [ ] Create/modify necessary files
  - [ ] Implement business logic
- [ ] **Subtask 1.2**: Write unit tests for core functionality
  - [ ] Implement N unit test functions (specify exact count):
    1. `test_function_name_1` (AC: #)
    2. `test_function_name_2` (AC: #)
    [List all test functions to prevent stubs]
  - [ ] Verify all unit tests passing

### Task 2: Integration Tests (AC: #)

**Integration Test Scope**: Implement exactly N integration test functions (specify count):

- [ ] **Subtask 2.1**: Set up integration test infrastructure
  - [ ] Configure test database/environment
  - [ ] Create test fixtures and mocks
- [ ] **Subtask 2.2**: Implement integration test scenarios:
  - [ ] `test_integration_scenario_1` (AC: #) - [Brief description]
  - [ ] `test_integration_scenario_2` (AC: #) - [Brief description]
  - [ ] `test_integration_scenario_3` (AC: #) - [Brief description]
  [List ALL integration tests - NO stubs allowed]
- [ ] **Subtask 2.3**: Verify all integration tests passing

### Task 3: Documentation + Security Review (AC: #)

- [ ] **Subtask 3.1**: Update documentation
  - [ ] Update README if applicable
  - [ ] Update architecture docs if new patterns
  - [ ] Generate/update API documentation
- [ ] **Subtask 3.2**: Security review
  - [ ] Verify no hardcoded secrets (grep for credentials)
  - [ ] Verify input validation present
  - [ ] Verify database queries parameterized
  - [ ] Verify rate limiting implemented (if applicable)

### Task 4: Final Validation (AC: all)

- [ ] **Subtask 4.1**: Run complete test suite
  - [ ] All unit tests passing
  - [ ] All integration tests passing
  - [ ] No test warnings or errors
- [ ] **Subtask 4.2**: Verify DoD checklist
  - [ ] Review each DoD item above
  - [ ] Update all task checkboxes
  - [ ] Mark story as review-ready

## Dev Notes

- Relevant architecture patterns and constraints
- Source tree components to touch
- Testing standards summary

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- Detected conflicts or variances (with rationale)

### References

- Cite all technical details with source paths and sections, e.g. [Source: docs/<file>.md#Section]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
