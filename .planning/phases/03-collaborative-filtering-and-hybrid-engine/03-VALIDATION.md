---
phase: 3
slug: collaborative-filtering-and-hybrid-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8.0.0 + pytest-asyncio ≥0.24.0 |
| **Config file (backend)** | `backend/pyproject.toml` — `asyncio_mode = "auto"` |
| **Config file (worker)** | `worker/pytest.ini` — `asyncio_mode = auto` |
| **Quick run command (backend)** | `cd backend && pytest tests/ -x -q` |
| **Quick run command (worker)** | `cd worker && pytest tests/ -x -q` |
| **Full suite command** | `cd backend && pytest tests/ && cd ../worker && pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -x -q` (or `cd worker && pytest tests/ -x -q` for worker tasks)
- **After every plan wave:** Run `cd backend && pytest tests/ && cd ../worker && pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-W0-01 | 03-01 | 0 | DATA-03, API-03 | unit | `cd backend && pytest tests/test_feedback.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-02 | 03-01 | 0 | SEC-03 | integration | `cd backend && pytest tests/test_rate_limit.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-03 | 03-01 | 0 | API-07 | smoke | `cd backend && pytest tests/test_concurrency.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-04 | 03-02 | 0 | REC-03 | unit | `cd worker && pytest tests/test_cf_pipeline.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-05 | 03-02 | 0 | REC-04 | unit | `cd backend && pytest tests/test_recommendations.py::test_hybrid_blending -x` | ❌ W0 | ⬜ pending |
| 3-01-01 | 03-01 | 1 | DATA-03, API-03 | integration | `cd backend && pytest tests/test_feedback.py -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 03-01 | 1 | SEC-03 | integration | `cd backend && pytest tests/test_rate_limit.py -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 03-01 | 1 | API-07 | smoke | `cd backend && pytest tests/test_concurrency.py -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 03-02 | 2 | REC-03 | unit | `cd worker && pytest tests/test_cf_pipeline.py -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 03-02 | 2 | REC-04 | unit | `cd backend && pytest tests/test_recommendations.py -x` | ✅ (extend) | ⬜ pending |
| 3-03-01 | 03-03 | 3 | UI-05 | manual | N/A — browser test | manual-only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_feedback.py` — stubs for DATA-03, API-03
- [ ] `backend/tests/test_rate_limit.py` — stubs for SEC-03
- [ ] `backend/tests/test_concurrency.py` — stubs for API-07
- [ ] `worker/tests/test_cf_pipeline.py` — stubs for REC-03
- [ ] Extend `backend/tests/test_recommendations.py` — add stubs for REC-04 hybrid blending
- [ ] `backend/app/core/limiter.py` — defines `Limiter` instance (needed before feedback router and main.py can import it)
- [ ] `shared/config.py` — add `INTERACTIONS_COLLECTION = "interactions"` constant
- [ ] `backend/requirements.txt` — add `slowapi==0.1.9`

*Existing infrastructure: conftest.py, AsyncDatabase/AsyncCollection wrappers, seed_movies fixture, mongomock — all carry over from Phase 2.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Like/dislike buttons render below card | UI-05 | React component rendering | Open /recommendations, confirm thumbs up/down buttons visible below each card's explanation text |
| Clicking like highlights button | UI-05 | Visual state change | Click thumbs up — button should fill/highlight; click thumbs down — previous highlight clears, new one fills |
| Optimistic update (no reload) | UI-05 | UX behavior | After clicking, page should not reload; interaction state should persist on page |
| 429 message displayed in frontend | SEC-03 | Frontend error surface | Hit recommendation endpoint 11+ times/min — frontend should show retry-after message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
