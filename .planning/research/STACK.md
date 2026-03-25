# Technology Stack

**Project:** AI-Powered Personalized Movie Recommendation System
**Researched:** 2026-03-25

## Recommended Stack

### Backend Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12 | Runtime | Stable, widely supported, excellent ML/NLP ecosystem. 3.13 is available but 3.12 has broader library compatibility. | HIGH |
| FastAPI | 0.128.0 | Web framework | Async-native, automatic OpenAPI docs, Pydantic integration. Industry standard for Python APIs in 2025/2026. | HIGH |
| Uvicorn | latest | ASGI server | FastAPI's recommended server. Use `--workers` for multi-process in production. | HIGH |
| Pydantic | 2.12.5 | Data validation | FastAPI's native validation layer. V2 is 5-50x faster than V1. Required by both FastAPI and Beanie. | HIGH |

### Database & ODM

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| MongoDB Atlas | Free tier (M0) | Primary database | Flexible schema for heterogeneous movie metadata. Free tier sufficient for capstone scale (512MB). | HIGH |
| Beanie | 2.0.1 | MongoDB ODM | Async ODM built on Pydantic models -- seamless FastAPI integration. Document-level CRUD with validation. 5-10x throughput over sync PyMongo in async apps. | HIGH |
| PyMongo | 4.16.x | Database driver | Beanie's underlying driver. **Do NOT use Motor** -- Motor is deprecated (EOL May 2026). PyMongo now has native async API. | HIGH |

**Important:** Beanie 2.x still uses Motor internally but abstracts it away. For any raw MongoDB access, use PyMongo's native async API (`pymongo.asynchronous`), not Motor directly. This future-proofs the codebase.

### NLP & Feature Extraction

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| scikit-learn | 1.8.0 | TF-IDF + cosine similarity | `TfidfVectorizer` and `cosine_similarity` are battle-tested, fast on CPU, zero GPU needed. Core of content-based filtering. | HIGH |
| NLTK | 3.9.2 | Text preprocessing | Tokenization, stopword removal, stemming/lemmatization for movie summaries before TF-IDF. Lightweight enough for batch processing. | HIGH |
| spaCy | 3.8.11 | NLP pipeline (optional) | Use `en_core_web_sm` (small model, ~12MB) for lemmatization if NLTK's WordNetLemmatizer proves insufficient. **Do not install transformer models** -- too heavy for CPU-only constraint. | MEDIUM |
| sentence-transformers | latest | Semantic embeddings (Phase 2+) | `all-MiniLM-L6-v2` produces 384-dim embeddings, runs on CPU in ~50ms/sentence. Use for enhanced content similarity beyond TF-IDF. **Defer to later phase** -- TF-IDF first. | MEDIUM |

**NLP Strategy:** Start with scikit-learn TF-IDF + NLTK preprocessing. This is lightweight, well-understood, and sufficient for MVP. Sentence-transformers can be added later as an enhancement without architectural changes (just another feature vector).

**What NOT to use:**
- **Full spaCy transformer models (`en_core_web_trf`)** -- 400MB+, requires GPU for reasonable speed. Violates no-GPU constraint.
- **Hugging Face transformers directly** -- Overkill for this use case. sentence-transformers wraps it cleanly if needed.
- **Gensim** -- Was standard for topic modeling (LDA) and Word2Vec, but topic modeling is out of scope. scikit-learn covers TF-IDF better.

### Machine Learning

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyTorch | 2.11.0 | Neural collaborative filtering | Required by project spec. Use CPU-only install (`pip install torch --index-url https://download.pytorch.org/whl/cpu`) to avoid 2GB+ CUDA downloads. | HIGH |
| scikit-learn | 1.8.0 | Similarity computation, evaluation metrics | `cosine_similarity`, `precision_score`, `ndcg_score`. Already needed for NLP -- dual purpose. | HIGH |
| NumPy | latest | Numerical operations | Matrix operations for recommendation scoring. Transitive dependency of scikit-learn/PyTorch. | HIGH |
| SciPy | latest | Sparse matrices | `scipy.sparse` for efficient TF-IDF matrix storage and similarity computation on large movie catalogs. | HIGH |

**Collaborative Filtering approach:** Build a lightweight neural collaborative filtering (NCF) model in PyTorch rather than using the `implicit` or `surprise` libraries. Rationale: (1) PyTorch is already a project requirement, (2) NCF is well-documented and gives you full control, (3) avoids additional dependencies, (4) better capstone learning outcome.

**What NOT to use:**
- **TensorFlow/Keras** -- PyTorch is the project spec. TF adds massive dependency bloat.
- **surprise library** -- Only handles explicit ratings with SVD. PyTorch NCF is more flexible for hybrid approach.
- **implicit library** -- Good for ALS but adds another dependency when PyTorch already handles this.

### Authentication & Security

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| python-jose[cryptography] | latest | JWT token handling | FastAPI's officially recommended JWT library. HS256 signing. | HIGH |
| passlib[bcrypt] | latest | Password hashing | bcrypt hashing via passlib's CryptContext. FastAPI docs standard. | HIGH |
| python-multipart | latest | Form data parsing | Required for OAuth2 password flow in FastAPI. | HIGH |

### Batch Processing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| APScheduler | 3.11.2 | Job scheduling | Schedule TMDB data ingestion and NLP feature recomputation. Lightweight, no external broker needed. | HIGH |
| httpx | latest | Async HTTP client | TMDB API calls in batch workers. Async-native, supports rate limiting. Prefer over `requests` for async codebase. | HIGH |

**What NOT to use:**
- **Celery + Redis/RabbitMQ** -- Massive overkill for 10-user capstone. Requires external broker service. APScheduler runs in-process.
- **requests library** -- Synchronous. Use httpx for consistency with async FastAPI codebase.

### Frontend

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| React | 19.x | UI framework | Project spec. Component-based, massive ecosystem. | HIGH |
| TypeScript | 5.x | Type safety | Catches bugs at compile time. Standard for professional React in 2025/2026. | HIGH |
| Vite | 8.x | Build tool | Industry standard replacement for CRA. Rolldown integration gives near-instant builds. | HIGH |
| React Router | 7.x | Client-side routing | Standard routing for React SPAs. v7 is non-breaking upgrade from v6. | HIGH |
| TanStack Query | 5.x | Server state management | Handles API caching, refetching, loading states. Eliminates manual fetch/state boilerplate. | HIGH |
| Zustand | 5.x | Client state management | Lightweight store for auth state, user preferences, UI state. ~1KB, zero boilerplate. | HIGH |
| Axios | 1.x | HTTP client | Auto JSON parsing, interceptors for auth tokens, better error handling than fetch. Works well with TanStack Query. | MEDIUM |
| Tailwind CSS | 4.x | Styling | Utility-first CSS. Fast prototyping, consistent design. Standard for 2025/2026 React projects. | MEDIUM |

**What NOT to use:**
- **Redux/Redux Toolkit** -- Overkill for this app's state complexity. Zustand + TanStack Query covers everything with 90% less code.
- **Create React App (CRA)** -- Deprecated. Vite is the standard.
- **Next.js** -- SSR/SSG not needed for a SPA that calls a FastAPI backend. Adds unnecessary complexity.
- **Material UI** -- Heavy bundle, opinionated design. Tailwind gives more control with less weight.

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | latest | Backend testing | Python testing standard. FastAPI has excellent pytest integration. | HIGH |
| pytest-asyncio | latest | Async test support | Required for testing async FastAPI endpoints and Beanie operations. | HIGH |
| httpx | latest | Test client | FastAPI's `TestClient` uses httpx under the hood. Already in stack for TMDB calls. | HIGH |
| Vitest | latest | Frontend testing | Vite-native test runner. Same config as build tool, fast watch mode. | MEDIUM |

### Developer Tools

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Ruff | latest | Python linting + formatting | Replaces flake8 + black + isort. 10-100x faster, single tool. Industry standard 2025. | HIGH |
| pre-commit | latest | Git hooks | Enforce linting/formatting before commits. | MEDIUM |
| ESLint | 9.x | TypeScript linting | Standard for React/TypeScript projects. | MEDIUM |
| Prettier | latest | Frontend formatting | Standard code formatter for TS/JSX. | MEDIUM |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | FastAPI | Django REST Framework | Django is heavier, sync-first. FastAPI's async + auto-docs is better fit. |
| Database | MongoDB | PostgreSQL | Project spec requires MongoDB. Flexible schema fits movie metadata well. |
| ODM | Beanie | MongoEngine | MongoEngine is synchronous. Beanie is async + Pydantic-native. |
| MongoDB driver | PyMongo (async) | Motor | Motor deprecated May 2025, EOL May 2026. PyMongo native async is the successor. |
| NLP baseline | scikit-learn TF-IDF | Gensim | Gensim's TF-IDF is less integrated. scikit-learn covers TF-IDF + metrics in one package. |
| Embeddings | sentence-transformers | OpenAI embeddings API | Costs money per request. sentence-transformers runs locally, free, no API dependency. |
| ML framework | PyTorch | TensorFlow | Project spec. PyTorch has better research ecosystem and debugging (eager mode). |
| Task queue | APScheduler | Celery | Celery requires Redis/RabbitMQ broker. APScheduler is in-process, perfect for capstone scale. |
| Frontend state | Zustand + TanStack Query | Redux Toolkit | Redux is ~40% more code for same functionality at this scale. |
| Build tool | Vite 8 | Webpack | Vite is 10-100x faster, less config. Industry standard since 2024. |
| HTTP client (Python) | httpx | requests | httpx is async-native, critical for FastAPI/async codebase. |
| Styling | Tailwind CSS | Styled Components | Tailwind has faster prototyping cycle, smaller runtime overhead. |
| Python linter | Ruff | flake8 + black + isort | Ruff replaces all three, 100x faster, single dependency. |

## Installation

### Backend

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Core framework
pip install fastapi==0.128.0 uvicorn[standard] pydantic==2.12.5

# Database
pip install beanie==2.0.1

# NLP & ML (CPU-only PyTorch)
pip install scikit-learn==1.8.0 nltk==3.9.2 numpy scipy
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Auth
pip install python-jose[cryptography] passlib[bcrypt] python-multipart

# HTTP & Scheduling
pip install httpx apscheduler==3.11.2

# Dev tools
pip install pytest pytest-asyncio ruff pre-commit

# Optional (Phase 2+): spaCy + lightweight model
# pip install spacy==3.8.11 && python -m spacy download en_core_web_sm

# Optional (Phase 2+): Sentence embeddings
# pip install sentence-transformers
```

### Frontend

```bash
# Scaffold project
npm create vite@latest frontend -- --template react-ts

cd frontend

# Core
npm install react-router axios

# State management
npm install @tanstack/react-query zustand

# Styling
npm install tailwindcss @tailwindcss/vite

# Dev tools
npm install -D eslint prettier vitest
```

### NLTK Data Downloads

```python
# Run once after install
import nltk
nltk.download('punkt_tab')
nltk.download('stopwords')
nltk.download('wordnet')
```

## Version Pinning Strategy

Pin major+minor versions in `requirements.txt` for reproducibility:

```
fastapi==0.128.0
pydantic==2.12.5
beanie==2.0.1
scikit-learn==1.8.0
nltk==3.9.2
apscheduler==3.11.2
```

Let patch versions float for security fixes. Pin exact versions only in `requirements.lock` for production deployments.

## Architecture Compatibility Notes

1. **Async everywhere:** FastAPI + Beanie + httpx + PyMongo async = fully async I/O pipeline. Do not mix in synchronous blocking calls on the main thread.

2. **Batch vs. Serving separation:** PyTorch model training and TF-IDF computation happen in batch workers (APScheduler jobs), not in API request handlers. API handlers only load pre-computed artifacts (similarity matrices, model weights).

3. **Artifact storage:** Pre-computed TF-IDF matrices and PyTorch model checkpoints should be saved to disk (pickle/joblib for sklearn, `.pt` for PyTorch) and loaded into memory at API startup. MongoDB stores movie metadata and user data, not ML artifacts.

4. **TMDB rate limiting:** httpx with `asyncio.Semaphore` for concurrent request throttling. TMDB free tier allows ~40 requests/10 seconds.

## Sources

- [FastAPI PyPI](https://pypi.org/project/fastapi/) - Version 0.128.0 confirmed
- [FastAPI Official Docs](https://fastapi.tiangolo.com/) - JWT auth patterns, async best practices
- [scikit-learn 1.8.0 Release](https://scikit-learn.org/stable/whats_new.html) - TfidfVectorizer docs
- [PyTorch Releases](https://github.com/pytorch/pytorch/releases) - v2.11.0 confirmed March 2026
- [Motor Deprecation Notice](https://www.mongodb.com/docs/drivers/motor/) - Deprecated May 2025, EOL May 2026
- [PyMongo Async API](https://pymongo.readthedocs.io/en/stable/api/pymongo/asynchronous/) - v4.16.0 GA
- [Beanie ODM](https://beanie-odm.dev/) - v2.0.1 on PyPI
- [Pydantic v2.12](https://pydantic.dev/articles/pydantic-v2-12-release) - v2.12.5 stable
- [Vite 8 Announcement](https://vite.dev/blog/announcing-vite8) - Rolldown integration
- [React Router Releases](https://github.com/remix-run/react-router/releases) - v7.13.x
- [spaCy PyPI](https://pypi.org/project/spacy/) - v3.8.11
- [NLTK PyPI](https://pypi.org/project/nltk/) - v3.9.2
- [sentence-transformers](https://sbert.net/) - all-MiniLM-L6-v2 for CPU
- [Model2Vec](https://dev.to/pringled/model2vec-making-sentence-transformers-500x-faster-on-cpu-and-15x-smaller-3mhe) - 500x faster CPU embeddings
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) - v3.11.2
- [State Management 2026](https://www.c-sharpcorner.com/article/state-management-in-react-2026-best-practices-tools-real-world-patterns/) - Zustand + TanStack Query
