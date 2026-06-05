#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Medical Coding AI — One-Shot Setup Script
# Run from project root: bash scripts/setup.sh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -euo pipefail

echo "════════════════════════════════════════"
echo "  Medical Coding AI — Setup"
echo "════════════════════════════════════════"

# ── 1. Copy env files ─────────────────────────────────────────────────────────
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "✅ Created backend/.env — edit with your GROQ_API_KEY and DB credentials"
else
  echo "⏭  backend/.env already exists"
fi

# ── 2. Backend Python environment ─────────────────────────────────────────────
echo ""
echo "Setting up Python environment..."
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
python -m spacy download en_core_web_lg -q
echo "✅ Backend Python packages installed"

# ── 3. Database migrations ─────────────────────────────────────────────────────
echo ""
echo "Running Alembic migrations..."
alembic upgrade head
echo "✅ Database schema created"
cd ..

# ── 4. Frontend dependencies ───────────────────────────────────────────────────
echo ""
echo "Installing frontend packages..."
cd frontend
npm install -q
echo "✅ Frontend packages installed"
cd ..

# ── 5. Download sample data & build vector index ──────────────────────────────
echo ""
echo "Building vector store index (sample data)..."
cd backend
python -c "
import json
from pathlib import Path

# Create sample dataset
sample = [
    {'code_type':'icd10','code':'E11.9','description':'Type 2 diabetes mellitus without complications','short_desc':'T2DM w/o complications','category':'E11','billable':True,'text':'E11.9: Type 2 diabetes mellitus without complications. Also known as: T2DM w/o complications','version':'2024'},
    {'code_type':'icd10','code':'I10','description':'Essential (primary) hypertension','short_desc':'Essential hypertension','category':'I10','billable':True,'text':'I10: Essential (primary) hypertension. Also known as: Essential hypertension','version':'2024'},
    {'code_type':'icd10','code':'J18.9','description':'Pneumonia, unspecified organism','short_desc':'Pneumonia, unspecified','category':'J18','billable':True,'text':'J18.9: Pneumonia, unspecified organism. Also known as: Pneumonia, unspecified','version':'2024'},
    {'code_type':'icd10','code':'N18.3','description':'Chronic kidney disease, stage 3','short_desc':'CKD stage 3','category':'N18','billable':True,'text':'N18.3: Chronic kidney disease stage 3 moderate. Also known as: CKD stage 3','version':'2024'},
    {'code_type':'icd10','code':'E78.5','description':'Hyperlipidemia, unspecified','short_desc':'Hyperlipidemia','category':'E78','billable':True,'text':'E78.5: Hyperlipidemia, unspecified. Also known as: High cholesterol, dyslipidemia','version':'2024'},
    {'code_type':'hcpcs','code':'99213','description':'Office visit, established patient, low to moderate MDM, 20-29 min','short_desc':'Office visit est low-mod MDM','category':'9','billable':True,'text':'99213: Office visit established patient 20-29 minutes low to moderate medical decision making','version':'2024'},
    {'code_type':'hcpcs','code':'71046','description':'Radiologic examination, chest; 2 views','short_desc':'Chest X-ray 2 views','category':'7','billable':True,'text':'71046: Chest X-ray radiologic examination 2 views','version':'2024'},
    {'code_type':'hcpcs','code':'85025','description':'Complete blood count, automated, with differential','short_desc':'CBC with differential','category':'8','billable':True,'text':'85025: Complete blood count CBC automated differential white blood cell','version':'2024'},
    {'code_type':'hcpcs','code':'80053','description':'Comprehensive metabolic panel','short_desc':'CMP','category':'8','billable':True,'text':'80053: Comprehensive metabolic panel CMP glucose BUN creatinine electrolytes','version':'2024'},
    {'code_type':'hcpcs','code':'93000','description':'Electrocardiogram, 12 leads, with interpretation and report','short_desc':'ECG 12 leads','category':'9','billable':True,'text':'93000: Electrocardiogram ECG 12 lead routine with interpretation and report','version':'2024'},
]

Path('./data/processed').mkdir(parents=True, exist_ok=True)
with open('./data/processed/medical_codes_v2024.jsonl', 'w') as f:
    for r in sample:
        f.write(json.dumps(r) + '\n')
print(f'Sample dataset: {len(sample)} records')
"

python ../data_pipeline/scripts/build_index.py \
  --input ./data/processed/medical_codes_v2024.jsonl \
  --output ./data/vector_stores/faiss_index

echo "✅ Vector index built"
cd ..

echo ""
echo "════════════════════════════════════════"
echo "  Setup complete!"
echo "════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env with your GROQ_API_KEY"
echo "  2. Start backend:   cd backend && uvicorn app.main:app --reload"
echo "  3. Start frontend:  cd frontend && npm run dev"
echo "  4. Or use Docker:   docker-compose up --build"
echo ""
echo "For production data:"
echo "  ICD-10-CM: https://www.cms.gov/medicare/coding-billing/icd-10-codes"
echo "  HCPCS:     https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-coding-system"
