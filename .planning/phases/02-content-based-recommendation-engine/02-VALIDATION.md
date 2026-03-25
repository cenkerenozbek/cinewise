---
phase: 2
slug: content-based-recommendation-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `backend/pyproject.toml` (`asyncio_mode = "auto"`) and `worker/pytest.ini` (`asyncio_mode = auto`) |
| **Quick run command** | `cd backend && pytest tests/test_recommendations.py -x -q` OR `cd worker && pytest tests/test_nlp_pipeline.py -x -q` |
| **Full suite command** | `cd backend && pytest -x -q && cd ../worker && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_recommendations.py -x -q` OR `cd worker && pytest tests/test_nlp_pipeline.py -x -q` (whichever is relevant to the task)
- **After every plan wave:** Run `cd backend && pytest -x -q && cd ../worker && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-NLP-01 | NLP pipeline | 0 | NLP-01 | unit | `cd worker && pytest tests/test_nlp_pipeline.py::test_preprocess_text -x` | ❌ W0 | ⬜ pending |
| 2-NLP-02 | NLP pipeline | 0 | NLP-02 | unit | `cd worker && pytest tests/test_nlp_pipeline.py::test_tfidf_vectorizer -x` | ❌ W0 | ⬜ pending |
| 2-NLP-03 | NLP pipeline | 0 | NLP-03 | unit | `cd worker && pytest tests/test_nlp_pipeline.py::test_similarity_index -x` | ❌ W0 | ⬜ pending |
| 2-NLP-04 | recommendations | 0 | NLP-04 | unit | `cd backend && pytest tests/test_recommendations.py::test_explanation_format -x` | ❌ W0 | ⬜ pending |
| 2-REC-01 | recommendations | 0 | REC-01 | unit | `cd backend && pytest tests/test_recommendations.py::test_returns_top_k -x` | ❌ W0 | ⬜ pending |
| 2-REC-02 | recommendations | 0 | REC-02 | integration | `cd backend && pytest tests/test_recommendations.py::test_different_genres_differ -x` | ❌ W0 | ⬜ pending |
| 2-REC-05 | recommendations | 0 | REC-05 | unit | `cd backend && pytest tests/test_recommendations.py::test_cold_start -x` | ❌ W0 | ⬜ pending |
| 2-UI-02 | UI onboarding | — | UI-02 | manual | N/A | — | ⬜ pending |
| 2-UI-04 | UI results | — | UI-04 | manual | N/A | — | ⬜ pending |
| 2-API-02 | recommendations | 0 | API-02 | integration | `cd backend && pytest tests/test_recommendations.py::test_endpoint_200 -x` | ❌ W0 | ⬜ pending |
| 2-API-05 | recommendations | 0 | API-05 | smoke | `cd backend && pytest tests/test_recommendations.py::test_response_time -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `worker/tests/test_nlp_pipeline.py` — stubs covering NLP-01, NLP-02, NLP-03
- [ ] `backend/tests/test_recommendations.py` — stubs covering REC-01, REC-02, REC-05, NLP-04, API-02, API-05
- [ ] `worker/requirements.txt` additions: `scikit-learn>=1.6.0`, `numpy>=2.0.0`, `scipy>=1.17.0`, `joblib>=1.3.0`
- [ ] `backend/requirements.txt` additions: `scikit-learn>=1.6.0`, `numpy>=2.0.0`, `joblib>=1.3.0`
- [ ] `docker-compose.yml` — add `nlp_artifacts` named volume shared by worker and backend
- [ ] `.env` addition: `ARTIFACTS_DIR=/artifacts`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Genre chips populated from `/movies/genres`; mood chips show exactly 5 options | UI-02 | React component rendering requires visual/browser verification | Open `/recommendations` page, verify genre chips match DB genres, verify 5 mood options (Happy, Tense, Relaxing, Mind-bending, Romantic) |
| Each recommendation card shows poster, title, year, summary, explanation text | UI-04 | Visual layout verification | Open `/recommendations` page with saved preferences, verify each card displays all 5 fields including explanation below card |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
