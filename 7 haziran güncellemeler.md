# Cinewise — 7 Haziran Güncellemeleri

## Özet

Bitirme projesi sunumuna hazırlamak amacıyla yapılan kapsamlı UI ve özellik güncellemeleri.

---

## 1. Proje Kimliği (Faz 0)

- `index.html` başlığı `frontend` → `Cinewise — AI Movie Recommendations`
- Navbar adı `MovieMRS` → `Cinewise`
- Navbar'a glassmorphism efekti (`backdrop-blur`, şeffaf kenarlık)
- Giriş yapmış kullanıcılar için Navbar'a **History**, **Profile**, **Watchlist** linkleri eklendi
- Aktif sayfa linki accent renginde alt çizgiyle vurgulanıyor

---

## 2. Mood'a Göre Dinamik Arka Plan Rengi (Faz 2)

Hocanın isteği: kullanıcı mood seçince sitenin arka plan rengi değişsin.

**Teknik yaklaşım:** CSS değişkenleri (`--cw-bg`, `--cw-surface`, `--cw-accent`) JavaScript ile runtime'da güncelleniyor. Tailwind JIT rebuild gerekmez.

| Mood | Arka Plan | Aksan Rengi |
|---|---|---|
| Varsayılan | `#0f0f14` (sinema siyahı) | `#6366f1` (indigo) |
| Happy 😄 | `#1a1008` (sıcak koyu amber) | `#f59e0b` (ochre) |
| Tense 😬 | `#071a14` (derin teal) | `#2dd4bf` (teal) |
| Relaxing 😌 | `#0e1220` (lavender koyu) | `#b8a4ed` (lavender) |
| Mind-bending 🌀 | `#120a1f` (derin mor) | `#a855f7` (purple) |
| Romantic ❤️ | `#1a0a10` (derin gül) | `#fb7185` (rose) |

- `0.6s ease` CSS geçişiyle yumuşak renk değişimi
- **Tetikleyiciler:**
  - Öneri sayfasında mood seçip "Get Recommendations" tıklanınca
  - Anasayfada kaydedilmiş tercihler yüklenince otomatik

**Yeni dosya:** `frontend/src/features/mood/MoodThemeContext.tsx`

---

## 3. Dark Mode UI + Hero Section (Faz 3)

Tüm sayfa ve bileşenler CSS değişken tabanlı dark mode'a geçirildi:

- `LoginPage`, `RegisterPage`, `RecommendationsPage`, `MovieDetailPage`
- `MovieCard`, `MovieGrid`, `SearchBar`, `FilterDropdowns`
- `FeedbackControls`, `PreferenceChips`, `RecommendationCard`

**Hero Section** (giriş yapılmamışken anasayfada görünür):
- Sinematik gradient banner
- "Discover Your Next Favorite Film" başlığı
- "Get Recommendations" ve "Browse Movies" CTA butonları

---

## 4. İzleme Süresi / Tamamlanma Oranı (Faz 1)

Film değerlendirmesine izleme süresi bilgisi eklendi — bu veri öneri algoritmasını etkiliyor.

### Backend

`POST /api/feedback` isteğine `watch_completion: float` (0.0–1.0) alanı eklendi.

**Öneri ağırlıklandırması:**

| İzleme Oranı | Çarpan | Anlam |
|---|---|---|
| ≥ %90 | ×1.5 | Bitirildi → güçlü pozitif sinyal |
| ≥ %50 | ×1.2 | Çoğunlukla izlendi |
| ≥ %10 | ×1.0 | Kısmen → nötr |
| < %10 | ×(−0.3) | Neredeyse hiç izlenmedi → hafif negatif |

### Frontend

- `WatchCompletionPicker` bileşeni: 4 düğmeli segment kontrol (Barely / Half / Almost / Finished)
- SVG progress bar ikonlar (kütüphane yok)
- Kullanıcı beğeni/beğenmedi verdikten sonra slide-in görünür
- `FeedbackControls` ve `MovieDetailPage`'e entegre edildi

---

## 5. Kullanıcı Profil Sayfası (Faz 4)

**Yeni sayfa:** `/profile`

- **Avatar:** Email baş harfi, mood'a göre renk
- **4 İstatistik Kartı:** Toplam Değerlendirme / Beğeni / Beğenmeme / Ort. İzleme
- **Zevk Profili:** Saf SVG donut chart — tür dağılımını gösterir (kütüphane yok)
- **Kişiselleştirme Progress Bar:** "X/5 etkileşimde collaborative filtering aktif"
- **Son Aktivite:** Son 5 etkileşim mini poster listesi
- **Aktif Mood Badge:** Mevcut mood renkli etiketle gösterilir

**Yeni backend endpoint:** `GET /api/history/stats` — tür sayımları, beğeni/beğenmeme oranları

---

## 6. İzleme Geçmişi Sayfası (Faz 5)

**Yeni sayfa:** `/history`

- **Filtre sekmeleri:** Tümü / Beğendi / Beğenmedi / İzledi
- Film posterlerinde aksiyon renk overlay (yeşil/kırmızı)
- İzleme yüzdesi için **SVG CompletionRing** (donut halka)
- Hover'da geçmişten silme butonu (×)
- Sayfalama (Previous / Next)

**Yeni backend endpoint:** `DELETE /api/feedback/{movie_id}`

---

## 7. Watchlist (Film Listesi) (Faz 6)

**Yeni sayfa:** `/watchlist`

- Film grid görünümü, boş durum mesajı
- Her filmde "Remove" butonu

**Yer imi ikonu (WatchlistButton):**
- Her film kartında hover'da görünür (anasayfa, arama sonuçları)
- Film detay sayfasında başlığın yanında sabit görünür
- Listedeyse dolu yer imi ikonu (accent rengi), değilse outline
- Optimistic update ile anlık geri bildirim

**Yeni backend:** `GET/POST /api/watchlist`, `DELETE /api/watchlist/{movie_id}`

---

## 8. Onboarding Akışı (Faz 7)

**Yeni sayfa:** `/onboarding` — kayıt sonrası otomatik yönlendirme

3 adımlı akış:
1. **Tür Tercihleri** — chip seçimi (en az 1 zorunlu)
2. **Mood Seçimi** — opsiyonel, temayı anında tetikler
3. **Hızlı Değerlendirme** — 8 popüler film 👍 / — / 👎, anında CF sinyali

Üstte progress dots animasyonu.

---

## Değişen Dosyalar

### Frontend (Yeni)
- `src/features/mood/MoodThemeContext.tsx`
- `src/components/WatchCompletionPicker.tsx`
- `src/components/WatchlistButton.tsx`
- `src/components/TasteProfileChart.tsx`
- `src/hooks/useHistory.ts`
- `src/hooks/useWatchlist.ts`
- `src/pages/ProfilePage.tsx`
- `src/pages/HistoryPage.tsx`
- `src/pages/WatchlistPage.tsx`
- `src/pages/OnboardingPage.tsx`

### Frontend (Güncellenen)
- `index.html` — başlık
- `src/index.css` — CSS değişkenleri, animasyonlar
- `src/main.tsx` — MoodThemeProvider eklendi
- `src/App.tsx` — 4 yeni route
- `src/components/Navbar.tsx` — Cinewise, glassmorphism, auth linkleri
- `src/components/MovieCard.tsx` — dark mode, genre badge, actionSlot
- `src/components/MovieGrid.tsx` — WatchlistButton actionSlot
- `src/components/FeedbackControls.tsx` — WatchCompletionPicker entegrasyonu
- `src/components/PreferenceChips.tsx` — dark mode, emoji
- `src/pages/HomePage.tsx` — Hero section, setActiveMood
- `src/pages/RecommendationsPage.tsx` — dark mode, setActiveMood
- `src/pages/MovieDetailPage.tsx` — dark mode, WatchlistButton
- `src/pages/LoginPage.tsx` / `RegisterPage.tsx` — dark mode, /onboarding yönlendirme
- `src/lib/types.ts` — WatchCompletion tipi
- `src/hooks/useFeedback.ts` — watch_completion alanı

### Backend (Yeni)
- `app/repositories/watchlist_repo.py`
- `app/api/routes/history.py`
- `app/api/routes/watchlist.py`

### Backend (Güncellenen)
- `app/api/routes/feedback.py` — watch_completion alanı, DELETE endpoint
- `app/repositories/interactions_repo.py` — upsert, delete, get_stats
- `app/services/recommendation_service.py` — completion ağırlık çarpanı
- `app/main.py` — yeni router kayıtları
- `tests/test_feedback.py` — 3 yeni test

---

## Doğrulama

```
npm run build   → 153 modül, 367KB, 0 TypeScript hatası
pytest          → 51/51 geçti (5 önceden mevcut bcrypt hatası — Docker'da geçiyor)
```
