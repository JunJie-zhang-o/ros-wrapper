# Task Plan: Lightweight ROS Wrapper (ROS1/ROS2)

## Goal
Build a lightweight Python `ros_wrapper` package managed by `pdm` that isolates ROS1 vs ROS2 differences via two usage modes: (1) abstract factory methods returning concrete ROS entities, and (2) decorators that inject native ROS entities and attach `ros_meta` for static inspection.

## Current Phase
Complete

## Phases
### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify constraints and requirements
- [x] Document findings in findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Define technical approach
- [x] Create project structure for `pdm` and non-`src` layout
- [x] Document decisions with rationale
- **Status:** complete

### Phase 3: Implementation
- [x] Implement ROS backend abstraction for ROS1/ROS2
- [x] Implement mode 1 factory APIs for pub/sub/service/action
- [x] Implement mode 2 decorators + `ros_meta`
- [x] Add examples and docs
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Run syntax/import checks
- [x] Validate metadata behavior in decorator mode
- [x] Verify docs match implemented API
- **Status:** complete

### Phase 5: Delivery
- [x] Review output files
- [x] Summarize architecture and ROS1/ROS2 custom type differences
- [x] Deliver usage notes and next steps
- **Status:** complete

## Key Questions
1. How to keep wrapper usable without forcing ROS runtime imports during package import time?
2. How to represent decorator metadata for static/introspective use in a stable schema?
3. What are the most important ROS1/ROS2 differences for custom msg/srv/action definitions?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use lazy imports in backend adapters | Avoid import-time failures when target ROS runtime is unavailable |
| Keep package layout as `ros_wrapper/` at repo root | Matches user requirement: no `src/` layout |
| Use `pdm` dynamic version from package file | User要求动态使用库中版本信息 |
| Expose two clear modes in one facade (`RosWrapper`) | Keep business code unified while backend differences stay in adapters |
| Infer `Service/Action` injection role from function signature | Satisfies `client/server` automatic behavior requirement |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `python: command not found` | 1 | Switched all validation commands to `python3` |
| `No module named pytest` | 1 | Performed inline assertion-based self-check via `python3` |

## Notes
- Update phase status as progress changes.
- Keep docs explicit about ROS not installed vs installed behavior.

## Session: 2026-03-10 ServiceClient Compatibility Update

### Phase 1: Diff Review
- [x] Inspect current `git diff` and locate unified client implementation
- [x] Confirm missing `ServiceClient.call_async` cross-version API
- **Status:** complete

### Phase 2: Implementation
- [x] Add `ServiceClient.call_async` for ROS1/ROS2
- [x] Refactor `ServiceClient.call` to reuse `call_async`
- [x] Keep timeout semantics explicit for ROS2 blocking waits
- [x] Add `ActionClient.call` / `ActionClient.call_async` aliases for ROS1/ROS2 unified invocation
- **Status:** complete

### Phase 3: Type Hinting
- [x] Add `ros_wrapper/clients.pyi` for IDE/static hint support
- **Status:** complete

### Phase 4: Verification
- [x] Run compile check for package and tests
- [x] Run executable self-check script for `call`/`call_async` behavior
- [ ] Run `pytest` (blocked by missing dependency)
- **Status:** complete
