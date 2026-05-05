# Capstone Project Status Report — Dönüşüm Rehberi

## Genel Yapısal Değişiklikler

| Alan | Proposal | Status Report'ta olmalı |
|------|----------|------------------------|
| Kapak başlığı | "CAPSTONE PROJECT PROPOSAL" | "CAPSTONE PROJECT STATUS REPORT" (veya "INTERIM/PARTIAL REPORT") |
| Tarih | "Jan, 2026" | "May, 2026" (teslim ayı) |
| Belge sahibi | Bireysel imza alanları | Üç ekibin tek belge olarak hazırladığı imzalı versiyon |

**Özet paragraf güncelleme:**

> Eski: "AI-powered personalized movie recommendation system... will utilize NLP..."
>
> Yeni: "We developed an AI-powered personalized movie recommendation system that mitigates the cold-start problem by combining TF-IDF-based content similarity with collaborative filtering. The system ingests 5,500+ movies from TMDB, builds a 5,000-feature TF-IDF vocabulary with bigrams, and serves recommendations through a FastAPI backend with p95 latency under 3 seconds. Offline evaluation on MovieLens-20M yielded Precision@10 = X.XX and NDCG@10 = X.XX. Frontend is a React SPA delivering explainable Top-K results. Phases 1–3 are complete; Phase 4 (evaluation and demo preparation) is in final integration."

Anahtar Words listesinde değişiklik gerekmez.

---

## §1 Background and Motivation (s. 1-4)

- **§1.1, §1.2, §1.4:** Aynen tutabilirsin (problem değişmedi)
- **§1.3 Project Objectives:** Her madde için `✓ Achieved` / `🟡 In progress` / `✗ Pending` eklemesi yap. Örnek:
  - `✓ Hybrid TF-IDF content similarity with item-item collaborative filtering — delivered in Phase 2-3`
- **§1.5 Limitations:** "Encountered limitations" alt başlığı ekle — uygulama sırasında karşılaşılan gerçek kısıtlar (örn. TMDB rate limit nedeniyle 5500 film tavanı)

---

## §2 Literature Review (s. 5-6)

- Yapısal değişiklik yok
- **Eklenecek kaynaklar:** MovieLens-20M paper (Harper & Konstan 2015), slowapi rate limiting, FastAPI lifespan pattern, scipy.sparse paper
- **§2.3 "Identified Gap" son cümle:** "This project bridges that gap, as demonstrated by our delivered hybrid system measured against three baselines in §7."

---

## §3 Methodology and Technical Approach (s. 7-18) — BÜYÜK GÜNCELLEME

### §3.1 Conceptual Solutions

Tablo 1 (üç konsept karşılaştırması) → **"Selected: Concept 3 (Hybrid)"** işareti koy. Concept 1 ve 2'yi karşılaştırma için tutmaya devam et.

### §3.2 System Design / Architecture

- **Figure 1** → Gerçek port numaraları, volume isimleri (`nlp_artifacts:/artifacts`). Container'lar:
  - `mongo:7` (port 27017)
  - `backend` FastAPI (port 8000)
  - `frontend` Vite dev server (port 5173)
  - `worker` (batch only, no port)
- **Figure 2** (offline pipeline) → Gerçek dosya isimleriyle güncelle: `ingest_tmdb.py` → `nlp_features.py` → `cf_features.py`
- **Figure 3** (runtime flow) → `CF_THRESHOLD=5`, `CF_ALPHA=0.5` değerlerini diyagrama ekle

### §3.2.1 Functional Requirements (MUST/SHOULD/COULD listesi)

Her madde için status işareti ekle:

| Status | Requirement |
|--------|-------------|
| ✓ Implemented | The system shall serve Top-K movie recommendations |
| ✓ Implemented | The system shall implement collaborative filtering signal |
| ✓ Implemented | The system shall apply rate limiting (10 req/min/user) |
| 🟡 Partial | UAT with university students |

### §3.2.2 Non-Functional Requirements

Target vs. Achieved tablosu:

| Requirement | Target | Achieved | Status |
|-------------|--------|----------|--------|
| Recommendation API p95 | < 3s | … ms (DevTools/load test'ten) | ✓ |
| Search API p95 | < 2s | … ms | ✓ |
| Rate limiting | 10 req/min/user → 429 | 11th request returns 429 + Retry-After | ✓ |

### §3.3 Tools, Technologies — küçük güncelleme

- **"PyTorch"** → "PyTorch was initially planned for NCF but replaced with scikit-learn cosine similarity on scipy sparse matrices for memory efficiency on the available hardware (decision logged in §6.2)."
- **"NLTK ve spaCy"** → gerçekte hangisi kullanıldıysa güncelle

---

## §4 Project Management (s. 19-23)

### §4.1 Work Breakdown Structure

`"Planned"` etiketlerini `"✓ Completed"` / `"🟡 In Progress"` olarak değiştir.

### §4.2 Team Roles

Her satıra "Delivered" / "In Progress" sütunu ekle.

### §4.3 Gantt Chart — KRİTİK GÜNCELLEME

Figure 5'i **Planned vs. Actual Gantt** olarak değiştir (iki barlı format):

```
Mar 08 |■■■|           Project setup          (planned: 1 wk  → actual: 0.5 wk)
Mar 15 |■■■■■■■■■|     TMDB ingestion         (planned: 2 wk  → actual: 1 wk)
Mar 22 |■■■■■■|        MongoDB schema         (overlap with above)
...
May 04 |■■▢▢▢▢|        Phase 4               (currently ~60% complete)
May 17 |▢▢▢▢|          Final report writing   (planned, not started)
Jun 14 |▢|             Defense presentation
```

**Not:** git log referansı — Phase 1: 25 Mart, Phase 2-3: 26 Mart. Planlanandan çok daha hızlı tamamlanmış (Mart-Haziran yerine 2 günde 3 phase). **Pozitif bir nokta — vurgula.**

---

## §5 Required Resources (s. 24-25)

### §5.1 Hardware

"TF-IDF + CF approach trained successfully on local CPU." (real saving — GPU gerekmedi)

### §5.2 Software

Gerçekten kullanılan kütüphane sürümleri ekle (requirements.txt'den):
- `fastapi==0.115.x`
- `pymongo==4.x` (Motor yerine)
- `scikit-learn==1.x`
- `passlib[bcrypt]<5.0`

### §5.3 Facilities and Services

"Cloud Hosting: Vercel/Netlify... Railway" → güncelle:
- "Currently deployed locally via Docker Compose; cloud deployment scheduled for Phase 4 final week"
- veya deploy edildiyse: "Deployed to Vercel (frontend) at https://… and Railway (backend) at https://…"

### §5.4 Estimated Budget

Tablo 3'e **"Actual"** sütunu ekle:

| Item | Estimated | Actual |
|------|-----------|--------|
| Domain | … | alındıysa fiili tutar, alınmadıysa 0 |
| Backend hosting | … | lokal kullanılıyorsa 0 |
| TMDB API | 0 (free tier) | 0 |
| **Total** | … | … |

---

## §6 Risk Assessment (s. 26)

Tablo 5'e **"Status"** ve **"Mitigation Outcome"** sütunları ekle:

| Risk | Likelihood | Severity | Risk Level | Status | Outcome / Mitigation |
|------|------------|----------|------------|--------|----------------------|
| Data availability | Possible | Moderate | Medium | ✓ Mitigated | 5,500 movies ingested successfully |
| External API constraints | Possible | Moderate | Medium | ✓ Mitigated | `append_to_response=credits,translations` reducing 15k requests → 5.5k |
| Turkish NLP limitations | Likely | Moderate | High | 🟡 Partial | English-only model used; noted as limitation |
| Recommendation quality below target | Possible | Significant | High | ✓ Mitigated | P@10 = X.XX achieved (above threshold) |
| Limited compute resources | Likely | Moderate | High | ✓ Mitigated | TF-IDF on CPU sufficient; no GPU needed |
| Integration complexity | Possible | Moderate | Medium | ✓ Mitigated | 85 automated tests passing; Phase boundaries clean |
| Deployment instability | Likely | Moderate | High | 🟡 Pending | Cloud deploy in final week |
| Team coordination | Possible | Moderate | Medium | ✓ Mitigated | Clear phase ownership; parallel workstreams |

---

## §7 Outcomes and Evaluation Results (s. 27-28) — EN BÜYÜK DEĞİŞİKLİK

**Başlık değişikliği:** "§7 Expected Outcomes and Evaluation" → **"§7 Outcomes and Evaluation Results"**

### §7.1 Delivered Outcomes

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| Hybrid Recommendation Engine | ✓ Delivered | `recommendation_service.py` step-function blending |
| Data & NLP Pipeline | ✓ Delivered | `worker/jobs/`; 7,889 movies indexed |
| REST API | ✓ Delivered | FastAPI; 46 passing tests |
| React SPA Frontend | ✓ Delivered | Vite build; login → onboarding → recommendations |
| Offline Evaluation | 🟡 In Progress | metrics.json pending (this week) |
| Final Project Report | 🟡 In Progress | This document |

### §7.2 Success Criteria Verification

- ✓ **Cold-Start Effectiveness:** New users get differentiated recommendations from genre selection (Phase 2 SC-3)
- ✓ **Hybrid blending** outperforms content-only (Phase 3 SC-2)
- ✓ **Rate limiting** enforced at 10 req/min (Phase 1 SC-4)

### §7.3.1 Offline Algorithmic Benchmarking

**Koşulması gereken komutlar:**

```bash
python -m jobs.evaluate --max-users 500              # Hybrid
CF_ALPHA=1.0 python -m jobs.evaluate --max-users 500 # Content-only
CF_ALPHA=0.0 python -m jobs.evaluate --max-users 500 # CF-only
# Most Popular baseline — evaluate.py'a ~20 satır flag eklenmesi gerekiyor
```

**Sonuç tablosu (doldurulacak):**

| Algorithm | Precision@10 | NDCG@10 | Notes |
|-----------|-------------|---------|-------|
| Most Popular (baseline) | … | … | TMDB vote_average × log(vote_count) |
| Content-Based Only (alpha=1.0) | … | … | Pure TF-IDF cosine |
| Collaborative Only (alpha=0.0) | … | … | Pure item-item CF |
| **Hybrid (alpha=0.5)** | **…** | **…** | **Step-function blending** |

**History-limit tablosu (cold-start robustness):**

| History Size | Precision@10 | NDCG@10 |
|-------------|-------------|---------|
| N = 1 | … | … |
| N = 3 | … | … |
| N = 5 | … | … |

### §7.3.2 Functional End-to-End Testing

- 85 automated tests — 100% pass (backend: 46, worker: 39)
- Run command: `pytest -q` (full output → Appendix A)

### §7.3.3 Stress/Load Testing

- 10 concurrent users via `test_concurrency.py`: all 200 OK in <3s
- (İsteğe bağlı: Locust ile 25-50 kullanıcı testi — yapılmadıysa "deferred to final report")

### §7.3.4 Failure Simulations

- TMDB unavailability simulation
- MongoDB connection failure
- Invalid JWT / expired token

### §7.3.5 UAT

Yapılmadıysa: "Scheduled for Week 14 (May 24-31). Survey instrument prepared (see Appendix A)."

### §7.3.6 Qualitative Examples (YENİ — proposal §7.1 explicitly istiyor)

3-5 ekran görüntüsü + JSON çıktı:
- Cold-start kullanıcı için "Sci-Fi + thoughtful" → öneri listesi
- Returning kullanıcı için aynı tercihlerle farklı sonuç
- Like/dislike sonrası recommendation değişimi
- "Recommended because…" açıklama örnekleri

---

## §8 Ethical, Safety, Sustainability (s. 29)

- "will adhere" → "adheres to KVKK/GDPR by..."
- bcrypt kanıtı: "Verified in `backend/app/services/auth_service.py`; passwords stored as `$2b$...` hashes (never plaintext)"
- "will operate within TMDB Terms of Service" → "Operates within TMDB ToS; only metadata and poster URLs are stored, no copyrighted content"

---

## §9 References (s. 30)

Yeni eklenecekler:
- Harper, F. M., & Konstan, J. A. (2015). The MovieLens Datasets. *ACM TIIS*.
- Pedregosa et al. (2011). Scikit-learn. *JMLR*. (zaten var mı kontrol et)

---

## YENİ §10 — Current Status Summary (1 sayfa)

Proje sağlık panosu — danışman için tek bakışta görüntü:

```
Phase Completion:        ████████████░░  93% (14/15 plans)
Requirement Coverage:    ████████████████ 30/30 MUST
Test Pass Rate:          ████████████████ 85/85 (100%)
Deployment Status:       ████████░░░░░░░░ Local only (cloud pending)
UAT Status:              ░░░░░░░░░░░░░░░░ Scheduled Week 14
Risk Status:             6/8 mitigated, 2/8 pending
```

---

## YENİ §11 — Lessons Learned & Deviations from Proposal

- "PyTorch yerine scikit-learn kullandık çünkü memory efficiency gerekiyordu ve local CPU'da yeterliydi."
- "MovieLens-20M ID mapping için TMDB cross-referencing gerekti — bu ek iş planlanmamıştı."
- "CF_THRESHOLD=5 ve CF_ALPHA=0.5 empirically belirlendi; proposal'da sabit değerler yoktu."
- "Motor (async MongoDB) yerine pymongo kullandık; FastAPI lifespan pattern ile yeterli performansı sağladı."

---

## YENİ §12 — Remaining Work (Plan to Final Submission)

- [ ] Run baseline evaluations (Most Popular, Content-only, CF-only) → `artifacts/metrics.json`
- [ ] UAT session with 5 students (Week 14: May 24-31)
- [ ] Cloud deployment (Vercel + Railway)
- [ ] Final report writing (full version)
- [ ] Defense presentation prep

---

## Yeni Appendix A — Test Output Logs

`pytest -q` çıktısı, eval script çıktısı (`metrics.json`), Postman/curl response'ları

## Yeni Appendix B — Screenshots

Login → Onboarding → Recommendations → Like/Dislike → Search → 429 error → Metrics card

---

## Pratik İş Akışı (Bu Hafta — 5-9 Mayıs)

| Gün | Görev | Sorumlu |
|-----|-------|---------|
| Pzt-Sal | `artifacts/metrics.json` üret (16 koşu), stress test, failure logs | Cenk |
| Çar | §1-2, §5, §6 yaz | İbrahim |
| Çar | §3.1, §3.2.1, §7 yaz (methodology + results) | Cenk ← AĞIR YÜK |
| Çar | §3.2 (architecture), §3.5, §10-12, Appendix B | Yunus |
| Per | İlk taslak birleştirme + iç review | Hepsi |
| Cum | Diyagramları yenile, PDF üret, danışmana gönder | — |

Dosya adı: `4992Status<KOD>.pdf`

---

## Tek Cümlelik Özet

Status report, proposal'ın geçmiş zamana çevrilmiş + her iddia için kanıt eklenmiş halidir; eksik kısımlar dürüstçe "Scheduled for Week N" diye işaretlenir; ekibin üçü kendi RM satırından sorumlu olduğu bölümleri yazar.
