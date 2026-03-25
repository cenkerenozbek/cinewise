---
phase: 1
slug: foundation-and-data-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ~8.x + pytest-asyncio ~0.24+ (backend/worker), vitest ~3.x (frontend) |
| **Config file** | `backend/pyproject.toml` (Wave 0), `frontend/vitest.config.ts` (Wave 0) |
| **Quick run command** | `cd backend && pytest tests/ -x --timeout=30` |
| **Full suite command** | `cd backend && pytest tests/ -v && cd ../worker && pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `cd backend && pytest tests/ -v && cd ../worker && pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-01 | unit | `pytest worker/tests/test_pipeline.py::test_transform_movie -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | DATA-02 | unit | `pytest worker/tests/test_pipeline.py::test_turkish_title -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | DATA-04 | unit | `pytest worker/tests/test_pipeline.py::test_missing_fields -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | DATA-05 | integration | `pytest worker/tests/test_pipeline.py::test_ingestion_e2e -x` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 1 | DATA-06 | manual-only | Manual timing of full ingestion run | N/A | ⬜ pending |
| 01-02-01 | 02 | 1 | API-04 | unit | `pytest worker/tests/test_pipeline.py::test_retry_on_failure -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | SEC-02 | unit | `pytest backend/tests/test_auth.py::test_password_hashing -x` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 1 | UI-01 | e2e | Manual or Playwright (future) | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | API-01 | unit | `pytest backend/tests/test_movies.py -x` | ❌ W0 | ⬜ pending |
| 01-04-02 | 04 | 1 | API-06 | integration | `pytest backend/tests/test_movies.py::test_search_performance -x` | ❌ W0 | ⬜ pending |
| 01-04-03 | 04 | 1 | SEC-01 | integration | `pytest backend/tests/test_movies.py::test_persistence -x` | ❌ W0 | ⬜ pending |
| 01-05-01 | 05 | 2 | UI-03 | e2e | Manual or Playwright (future) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pyproject.toml` — pytest configuration with asyncio mode
- [ ] `backend/tests/conftest.py` — shared fixtures (test DB, test client, mock TMDB)
- [ ] `backend/tests/test_auth.py` — covers SEC-02, UI-01 API side
- [ ] `backend/tests/test_movies.py` — covers API-01, API-06, SEC-01
- [ ] `worker/tests/conftest.py` — shared fixtures (mock TMDB responses, test DB)
- [ ] `worker/tests/test_pipeline.py` — covers DATA-01, DATA-02, DATA-04, DATA-05, API-04
- [ ] `frontend/vitest.config.ts` — vitest configuration
- [ ] Framework installs: `pip install pytest pytest-asyncio` (backend/worker), `npm install -D vitest` (frontend)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pipeline completes within 2h | DATA-06 | Requires full TMDB ingestion run with real API | Run `python -m worker.jobs.ingest` and verify wall-clock time < 2h |
| User registration & login flow | UI-01 | Full E2E through React UI | Register new user, login, verify redirect to home |
| Search with genre/year filters | UI-03 | Full E2E through React UI | Search "Inception", filter by Sci-Fi, filter by 2010, verify results |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
