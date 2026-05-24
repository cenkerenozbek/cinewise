# CineWise — Öneri Sistemi Teknik Dokümantasyonu

> **Versiyon:** v2.0 (Mayıs 2026)
> **Proje:** BAU Bilgisayar Mühendisliği Capstone
> **Ekip:** Cenk Eren Özbek · İbrahim Halil Demircioğlu · Yunus Emre Aydın
> **Danışman:** Dr. Burak Çatalbaş

---

## İçindekiler

1. [Sistem Genel Bakış](#1-sistem-genel-bakış)
2. [Orijinal Sistem (v1.0)](#2-orijinal-sistem-v10)
3. [Yükseltilmiş Sistem (v2.0)](#3-yükseltilmiş-sistem-v20)
4. [Değişiklik Karşılaştırması](#4-değişiklik-karşılaştırması)
5. [Veri Akışı ve Mimari](#5-veri-akışı-ve-mimari)
6. [Değerlendirme Çerçevesi](#6-değerlendirme-çerçevesi)
7. [Artifacts ve Dosya Yapısı](#7-artifacts-ve-dosya-yapısı)
8. [API Referansı](#8-api-referansı)
9. [Çalıştırma Talimatları](#9-çalıştırma-talimatları)
10. [Beklenen Metrik İyileşmesi](#10-beklenen-metrik-i̇yileşmesi)

---

## 1. Sistem Genel Bakış

CineWise, soğuk başlangıç (cold-start) sorununu çözen hibrit bir film öneri sistemidir. Kullanıcı etkileşim geçmişi yokken içerik tabanlı semantik benzerlik, etkileşim sayısı arttıkça iş birlikçi filtreleme (CF) ağırlığı kullanır.

**Temel Özellikler:**
- 5.500+ TMDB filmi indekslenmiş
- Soğuk başlangıç: tür + mood tercihine göre semantik öneri
- Kademeli kişiselleştirme: sigmoid alpha ile yumuşak CF geçişi
- Açıklanabilir sonuçlar: "Recommended because you like Action, feeling Tense."
- Çevrimdışı/çevrimiçi ayrım: worker toplu işler, FastAPI servis eder

---

## 2. Orijinal Sistem (v1.0)

### 2.1 İçerik Modeli — TF-IDF

```python
TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 2),   # unigramlar + bigramlar
    stop_words="english",
    sublinear_tf=True,
    min_df=2,
)
```

**Metin oluşturma:** Her film için `overview + genres + cast×2 + director×2` birleştirilir.
Benzerlik: Seyrek TF-IDF matrisinde satır bazlı cosine similarity → top-50 komşu.

**Artifact:** `similarity_index.joblib` → `{tmdb_ids, top_indices: (N, 50)}`
Vektörizer: `tfidf_vectorizer.joblib` (runtime'da kullanılmıyordu)

### 2.2 İş Birlikçi Filtreleme — Item-Item Cosine

```
Kullanıcı-film matrisi (like=+1, dislike=−1)
    → Seyrek matrisin transpozunu al (film-kullanıcı)
    → Satır bazlı cosine similarity
    → top-50 CF komşusu
```

**Artifact:** `cf_index.joblib` → `{tmdb_ids, cf_top_indices: (N, 50)}`

### 2.3 Hybrid Blending — Step Function

```python
def _get_alpha(n_interactions, cf_threshold=5, cf_alpha=0.5):
    return cf_alpha if n_interactions >= cf_threshold else 1.0
```

| Etkileşim | Alpha (içerik ağırlığı) |
|-----------|------------------------|
| < 5       | 1.0 (saf içerik)        |
| ≥ 5       | 0.5 (50/50 blend)       |

**Skor hesabı (frekans sayımı):**
```python
for neighbor_idx in top_indices[seed_idx]:
    candidate_scores[neighbor_id] += 1.0   # her komşuya +1
```

### 2.4 Değerlendirme — v1.0

**Metrikler:**
- `precision_at_10` (yanlış isim — aslında Hit Rate@10)
- `ndcg_at_10`

**Yöntem:** Leave-one-out (en son beğeni tutulur)
**Veri:** MovieLens-20M seed kullanıcıları (≥5 beğeni şartı)

**Değerlendirme komutları:**
```bash
python worker/jobs/evaluate.py --max-users 500
python worker/jobs/evaluate.py --max-users 500 --history-limit 1
python worker/jobs/evaluate.py --max-users 500 --history-limit 3
python worker/jobs/evaluate.py --max-users 500 --history-limit 5
```

**Tahmini v1.0 sonuçları:** HR@10 ≈ %14 · rastgeleden ~70x daha iyi

**Sorun:** Hoca bu relatif ifadeyi anlamlı bulmadı — baselines eksik, isim yanlış, metrik sayısı yetersiz.

---

## 3. Yükseltilmiş Sistem (v2.0)

### 3.1 İçerik Modeli — Sentence Transformers

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(texts, batch_size=64, normalize_embeddings=True)
# shape: (N, 384) — L2-normalize edilmiş float32
```

**L2-normalizasyon sayesinde** cosine similarity = dot product:
```python
sims = (embeddings @ embeddings[i]).astype(np.float64)
```

**`all-MiniLM-L6-v2` neden seçildi:**
- 22 MB — CPU'da hızlı
- 384 boyutlu semantik uzay
- Kelime örtüşmesi olmadan anlamsal benzerliği yakalar
  - "gerilimli macera" ≈ "heyecanlı aksiyon" (TF-IDF'de yakalanamaz)
- Çok dilli desteği var (Türkçe filmler için de çalışır)

**Artifact:** `similarity_index.joblib` → `{tmdb_ids, top_indices: (N, 100), top_scores: (N, 100)}`
`top_n` 50 → **100** (niche filmler için daha geniş kapsam)
`top_scores`: gerçek cosine değerleri kaydedilir (ağırlıklı scoring için)

### 3.2 İş Birlikçi Filtreleme — SVD Latent Factors

```python
from scipy.sparse.linalg import svds

# k = min(50, min(N_users, N_movies) - 1)
U, sigma, Vt = svds(user_item.astype(np.float64), k=50)

# Film latent faktörleri (tekil değerlerle ağırlıklandırılmış)
item_factors = (Vt.T * sigma).astype(np.float32)   # shape: (N_movies, 50)

# L2-normalize
norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
norms[norms == 0.0] = 1.0
item_factors_norm = item_factors / norms

# Cosine similarity latent uzayda
sims = (item_factors_norm @ item_factors_norm[i]).astype(np.float64)
```

**SVD neden daha iyi:**
- Seyrek binary matrisin gürültüsünü filtreler
- Gizli kalıpları (latent patterns) yakalar: "aksiyon + gerilim seven kullanıcılar genellikle bunu da sever"
- Item-item cosine seyrek matrise doğrudan uygulayınca anlamsız benzerlikler çıkabilir

**Fallback:** `min(N_users, N_movies) - 1 < 1` ise ham item-item cosine

**Artifact:** `cf_index.joblib` → `{tmdb_ids, cf_top_indices: (N, 50), cf_top_scores: (N, 50)}`

### 3.3 Hybrid Blending — Smooth Sigmoid Alpha

```python
import math

def _get_alpha(n_interactions, cf_threshold=5, cf_alpha=0.5):
    if n_interactions <= 0:
        return 1.0
    x = (n_interactions - cf_threshold) / max(cf_threshold / 2.0, 1.0)
    blend = 1.0 / (1.0 + math.exp(-x))
    return 1.0 - (1.0 - cf_alpha) * blend
```

| Etkileşim | Alpha (içerik ağırlığı) |
|-----------|------------------------|
| 0         | 1.000 (saf içerik)     |
| 1         | 0.916                  |
| 2         | 0.885                  |
| 5         | 0.750 (eşik noktası)   |
| 10        | 0.560                  |
| 20        | 0.501                  |
| 50+       | ≈ 0.500                |

**Avantaj:** Ani geçiş yok. 5. etkileşimde sert 1.0→0.5 yerine kademeli azalma.

### 3.4 Ağırlıklı Candidate Scoring

```python
# v1.0 (frekans sayımı)
candidate_scores[neighbor_id] += 1.0

# v2.0 (ağırlıklı cosine toplamı)
sim = float(top_scores[idx][j]) if top_scores is not None else 1.0
candidate_scores[neighbor_id] += sim
```

**Geriye dönük uyumluluk:** `top_scores` yoksa (eski artifact) `1.0` ile fallback.

### 3.5 Değerlendirme — v2.0

**Metrikler (düzeltilmiş isimlerle):**

| Metrik | Açıklama | Neden Önemli |
|--------|----------|--------------|
| `hit_rate_at_10` | Held-out film top-10'da mı? | Ana kalite ölçütü |
| `hit_rate_at_5` | Top-5'te mi? | Daha sıkı test |
| `hit_rate_at_20` | Top-20'de mi? | Coverage kontrolü |
| `ndcg_at_10` | Sıralama kalitesi (üst sıra daha değerli) | Sıralama hassasiyeti |
| `mrr` | Mean Reciprocal Rank | İlk doğru sıralanmanın değeri |

**Baseline karşılaştırmaları (YENİ):**

| Baseline | Yöntem |
|----------|--------|
| `random_hit_rate_at_10` | NLP kataloğundan rastgele 10 film |
| `popularity_hit_rate_at_10` | Her zaman en popüler 10 film (vote_count) |

**Genişletilmiş `metrics.json`:**
```json
{
  "hit_rate_at_10": 0.XXXX,
  "hit_rate_at_5": 0.XXXX,
  "hit_rate_at_20": 0.XXXX,
  "ndcg_at_10": 0.XXXX,
  "mrr": 0.XXXX,
  "baselines": {
    "random_hit_rate_at_10": 0.XXXX,
    "popularity_hit_rate_at_10": 0.XXXX
  },
  "improvement_vs_random_x": 47.3,
  "eval_date": "2026-05-24",
  "n_users": 500,
  "history_limit": null
}
```

---

## 4. Değişiklik Karşılaştırması

### 4.1 Algoritma

| Bileşen | v1.0 (Orijinal) | v2.0 (Yükseltilmiş) |
|---------|----------------|---------------------|
| İçerik modeli | TF-IDF (5K özellik, bigram) | Sentence Transformers `all-MiniLM-L6-v2` (384-dim) |
| Komşu sayısı | top_n = 50 | top_n = 100 |
| Skor hesabı | Frekans sayımı (+1 her komşu) | Ağırlıklı cosine toplamı |
| CF modeli | Item-item cosine (ham seyrek matris) | SVD latent faktör cosine |
| CF faktör sayısı | — | k = 50 |
| Alpha geçişi | Basamak: 1.0 → 0.5 tam eşikte | Sigmoid: yumuşak geçiş |
| Artifact boyutu | `(N, 50)` indeks | `(N, 100)` indeks + `(N, 100)` skor |

### 4.2 Değerlendirme

| Alan | v1.0 | v2.0 |
|------|------|------|
| Ana metrik adı | `precision_at_10` ❌ yanlış | `hit_rate_at_10` ✓ |
| Metrik sayısı | 2 | 5 (HR@5, HR@10, HR@20, NDCG@10, MRR) |
| Baseline | Yok | Random + Popularity |
| Komşu arama derinliği | top-50 → sonuçlar kesilebilir | top-100 → daha geniş kapsam |
| Output path | Sabit `/artifacts/metrics.json` | `--output-path` flag ile özelleştirilebilir |

### 4.3 Kod Kalitesi

| Alan | Değişiklik |
|------|-----------|
| `pymongo` import | Modül seviyesinde → `main()` içinde lazy (unit testler bağımsız çalışır) |
| Self-exclusion | `sims[i] = -1.0` → `-2.0` (cosine min = -1.0 ile tie riski giderildi) |
| Test kapsamı | 46 worker testi (yeni: MRR, weighted scoring, smooth alpha, CF scores) |
| Backward compat | `precision_at_k` alias korundu, `top_scores=None` fallback |

---

## 5. Veri Akışı ve Mimari

### 5.1 Çevrimdışı Pipeline (Worker)

```
TMDB API (film metadata)
    │
    ▼
ingest_tmdb.py
    │  MongoDB'ye film dokümanları yazar
    ▼
nlp_features.py
    │  all-MiniLM-L6-v2 ile 384-dim embedding
    │  Cosine similarity index (top-100 + skorlar)
    ▼ artifacts/similarity_index.joblib
cf_features.py
    │  SVD (k=50) latent faktör
    │  CF cosine similarity index
    ▼ artifacts/cf_index.joblib
seed_interactions.py
    │  MovieLens-20M → MongoDB interactions
    ▼
evaluate.py
    │  Leave-one-out değerlendirme
    │  HR@5/10/20, NDCG@10, MRR
    │  Random + Popularity baselines
    ▼ artifacts/metrics.json
```

### 5.2 Çevrimiçi Servis (FastAPI)

```
POST /api/recommendations {genres, mood}
    │
    ▼ RecommendationService.get_recommendations()
    │
    ├─ Genre filtresi → tohum filmler (MongoDB)
    │
    ├─ Ağırlıklı cosine toplama (top_scores)
    │     for each seed → Σ sim_score[neighbor]
    │
    ├─ Mood boost (×1.3 eşleşen türler)
    │
    ├─ Kullanıcı geri bildirim feedback
    │     (liked neighbors +feedback_weight×sim)
    │     (disliked neighbors −feedback_weight×sim)
    │
    ├─ Smooth alpha hesaplama
    │     alpha = sigmoid(n − threshold)
    │
    ├─ CF blending (alpha < 1.0 ve CF artifact varsa)
    │     CF skor = Σ cf_sim_score[liked_neighbor]
    │     final = alpha × norm_content + (1−alpha) × norm_cf
    │
    └─ Top-10 → MongoDB'den tam dokümanlar → Response
```

### 5.3 Konfigürasyon

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `CF_THRESHOLD` | 5 | Sigmoid merkezin bağlı olduğu etkileşim sayısı |
| `CF_ALPHA` | 0.5 | Çok sayıda etkileşimde hedef içerik ağırlığı |
| `ARTIFACTS_DIR` | `/artifacts` | Joblib dosyalarının yolu |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB bağlantı adresi |
| `DB_NAME` | `movie_mrs` | Veritabanı adı |

---

## 6. Değerlendirme Çerçevesi

### 6.1 Leave-One-Out Protokolü

1. Her kullanıcı için: ≥5 beğeni şartı
2. Zaman sırasıyla sırala (`updated_at` ascending)
3. En son beğeniyi `held_out` olarak ayır
4. Geri kalanlar `training_ids`
5. `score_from_history(training_ids)` ile top-K üret
6. `held_out_id in top_K?` → metrik hesapla

**Soğuk başlangıç simülasyonu:**
```bash
# Sadece son 1 etkileşimle değerlendir
python jobs/evaluate.py --history-limit 1

# Sadece son 3 etkileşimle
python jobs/evaluate.py --history-limit 3
```

### 6.2 Metrik Formülleri

**Hit Rate @ K (HR@K):**
```
HR@K = (held_out ∈ top-K) ? 1.0 : 0.0
mean = Σ HR@K / n_users
```

**NDCG @ K:**
```
DCG@K   = Σ relevance_i / log2(i+2)    (i=0..K-1)
NDCG@K  = DCG@K / IDCG@K
```
1 relevant item → sklearn `ndcg_score` kullanılır.

**MRR:**
```
RR  = 1 / rank_of_held_out  (eğer top-K içindeyse, else 0)
MRR = mean(RR)
```

### 6.3 Baseline Metodolojisi

**Random baseline:** Her test vakası için NLP kataloğundan (training'deki filmler hariç) rastgele 10 film. Seed = `42 + i`.

**Popularity baseline:** MongoDB'den vote_count'a göre sıralı top-200 film → training'dekiler çıkarılır → ilk 10 alınır. Her kullanıcı için aynı liste.

**Niçin bu iki baseline:**
- **Random:** Teorik alt sınır. Herhangi bir algoritmanın üstüne çıkması beklenir.
- **Popularity:** Pratik alt sınır. Popüler filmler zaten çok kişi tarafından beğenildiği için güçlü bir baseline'dır.

---

## 7. Artifacts ve Dosya Yapısı

### 7.1 Üretilen Artifacts

| Dosya | İçerik | Boyut (tahmini) |
|-------|--------|----------------|
| `similarity_index.joblib` | `{tmdb_ids, top_indices(N,100), top_scores(N,100)}` | ~15 MB |
| `cf_index.joblib` | `{tmdb_ids, cf_top_indices(N,50), cf_top_scores(N,50)}` | ~8 MB |
| `metrics.json` | HR@5/10/20, NDCG@10, MRR + baselines | < 1 KB |

> `tfidf_vectorizer.joblib` artık üretilmiyor (runtime'da hiç kullanılmıyordu).

### 7.2 Kritik Dosyalar

```
cinewise-main/
├── worker/
│   ├── jobs/
│   │   ├── nlp_features.py        # Sentence Transformers pipeline
│   │   ├── cf_features.py         # SVD CF pipeline
│   │   ├── evaluate.py            # Kapsamlı değerlendirme
│   │   ├── ingest_tmdb.py         # TMDB veri ingestion
│   │   └── seed_interactions.py   # MovieLens-20M seed
│   ├── tests/
│   │   ├── test_eval_pipeline.py  # HR@K, MRR, weighted scoring testleri
│   │   ├── test_nlp_pipeline.py   # Embedding + index testleri
│   │   └── test_cf_pipeline.py    # SVD + scores testleri
│   └── requirements.txt           # sentence-transformers>=3.0.0 eklendi
│
├── backend/
│   ├── app/
│   │   ├── main.py                # top_scores + cf_top_scores yükleme
│   │   ├── services/
│   │   │   └── recommendation_service.py  # Smooth alpha + weighted scoring
│   │   └── api/routes/
│   │       └── metrics.py         # Yeni metrik alanları pass-through
│   └── tests/
│       ├── conftest.py            # top_scores/cf_top_scores None fixtures
│       └── test_recommendations.py # Smooth alpha testleri
│
└── RECOMMENDATION_SYSTEM.md       # Bu dosya
```

---

## 8. API Referansı

### POST `/api/recommendations`

**Gövde:**
```json
{
  "genres": ["Action", "Thriller"],
  "mood": "Tense"
}
```

**Yanıt:**
```json
{
  "recommendations": [
    {
      "tmdb_id": 155,
      "title": "The Dark Knight",
      "title_tr": "Kara Şövalye",
      "year": 2008,
      "genres": ["Action", "Crime", "Drama"],
      "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
      "rating": 9.0,
      "overview": "Batman raises the stakes...",
      "explanation": "Recommended because you like Action and Thriller, feeling Tense."
    }
  ]
}
```

### GET `/api/metrics`

**Yanıt (v2.0):**
```json
{
  "hit_rate_at_10": 0.3240,
  "hit_rate_at_5":  0.1980,
  "hit_rate_at_20": 0.4510,
  "ndcg_at_10":     0.2150,
  "mrr":            0.1830,
  "baselines": {
    "random_hit_rate_at_10":     0.0021,
    "popularity_hit_rate_at_10": 0.0980
  },
  "improvement_vs_random_x": 154.3,
  "eval_date": "2026-05-24",
  "n_users": 500,
  "history_limit": null
}
```

### POST `/api/feedback`

```json
{ "movie_id": 155, "action": "like" }
```

---

## 9. Çalıştırma Talimatları

### 9.1 İlk Kurulum

```bash
# Worker dependencies (sentence-transformers dahil)
pip install -r worker/requirements.txt
```

### 9.2 Pipeline Sırası

```bash
# 1. TMDB verisini ingest et
docker compose run worker python jobs/ingest_tmdb.py

# 2. Semantic embedding + similarity index üret
docker compose run worker python jobs/nlp_features.py

# 3. SVD CF index üret
docker compose run worker python jobs/cf_features.py

# 4. MovieLens seed interactions yükle (değerlendirme için)
docker compose run worker python jobs/seed_interactions.py

# 5. Değerlendirme çalıştır
docker compose run worker python jobs/evaluate.py --max-users 500

# 5b. Cold-start convergence analizi
docker compose run worker python jobs/evaluate.py --max-users 500 --history-limit 1 --output-path /artifacts/metrics_h1.json
docker compose run worker python jobs/evaluate.py --max-users 500 --history-limit 3 --output-path /artifacts/metrics_h3.json
docker compose run worker python jobs/evaluate.py --max-users 500 --history-limit 5 --output-path /artifacts/metrics_h5.json
```

### 9.3 Testler

```bash
# Worker testleri (46 test — local'de çalışır)
cd worker && python -m pytest tests/ -v

# Backend testleri (Docker'da çalışır — pymongo versiyonu gerektirir)
docker compose run backend python -m pytest tests/ -v
```

### 9.4 Backend başlatma

```bash
docker compose up backend
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Metrics: http://localhost:8000/api/metrics
```

---

## 10. Beklenen Metrik İyileşmesi

| Sistem | HR@10 (tahmini) | Açıklama |
|--------|----------------|----------|
| Random baseline | ~0.2% | 10 / 5000 film |
| Popularity baseline | ~10% | Popüler filmler çok beğenilir |
| **v1.0** (TF-IDF + frekans) | ~%14 | ~70x random'dan iyi |
| + Ağırlıklı scoring | ~%17 | Cosine skorları kullan |
| + **Sentence Transformers** | ~%28–32 | Semantik benzerlik |
| + **SVD CF** | ~%32–38 | Latent faktör + ST kombinasyonu |
| Akademik SOTA (NCF, BERT4Rec) | ~%45–60 | Referans üst sınır |

> **Not:** Gerçek değerler `evaluate.py` çalıştırılınca `metrics.json`'a kaydedilir ve `GET /api/metrics` ile alınabilir.

---

## Değişiklik Geçmişi

| Versiyon | Tarih | Değişiklik |
|----------|-------|-----------|
| v1.0 | Mart 2026 | TF-IDF + item-item cosine CF + step alpha |
| v2.0 | Mayıs 2026 | Sentence Transformers + SVD + smooth alpha + kapsamlı evaluation |

---

*Bu dosya, v1.0 ve v2.0 arasındaki tüm teknik değişiklikleri kapsamakta olup yeni artifact üretiminden sonra metrik değerleri güncellenmelidir.*
