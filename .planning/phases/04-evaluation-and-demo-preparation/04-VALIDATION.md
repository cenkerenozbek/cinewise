---
phase: 4
slug: evaluation-and-demo-preparation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (already configured) |
| **Config file (backend)** | `backend/pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| **Config file (worker)** | `worker/pytest.ini` — `asyncio_mode = auto`, `testpaths = tests` |
| **Quick run command** | `cd backend && python -m pytest tests/test_recommendations.py tests/test_metrics.py -x && cd ../worker && python -m pytest tests/test_eval_pipeline.py -x` |
| **Full suite command** | `cd backend && python -m pytest -q && cd ../worker && python -m pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_recommendations.py -x -q && cd ../worker && python -m pytest tests/test_eval_pipeline.py -x -q`
- **After every plan wave:** Run full suite `cd backend && python -m pytest -q && cd ../worker && python -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| genre_fallback | 01 | 1 | cold-start genre fallback | unit | `cd backend && python -m pytest tests/test_recommendations.py::test_genre_fallback_returns_results -x` | ❌ Wave 0 | ⬜ pending |
| no_cf_artifact | 01 | 1 | cold-start no CF artifact | unit | `cd backend && python -m pytest tests/test_recommendations.py::test_no_cf_artifact_falls_back -x` | ✅ exists | ⬜ pending |
| obscure_movie | 01 | 1 | cold-start obscure movie | unit | `cd backend && python -m pytest tests/test_recommendations.py::test_obscure_movie_no_cf_neighbors -x` | ❌ Wave 0 | ⬜ pending |
| metrics_200 | 02 | 1 | GET /api/metrics with data | unit | `cd backend && python -m pytest tests/test_metrics.py::test_metrics_returns_200 -x` | ❌ Wave 0 | ⬜ pending |
| metrics_404 | 02 | 1 | GET /api/metrics no data | unit | `cd backend && python -m pytest tests/test_metrics.py::test_metrics_returns_404 -x` | ❌ Wave 0 | ⬜ pending |
| loo_split | 03 | 2 | leave-one-out split logic | unit | `cd worker && python -m pytest tests/test_eval_pipeline.py::test_leave_one_out_split -x` | ❌ Wave 0 | ⬜ pending |
| precision_at_k | 03 | 2 | Precision@K computation | unit | `cd worker && python -m pytest tests/test_eval_pipeline.py::test_precision_at_k -x` | ❌ Wave 0 | ⬜ pending |
| ndcg_at_k | 03 | 2 | NDCG@K computation | unit | `cd worker && python -m pytest tests/test_eval_pipeline.py::test_ndcg_at_k -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_metrics.py` — stubs for GET /api/metrics 200 and 404 cases
- [ ] `backend/tests/test_recommendations.py::test_genre_fallback_returns_results` — new test in existing file
- [ ] `backend/tests/test_recommendations.py::test_obscure_movie_no_cf_neighbors` — new test in existing file
- [ ] `worker/tests/test_eval_pipeline.py` — covers leave-one-out split, precision@k, ndcg@k

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UAT session (5 university students) | Phase 4 SC-2 | Requires real human testers | Provide demo URL; record crashes/errors; confirm 5 sessions complete without crash |
| Full demo walkthrough | Phase 4 SC-4 | End-to-end human flow | Register user, select preferences, view recommendations, like/dislike, log out, log back in — confirm no manual intervention required |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
