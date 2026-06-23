# Medical Coding AI — Production SaaS

HIPAA-aligned ICD-10 & CPT coding assistant powered by Groq LLM + RAG.
Live Demo: https://drive.google.com/file/d/1VcJEGJTr_do8H51yEAx3-IqRbQxRx2Q8/view?usp=drive_link
---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEDICAL CODING SAAS                                  │
│                                                                              │
│   ┌─────────────────┐         ┌──────────────────────────────────────────┐  │
│   │  Next.js 14     │◄──────►│           FastAPI Backend                 │  │
│   │  Frontend        │  REST  │                                          │  │
│   │                 │  API   │  ┌──────────┐   ┌────────────────────┐  │  │
│   │  • Landing page │        │  │   Auth   │   │  PHI Middleware    │  │  │
│   │  • Dashboard     │        │  │  (JWT)   │   │  (Guard Layer)     │  │  │
│   │  • Chat/Coder   │        │  └──────────┘   └────────────────────┘  │  │
│   │  • History       │        │                                          │  │
│   │  • Admin panel   │        │  ┌───────────────────────────────────┐  │  │
│   └─────────────────┘        │  │           RAG Pipeline             │  │  │
│                               │  │                                   │  │  │
│                               │  │  ┌────────────┐  ┌────────────┐  │  │  │
│   ┌─────────────────┐        │  │  │  FAISS     │  │  Groq API  │  │  │  │
│   │   Nginx          │        │  │  │  Vector DB │  │  LLaMA3-70B│  │  │  │
│   │  Reverse Proxy  │        │  │  │  (ICD-10 + │  │            │  │  │  │
│   │  + Rate Limit   │        │  │  │   HCPCS)   │  │  ~500 tok/s│  │  │  │
│   └─────────────────┘        │  │  └────────────┘  └────────────┘  │  │  │
│                               │  │         ▲                         │  │  │
│                               │  │  Sentence-Transformers Embeddings  │  │  │
│                               │  │  (all-MiniLM-L6-v2, 384-dim)      │  │  │
│                               │  └───────────────────────────────────┘  │  │
│                               │                                          │  │
│                               │  ┌───────────────────────────────────┐  │  │
│                               │  │    PHI Anonymizer (3 layers)       │  │  │
│                               │  │  Regex → Presidio → spaCy NER      │  │  │
│                               │  └───────────────────────────────────┘  │  │
│                               │                                          │  │
│                               │  ┌─────────────┐  ┌───────────────────┐ │  │
│                               │  │ PostgreSQL   │  │  Audit Logger     │ │  │
│                               │  │ Users        │  │  HIPAA-compliant  │ │  │
│                               │  │ Sessions     │  │  Immutable trail  │ │  │
│                               │  │ Audit logs   │  └───────────────────┘ │  │
│                               │  └─────────────┘                        │  │
│                               └──────────────────────────────────────────┘  │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │  Data Pipeline (Google Colab / local)                              │    │
│   │  CMS ICD-10-CM → parse → clean → embed → FAISS index              │    │
│   │  CMS HCPCS     → parse → clean → embed → (same index)             │    │
│   └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Folder Structure

```
medical-coding-saas/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, lifespan, middleware
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── dependencies.py            # JWT auth deps (get_current_user)
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py            # /register /login /refresh /me
│   │   │       ├── coding.py          # /analyze /sessions /feedback
│   │   │       └── admin.py           # /dashboard /users /sessions/review
│   │   ├── core/
│   │   │   ├── security.py            # JWT encode/decode, bcrypt
│   │   │   ├── phi_anonymizer.py      # 3-layer PHI removal
│   │   │   └── audit_logger.py        # HIPAA audit trail
│   │   ├── services/
│   │   │   ├── vector_store.py        # FAISS + sentence-transformers
│   │   │   ├── groq_service.py        # Groq API client + prompts
│   │   │   ├── rag_service.py         # Full RAG pipeline
│   │   │   └── coding_service.py      # Orchestration + persistence
│   │   ├── models/
│   │   │   ├── database.py            # AsyncEngine, Base, get_db
│   │   │   ├── user.py                # User table
│   │   │   ├── coding_session.py      # CodingSession + CodeFeedback
│   │   │   └── audit_log.py           # AuditLog table
│   │   ├── schemas/
│   │   │   ├── auth.py                # Request/response Pydantic models
│   │   │   ├── coding.py
│   │   │   └── admin.py
│   │   └── middleware/
│   │       └── phi_middleware.py      # Defense-in-depth PHI scan
│   ├── alembic/                       # DB migrations
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Landing page
│   │   │   ├── layout.tsx
│   │   │   ├── globals.css
│   │   │   ├── auth/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── layout.tsx         # Auth guard
│   │   │   │   ├── page.tsx           # Main coder UI
│   │   │   │   └── history/page.tsx   # Session history
│   │   │   └── admin/page.tsx         # Admin dashboard
│   │   ├── components/
│   │   │   ├── Navigation.tsx
│   │   │   ├── CodingForm.tsx
│   │   │   ├── ResultsDisplay.tsx
│   │   │   └── FeedbackWidget.tsx
│   │   ├── lib/
│   │   │   ├── api.ts                 # Axios client + all API calls
│   │   │   ├── auth.ts                # Zustand auth store
│   │   │   └── utils.ts
│   │   └── types/index.ts
│   ├── Dockerfile
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── package.json
│
├── data_pipeline/
│   ├── scripts/
│   │   ├── preprocess.py              # Parse ICD-10/HCPCS, clean, version
│   │   └── build_index.py             # Generate embeddings + FAISS index
│   └── notebooks/
│       └── medical_coding_colab.py    # Full Colab notebook (10 cells)
│
├── scripts/
│   ├── setup.sh                       # One-shot local setup
│   └── load_production_data.py        # Load full CMS datasets
│
├── nginx/
│   └── nginx.conf                     # Reverse proxy + rate limiting
│
└── docker-compose.yml
```

---

## 3. Dataset Acquisition

| Dataset | Source | License | Size |
|---------|--------|---------|------|
| ICD-10-CM 2024 | [CMS.gov](https://www.cms.gov/medicare/coding-billing/icd-10-codes/2024-icd-10-cm) | Public domain | ~87K codes |
| ICD-10-PCS 2024 | [CMS.gov](https://www.cms.gov/medicare/coding-billing/icd-10-codes/2024-icd-10-pcs-and-gems) | Public domain | ~78K codes |
| HCPCS Level II 2024 | [CMS.gov](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-coding-system) | Public domain | ~7K codes |
| MIMIC-III Notes | [PhysioNet](https://physionet.org/content/mimiciii/1.4/) | Credentialed (free) | 2M+ notes |

CPT codes are restricted by the AMA — use HCPCS Level II as a public equivalent.

---

## 4. Quick Start (Local Development)

### Prerequisites
- Python 3.11+, Node.js 20+
- PostgreSQL 14+, Redis 7+
- Groq API key (free at console.groq.com)

```bash
# 1. Clone and setup
git clone <repo>
cd medical-coding-saas
bash scripts/setup.sh   # installs deps, creates sample index

# 2. Edit env
nano backend/.env       # set GROQ_API_KEY, DATABASE_URL

# 3. Start services
# Terminal A:
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal B:
cd frontend && npm run dev

# Open http://localhost:3000
```

---

## 5. Docker Deployment

```bash
# Development
docker-compose up --build

# Production (with real env vars)
POSTGRES_PASSWORD=strong_password \
GROQ_API_KEY=your_key \
docker-compose -f docker-compose.yml up -d

# Load production ICD-10 data after containers start
docker exec mc_backend python /app/scripts/load_production_data.py \
  --icd10 /app/data/icd10/icd10cm_order_2024.txt \
  --hcpcs /app/data/hcpcs/HCPCS2024_ANWEB.csv \
  --output-index /app/data/vector_stores/faiss_index
```

---

## 6. Cloud Deployment (AWS / GCP / Vercel)

### AWS ECS + RDS
```bash
# Build and push images
aws ecr get-login-password | docker login --username AWS --password-stdin <ECR_URL>
docker build -t medical-coding-backend ./backend
docker tag medical-coding-backend:latest <ECR_URL>/medical-coding-backend:latest
docker push <ECR_URL>/medical-coding-backend:latest

# Use RDS PostgreSQL + ElastiCache Redis
# Set env vars in ECS Task Definition
# Use EFS volume for FAISS index persistence
```

### Vercel (Frontend only)
```bash
cd frontend
vercel --prod
# Set NEXT_PUBLIC_API_URL to your backend URL
```

### GCP Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT/medical-coding-backend ./backend
gcloud run deploy medical-coding-backend \
  --image gcr.io/PROJECT/medical-coding-backend \
  --set-env-vars GROQ_API_KEY=xxx,DATABASE_URL=xxx \
  --memory 2Gi --cpu 2 --timeout 120
```

---

## 7. HIPAA Compliance Notes

| Requirement | Implementation |
|-------------|----------------|
| PHI Detection | 3-layer: Regex + Microsoft Presidio + spaCy NER |
| Data minimization | Raw clinical text never stored; only anonymized text + SHA-256 hash |
| Audit trail | Immutable `audit_logs` table — every action logged with user, IP, timestamp |
| Encryption at rest | PostgreSQL TDE / AWS RDS encryption |
| Encryption in transit | TLS 1.3 via Nginx |
| Access control | JWT + RBAC (coder / reviewer / admin roles) |
| Rate limiting | Nginx: 30 req/min for API, 5 req/min for auth |

**Disclaimer**: This system implements privacy-safe design patterns. A formal HIPAA BAA with cloud providers and legal review are required for clinical production use.

---

## 8. RAG vs Fine-Tuning Decision Guide

| Use RAG (default) | Use Fine-Tuning |
|-------------------|-----------------|
| < 50K labeled examples | > 50K annotated note→code pairs |
| Codes change annually | Narrow specialty (oncology, cardiology) |
| Need per-code citations | Accuracy plateaus with RAG |
| Fast iteration needed | Budget for GPU training ($100-500/run) |

---

## 9. Environment Variables

See `backend/.env.example` for the full list. Key vars:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | From console.groq.com (free tier available) |
| `SECRET_KEY` | Random 256-bit string for JWT signing |
| `DATABASE_URL` | PostgreSQL async connection string |
| `FAISS_INDEX_PATH` | Path to built FAISS index file |
| `PHI_ANONYMIZATION_ENABLED` | Set false only in testing |

---

## 10. API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET  | `/api/v1/auth/me` | Current user info |
| POST | `/api/v1/coding/analyze` | **Main coding endpoint** |
| GET  | `/api/v1/coding/sessions` | List user sessions |
| GET  | `/api/v1/coding/sessions/{id}` | Session detail |
| POST | `/api/v1/coding/feedback` | Submit accuracy rating |
| GET  | `/api/v1/admin/dashboard` | Admin stats |
| GET  | `/api/v1/admin/audit-logs` | HIPAA audit trail |
| GET  | `/health` | Health check |
| GET  | `/metrics` | Prometheus metrics |
