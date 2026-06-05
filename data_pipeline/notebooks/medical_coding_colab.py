"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        MEDICAL CODING AI — GOOGLE COLAB NOTEBOOK                           ║
║        Convert to .ipynb by running:                                       ║
║          pip install jupytext && jupytext --to notebook this_file.py       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Copy each section into a separate Colab cell.
Runtime: GPU recommended for embedding generation (T4 sufficient).
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 1 — Install Dependencies
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTALL = """
!pip install -q \
    sentence-transformers \
    faiss-cpu \
    groq \
    presidio-analyzer \
    presidio-anonymizer \
    spacy \
    pandas \
    numpy \
    scikit-learn \
    tqdm \
    loguru \
    datasets

!python -m spacy download en_core_web_sm -q
print("✅ Installation complete")
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 2 — Mount Google Drive & Setup Paths
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SETUP = """
from google.colab import drive
import os, json, pickle
from pathlib import Path

drive.mount('/content/drive')

BASE = Path('/content/drive/MyDrive/medical_coding_ai')
DATA_DIR = BASE / 'data'
INDEX_DIR = BASE / 'indices'

for d in [DATA_DIR, INDEX_DIR, DATA_DIR / 'icd10', DATA_DIR / 'hcpcs', DATA_DIR / 'processed']:
    d.mkdir(parents=True, exist_ok=True)

print(f"✅ Directories ready under {BASE}")
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 3 — Download Dataset (ICD-10-CM from CMS)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOWNLOAD_DATA = """
import urllib.request
import zipfile

# ── ICD-10-CM 2024 (CMS official — public domain) ────────────────────────────
ICD10_URL = "https://www.cms.gov/files/zip/2024-code-descriptions-tabular-order-updated-01/09/2024.zip"
ICD10_ZIP = DATA_DIR / 'icd10' / 'icd10cm_2024.zip'

print("Downloading ICD-10-CM 2024...")
try:
    urllib.request.urlretrieve(ICD10_URL, ICD10_ZIP)
    with zipfile.ZipFile(ICD10_ZIP, 'r') as z:
        z.extractall(DATA_DIR / 'icd10')
    print("✅ ICD-10-CM downloaded and extracted")
except Exception as e:
    print(f"⚠️  Auto-download failed ({e}). Manual steps:")
    print("  1. Go to: https://www.cms.gov/medicare/coding-billing/icd-10-codes")
    print("  2. Download '2024 Code Descriptions in Tabular Order'")
    print("  3. Upload to your Drive under: data/icd10/")
    print("  4. Note: File is named 'icd10cm_order_2024.txt' (tab-delimited)")

# ── HCPCS Level II 2024 (CMS — fully public) ──────────────────────────────────
# Download from: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-coding-system
print("\\nHCPCS Level II: Download manually from CMS website")
print("  URL: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-coding-system")
print("  File: HCPCS2024_ANWEB_v3.zip → upload to data/hcpcs/")

# ── Create sample data for testing if files not available ─────────────────────
SAMPLE_ICD10 = [
    {"code_type": "icd10", "code": "E11.9",  "description": "Type 2 diabetes mellitus without complications",           "short_desc": "Type 2 diabetes w/o complications",    "category": "E11", "billable": True, "text": "E11.9: Type 2 diabetes mellitus without complications. Also known as: Type 2 diabetes w/o complications"},
    {"code_type": "icd10", "code": "I10",    "description": "Essential (primary) hypertension",                         "short_desc": "Essential hypertension",               "category": "I10", "billable": True, "text": "I10: Essential (primary) hypertension. Also known as: Essential hypertension"},
    {"code_type": "icd10", "code": "J18.9",  "description": "Pneumonia, unspecified organism",                          "short_desc": "Pneumonia, unspecified",                "category": "J18", "billable": True, "text": "J18.9: Pneumonia, unspecified organism. Also known as: Pneumonia, unspecified"},
    {"code_type": "icd10", "code": "N18.3",  "description": "Chronic kidney disease, stage 3 (moderate)",              "short_desc": "Chronic kidney disease, stage 3",       "category": "N18", "billable": True, "text": "N18.3: Chronic kidney disease, stage 3 (moderate). Also known as: CKD stage 3"},
    {"code_type": "icd10", "code": "F32.1",  "description": "Major depressive disorder, single episode, moderate",      "short_desc": "Major depressive disorder, moderate",  "category": "F32", "billable": True, "text": "F32.1: Major depressive disorder, single episode, moderate"},
    {"code_type": "icd10", "code": "M54.5",  "description": "Low back pain",                                            "short_desc": "Low back pain",                        "category": "M54", "billable": True, "text": "M54.5: Low back pain"},
    {"code_type": "icd10", "code": "Z87.891","description": "Personal history of nicotine dependence",                  "short_desc": "History of nicotine dependence",       "category": "Z87", "billable": True, "text": "Z87.891: Personal history of nicotine dependence"},
    {"code_type": "icd10", "code": "K21.0",  "description": "Gastro-esophageal reflux disease with esophagitis",       "short_desc": "GERD with esophagitis",                "category": "K21", "billable": True, "text": "K21.0: Gastro-esophageal reflux disease with esophagitis. Also known as: GERD"},
    {"code_type": "icd10", "code": "E78.5",  "description": "Hyperlipidemia, unspecified",                              "short_desc": "Hyperlipidemia, unspecified",           "category": "E78", "billable": True, "text": "E78.5: Hyperlipidemia, unspecified"},
    {"code_type": "icd10", "code": "J44.1",  "description": "Chronic obstructive pulmonary disease with acute exacerbation", "short_desc": "COPD with acute exacerbation",   "category": "J44", "billable": True, "text": "J44.1: COPD with acute exacerbation"},
]

SAMPLE_HCPCS = [
    {"code_type": "hcpcs", "code": "99213", "description": "Office or other outpatient visit, established patient, low to moderate medical decision making, 20-29 min",  "short_desc": "Office visit, established, low-moderate MDM", "category": "9", "billable": True, "text": "99213: Office visit established patient 20-29 minutes low to moderate complexity"},
    {"code_type": "hcpcs", "code": "99232", "description": "Subsequent hospital inpatient or observation care, moderate medical decision making, 25-34 min",              "short_desc": "Subsequent hospital care, moderate MDM",       "category": "9", "billable": True, "text": "99232: Subsequent hospital care moderate complexity 25-34 minutes"},
    {"code_type": "hcpcs", "code": "71046", "description": "Radiologic examination, chest; 2 views",                                                                      "short_desc": "Chest X-ray 2 views",                         "category": "7", "billable": True, "text": "71046: Chest X-ray radiologic examination 2 views"},
    {"code_type": "hcpcs", "code": "85025", "description": "Complete blood count (CBC), automated, and automated differential",                                           "short_desc": "CBC with differential, automated",            "category": "8", "billable": True, "text": "85025: Complete blood count CBC with automated differential white blood cell"},
    {"code_type": "hcpcs", "code": "93000", "description": "Electrocardiogram, routine ECG with at least 12 leads; with interpretation and report",                      "short_desc": "ECG 12 leads with report",                    "category": "9", "billable": True, "text": "93000: Electrocardiogram ECG 12-lead routine with interpretation report"},
    {"code_type": "hcpcs", "code": "99291", "description": "Critical care, evaluation and management of the critically ill or injured patient; first 30-74 minutes",      "short_desc": "Critical care first 30-74 min",               "category": "9", "billable": True, "text": "99291: Critical care evaluation management first 30-74 minutes intensive"},
    {"code_type": "hcpcs", "code": "36415", "description": "Collection of venous blood by venipuncture",                                                                  "short_desc": "Venipuncture",                                "category": "3", "billable": True, "text": "36415: Venipuncture collection of venous blood phlebotomy"},
    {"code_type": "hcpcs", "code": "80053", "description": "Comprehensive metabolic panel",                                                                               "short_desc": "Comprehensive metabolic panel",               "category": "8", "billable": True, "text": "80053: Comprehensive metabolic panel CMP glucose BUN creatinine electrolytes"},
]

all_sample = SAMPLE_ICD10 + SAMPLE_HCPCS
sample_path = DATA_DIR / 'processed' / 'medical_codes_sample.jsonl'
with open(sample_path, 'w') as f:
    for rec in all_sample:
        f.write(json.dumps(rec) + '\\n')

print(f"\\n✅ Sample dataset ({len(all_sample)} records) saved to {sample_path}")
print("Use this for testing. Replace with full CMS dataset for production.")
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 4 — Data Preprocessing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREPROCESSING = """
import pandas as pd
import re

def parse_icd10cm_flat(filepath):
    records = []
    try:
        with open(filepath, encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\\n').split('\\t')
                if len(parts) < 5:
                    continue
                _, raw_code, billable, short_desc, long_desc = parts[:5]
                raw_code = raw_code.strip()
                code = f"{raw_code[:3]}.{raw_code[3:]}" if len(raw_code) > 3 else raw_code
                records.append({
                    "code_type": "icd10", "code": code,
                    "description": long_desc.strip(), "short_desc": short_desc.strip(),
                    "category": code[:3], "billable": billable.strip() == "1",
                    "text": f"{code}: {long_desc.strip()}. Also known as: {short_desc.strip()}"
                })
    except FileNotFoundError:
        print(f"File not found: {filepath} — using sample data")
    return records

def clean_records(records):
    seen = set()
    cleaned = []
    for rec in records:
        code = rec.get('code', '').strip()
        desc = rec.get('description', '').strip()
        if not code or not desc or not rec.get('billable', True):
            continue
        if code in seen:
            continue
        seen.add(code)
        rec['description'] = re.sub(r'\\s+', ' ', desc)
        rec['text'] = re.sub(r'\\s+', ' ', rec.get('text', f"{code}: {desc}"))
        cleaned.append(rec)
    print(f"Cleaned: {len(cleaned)} records (from {len(records)})")
    return cleaned

# Try to load real data, fall back to sample
icd_path = DATA_DIR / 'icd10' / 'icd10cm_order_2024.txt'
records = parse_icd10cm_flat(str(icd_path))
if not records:
    print("Loading sample dataset...")
    with open(DATA_DIR / 'processed' / 'medical_codes_sample.jsonl') as f:
        records = [json.loads(l) for l in f if l.strip()]

records = clean_records(records)
df = pd.DataFrame(records)
print(f"\\nDataset overview:")
print(df.groupby('code_type').size())
print(f"\\nSample records:")
print(df.head(3).to_string())
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 5 — Embedding Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMBEDDING_GENERATION = """
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm.notebook import tqdm

# ── Why all-MiniLM-L6-v2? ────────────────────────────────────────────────────
# • 384-dim embeddings → small FAISS index
# • 14,000+ sentences/sec on GPU → fast batch processing
# • MTEB score: 56.3 (strong general-purpose semantic similarity)
# • Alternative: pritamdeka/PubMedBERT-mnli-snli-scinli (768-dim, biomedical)
#   → Use when coding accuracy on clinical notes is the primary concern
#   → 3× slower but better on specialized medical terminology
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
print(f"Loading model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)

texts = [r['text'] for r in records]
print(f"Encoding {len(texts)} texts...")

BATCH_SIZE = 256  # Reduce to 64 if OOM on free Colab GPU
embeddings = model.encode(
    texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    normalize_embeddings=True,  # L2 normalize → cosine via inner product
    convert_to_numpy=True,
)
embeddings = embeddings.astype('float32')
print(f"\\n✅ Embeddings shape: {embeddings.shape}")
print(f"   Memory usage: {embeddings.nbytes / 1024**2:.1f} MB")

# Verify normalization (all norms should be 1.0)
norms = np.linalg.norm(embeddings[:5], axis=1)
print(f"   Sample norms (should be ~1.0): {norms}")
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 6 — Build FAISS Index
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUILD_INDEX = """
import faiss
import pickle

DIM = embeddings.shape[1]  # 384

# IndexFlatIP = exact inner product (= cosine on normalized vectors)
# For >500K codes: use IndexIVFFlat for 50x speedup
#   quantizer = faiss.IndexFlatIP(DIM)
#   index = faiss.IndexIVFFlat(quantizer, DIM, 1024, faiss.METRIC_INNER_PRODUCT)
#   index.train(embeddings)  # Required for IVF
#   index.nprobe = 32

index = faiss.IndexFlatIP(DIM)
index.add(embeddings)
print(f"✅ FAISS index built: {index.ntotal} vectors × {DIM} dims")

# Save index and metadata
INDEX_PATH = INDEX_DIR / 'faiss_medical_index'
faiss.write_index(index, str(INDEX_PATH))
META_PATH = INDEX_DIR / 'faiss_medical_index.meta.pkl'
with open(META_PATH, 'wb') as f:
    pickle.dump(records, f)

index_size = INDEX_PATH.stat().st_size / 1024**2
print(f"   Index saved: {INDEX_PATH} ({index_size:.1f} MB)")
print(f"   Metadata saved: {META_PATH}")
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 7 — Query Testing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUERY_TESTING = """
def search_medical_codes(query, top_k=5, code_type=None, min_score=0.3):
    query_vec = model.encode([query], normalize_embeddings=True).astype('float32')
    scores, indices = index.search(query_vec, top_k * 3)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or score < min_score:
            continue
        meta = records[idx].copy()
        meta['score'] = float(score)
        if code_type and meta.get('code_type') != code_type:
            continue
        results.append(meta)
        if len(results) >= top_k:
            break
    return sorted(results, key=lambda x: x['score'], reverse=True)

# ── Test queries ──────────────────────────────────────────────────────────────
test_cases = [
    ("Patient presents with poorly controlled blood sugar, A1C of 9.2%, history of type 2 diabetes", "icd10"),
    ("Chest X-ray shows bilateral infiltrates consistent with pneumonia", "icd10"),
    ("Routine office visit, 25 minutes, established patient with hypertension follow-up", "hcpcs"),
    ("Blood draw for comprehensive metabolic panel and CBC with differential", "hcpcs"),
    ("Patient complains of lower back pain radiating to left leg, worsening with activity", "icd10"),
]

for query, code_type in test_cases:
    print(f"\\n{'='*70}")
    print(f"Query: {query[:80]}...")
    print(f"Code type: {code_type}")
    results = search_medical_codes(query, top_k=3, code_type=code_type)
    for r in results:
        print(f"  [{r['score']:.3f}] {r['code']}: {r['description'][:60]}")
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 8 — PHI Anonymization Test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHI_TEST = """
import re

# Lightweight regex-only anonymizer for Colab testing
# (Full Presidio version is in the backend)
PHI_PATTERNS = [
    ('SSN',   re.compile(r'\\b\\d{3}-\\d{2}-\\d{4}\\b'),             '[SSN]'),
    ('PHONE', re.compile(r'\\b(\\+1[-.\\s]?)?\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}\\b'), '[PHONE]'),
    ('EMAIL', re.compile(r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b'), '[EMAIL]'),
    ('DATE',  re.compile(r'\\b(?:\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}|\\w+ \\d{1,2},? \\d{4})\\b'), '[DATE]'),
    ('MRN',   re.compile(r'\\bMRN[:#\\s]*\\d{5,12}\\b', re.I),       '[MRN]'),
    ('ZIP',   re.compile(r'\\b\\d{5}(?:-\\d{4})?\\b'),               '[ZIP]'),
]

def anonymize(text):
    found = []
    for label, pattern, repl in PHI_PATTERNS:
        new_text, count = pattern.subn(repl, text)
        if count:
            found.extend([label] * count)
            text = new_text
    return text, found

# Test
sample_note = \"\"\"
Patient: John Smith, DOB: 03/15/1968, MRN: 123456789
Phone: (555) 867-5309, Email: jsmith@email.com
Address: 123 Oak Street, Boston, MA 02134
SSN: 123-45-6789

CC: Patient presents with chest pain and shortness of breath.
PMH: Type 2 diabetes mellitus (A1C 8.4%), hypertension.
Vitals: BP 145/92, HR 88, SpO2 97%.
Assessment: Probable GERD with anxiety component.
Plan: Start omeprazole 20mg daily. Follow up in 4 weeks.
\"\"\"

anon_text, entities = anonymize(sample_note)
print("ORIGINAL (snippet):", sample_note[:200])
print("\\n" + "="*60)
print("ANONYMIZED:")
print(anon_text)
print("\\nPHI entities removed:", entities)
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 9 — End-to-End RAG Pipeline Test with Groq
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E2E_TEST = """
from groq import Groq
import json as _json

GROQ_API_KEY = "your-groq-api-key-here"  # Replace with your key
client = Groq(api_key=GROQ_API_KEY)

def build_rag_context(icd_results, cpt_results):
    lines = ["=== RELEVANT ICD-10 CODES ==="]
    for r in icd_results:
        lines.append(f"• {r['code']}: {r['description']} (score: {r['score']:.2f})")
    lines.append("\\n=== RELEVANT CPT/HCPCS CODES ===")
    for r in cpt_results:
        lines.append(f"• {r['code']}: {r['description']} (score: {r['score']:.2f})")
    return "\\n".join(lines)

def extract_codes_with_rag(clinical_text, top_k=3):
    # Step 1: Anonymize
    safe_text, phi_found = anonymize(clinical_text)
    print(f"PHI removed: {phi_found}")

    # Step 2: Retrieve
    icd_results = search_medical_codes(safe_text, top_k=top_k, code_type='icd10')
    cpt_results = search_medical_codes(safe_text, top_k=top_k, code_type='hcpcs')
    rag_context = build_rag_context(icd_results, cpt_results)

    # Step 3: Generate
    prompt = f\"\"\"Analyze the following clinical text and extract medical codes.

KNOWLEDGE BASE CONTEXT:
{rag_context}

CLINICAL TEXT (anonymized):
{safe_text}

Return JSON with:
- clinical_summary (string)
- icd10_codes (list of {{code, description, confidence, supporting_evidence}})
- cpt_codes (list of {{code, description, confidence, supporting_evidence}})
- explanation (string)

Only return valid JSON.\"\"\"

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "You are an expert medical coder. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0.1,
    )
    raw = response.choices[0].message.content
    # Clean markdown fences
    raw = raw.strip().strip('`').replace('json\\n', '').strip()
    return _json.loads(raw)

# Test clinical note
clinical_note = \"\"\"
Patient is a 58-year-old male presenting for routine follow-up.
He has a known history of type 2 diabetes, hypertension, and hyperlipidemia.
Today's visit includes medication reconciliation and lab review.
A1C is 8.1%. BP: 148/90. Ordered CBC and comprehensive metabolic panel.
Chest X-ray ordered due to new cough. Total visit time: 28 minutes.
\"\"\"

result = extract_codes_with_rag(clinical_note)
print("\\n" + "="*70)
print("CLINICAL SUMMARY:", result.get('clinical_summary', ''))
print("\\nICD-10 CODES:")
for code in result.get('icd10_codes', []):
    confidence = code.get('confidence', 0)
    label = 'High' if confidence >= 0.85 else 'Medium' if confidence >= 0.65 else 'Low'
    print(f"  [{label} {confidence:.0%}] {code['code']}: {code['description']}")

print("\\nCPT/HCPCS CODES:")
for code in result.get('cpt_codes', []):
    confidence = code.get('confidence', 0)
    label = 'High' if confidence >= 0.85 else 'Medium' if confidence >= 0.65 else 'Low'
    print(f"  [{label} {confidence:.0%}] {code['code']}: {code['description']}")

print("\\nEXPLANATION:", result.get('explanation', '')[:300], "...")
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CELL 10 — Optional Fine-tuning Pipeline (when to use vs RAG)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINE_TUNING_GUIDE = """
# ═══════════════════════════════════════════════════════════════
# WHEN TO USE FINE-TUNING vs RAG
# ═══════════════════════════════════════════════════════════════
#
# USE RAG (default — this system):
#   ✓ < 50K labeled training examples
#   ✓ Codes update annually (re-index instead of retrain)
#   ✓ Need citation/evidence per code (auditability)
#   ✓ Development timeline < 2 weeks
#   ✓ Explainability is required for clinical compliance
#
# USE FINE-TUNING (augment or replace RAG):
#   ✓ > 50K annotated clinical note → code pairs
#   ✓ Accuracy on narrow specialty (e.g., oncology) must be >95%
#   ✓ RAG confidence scores plateau after adding more data
#   ✓ Budget allows GPU training ($100-500/run on A100)
#
# FINE-TUNING APPROACH (LoRA on Llama3):

'''
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
import datasets

# 1. Prepare dataset: JSONL with {"prompt": clinical_text, "completion": json_codes}
dataset = datasets.load_dataset("json", data_files="./training_data.jsonl")

# 2. Load base model (use 4-bit quantization for Colab)
model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, load_in_4bit=True)

# 3. Configure LoRA (low-rank adaptation — fine-tunes ~0.1% of parameters)
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,              # Rank
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
)
model = get_peft_model(model, lora_config)

# 4. Train
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    args=TrainingArguments(
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,
        output_dir="./checkpoints",
    ),
)
trainer.train()
# 5. Upload adapter to HuggingFace Hub and integrate with Groq via API
'''
print("Fine-tuning guide printed. Use RAG by default — switch to fine-tuning")
print("only when you have 50K+ annotated examples and RAG accuracy plateaus.")
"""

if __name__ == "__main__":
    print("This file contains Colab notebook cells as Python strings.")
    print("Copy each cell variable content into a separate Colab code cell.")
    print("Or run: jupytext --to notebook medical_coding_colab.py")
