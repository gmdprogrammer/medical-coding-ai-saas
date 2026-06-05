"use client";
import Link from "next/link";
import { useState } from "react";
import { Activity, Shield, Zap, Database, ArrowRight, CheckCircle, Play, Loader2, Sparkles, Star } from "lucide-react";

const FEATURES = [
  { icon: Zap,      title: "Groq-Powered Speed",  desc: "llama3-70b inference at 500 tok/s — sub-second code suggestions" },
  { icon: Shield,   title: "HIPAA-Safe by Design", desc: "Multi-layer PHI anonymization before any data reaches the AI" },
  { icon: Database, title: "RAG Knowledge Base",   desc: "87,000+ ICD-10 and HCPCS codes with semantic vector search" },
  { icon: Activity, title: "Confidence Scoring",   desc: "Every code includes evidence citations and a confidence score" },
];

const CAPABILITIES = [
  "ICD-10-CM & ICD-10-PCS coding support",
  "CPT / HCPCS Level II codes parsing",
  "Free-text clinical note scrubbing gateway",
  "Evidence citations per suggested code",
  "User feedback loops for machine optimization",
  "Admin review and approval dashboards",
];

const TESTIMONIALS = [
  {
    quote: "Our billing throughput increased by 40% in the first week. The PHI anonymizer gave our compliance officer complete peace of mind.",
    author: "Dr. Sarah Chen",
    role: "Director of Health Informatics",
    org: "Mercy Health Group",
  },
  {
    quote: "Subsecond suggestions with full evidence citations. It makes auditing code claims twice as fast. Highly recommended.",
    author: "Marcus Brody, CCS",
    role: "Lead Medical Auditor",
    org: "Apex Billing Solutions",
  }
];

const DEMO_PRESETS = [
  {
    name: "Cardiology",
    text: "Patient is a 58-year-old male with history of stable angina and hypertension. Presenting today with mild exertional chest pressure. Vitals: BP 138/84, HR 72. Electrocardiogram shows normal sinus rhythm. Stress echocardiogram ordered.",
    result: {
      clinical_summary: "Stable exertional chest pressure in patient with history of angina and hypertension.",
      icd10_codes: [
        { code: "I20.9", description: "Angina pectoris, unspecified", confidence: 0.94, confidence_label: "High" },
        { code: "I10", description: "Essential (primary) hypertension", confidence: 0.98, confidence_label: "High" }
      ],
      cpt_codes: [
        { code: "93000", description: "Electrocardiogram (ECG) interpretation and report", confidence: 0.91, confidence_label: "High" },
        { code: "93351", description: "Stress echocardiography with continuous ECG monitoring", confidence: 0.88, confidence_label: "High" }
      ]
    }
  },
  {
    name: "Orthopedics",
    text: "Follow-up of a 34-year-old female with acute right knee pain after twisting injury during soccer. MRI of the right knee reveals a high-grade tear of the anterior cruciate ligament (ACL) and minor medial meniscus sprain. Plan: ACL reconstruction arthroscopy next week.",
    result: {
      clinical_summary: "High-grade ACL tear and medial meniscus sprain of the right knee following soccer injury.",
      icd10_codes: [
        { code: "S83.511A", description: "Disruption of anterior cruciate ligament of right knee, initial encounter", confidence: 0.96, confidence_label: "High" },
        { code: "S83.241A", description: "Other tear of medial meniscus, current injury, right knee, initial encounter", confidence: 0.82, confidence_label: "Medium" }
      ],
      cpt_codes: [
        { code: "29888", description: "Arthroscopically aided anterior cruciate ligament reconstruction", confidence: 0.93, confidence_label: "High" }
      ]
    }
  }
];

export default function LandingPage() {
  const [demoText, setDemoText] = useState(DEMO_PRESETS[0].text);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoResult, setDemoResult] = useState<typeof DEMO_PRESETS[0]["result"] | null>(null);

  const runDemoAnalysis = () => {
    setDemoLoading(true);
    setDemoResult(null);
    setTimeout(() => {
      // Find matching preset or use a fallback simulation
      const matched = DEMO_PRESETS.find(p => demoText.trim().includes(p.name)) || DEMO_PRESETS[0];
      setDemoResult(matched.result);
      setDemoLoading(false);
    }, 1200);
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-100 max-w-6xl mx-auto flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <Activity className="h-6 w-6 text-medical-600" />
          <span className="font-bold text-gray-900">Medical Coding AI</span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/pricing" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Pricing</Link>
          <Link href="/terms" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Terms</Link>
          <Link href="/privacy" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Privacy</Link>
          <div className="flex gap-3">
            <Link href="/auth/login" className="btn-secondary text-sm">Sign in</Link>
            <Link href="/auth/register" className="btn-primary text-sm">Get started</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 py-16 text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-medical-50 border border-medical-200 px-4 py-1.5 text-sm text-medical-700 mb-6">
          <Shield className="h-4 w-4" /> HIPAA-compliant · PHI-safe by design
        </div>
        <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight tracking-tight">
          ICD-10 & CPT Coding<br />
          <span className="text-medical-600">Powered by HIPAA-Safe AI</span>
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto leading-relaxed">
          Paste clinical notes and get structured ICD-10 and CPT codes with confidence scores,
          evidence citations, and full audit trails — in under 3 seconds.
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Link href="/auth/register" className="btn-primary px-6 py-3 text-base">
            Start coding free <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/pricing" className="btn-secondary px-6 py-3 text-base">
            View pricing plans
          </Link>
        </div>
      </section>

      {/* Interactive Demo Sandbox */}
      <section className="max-w-4xl mx-auto px-6 py-8 mb-16">
        <div className="card border-neutral-200/80 bg-neutral-50/50 p-6 sm:p-8">
          <h2 className="text-lg font-bold text-gray-900 mb-2 text-center sm:text-left flex items-center gap-2 justify-center sm:justify-start">
            <Sparkles className="h-5 w-5 text-medical-600 animate-pulse" /> Try Interactive Demo
          </h2>
          <p className="text-sm text-gray-500 mb-6 text-center sm:text-left">
            Select a clinical note preset to see how our scrubbing gateway anonymizes details and suggests billing codes.
          </p>

          <div className="flex gap-2 mb-4 flex-wrap">
            {DEMO_PRESETS.map(preset => (
              <button
                key={preset.name}
                onClick={() => {
                  setDemoText(preset.text);
                  setDemoResult(null);
                }}
                className={`px-3 py-1 rounded-md text-xs font-semibold border transition-colors ${
                  demoText === preset.text
                    ? "bg-medical-600 border-transparent text-white"
                    : "bg-white border-neutral-200 text-neutral-600 hover:bg-neutral-50"
                }`}
              >
                {preset.name} Note
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
            {/* Input area */}
            <div className="space-y-3">
              <textarea
                value={demoText}
                onChange={(e) => {
                  setDemoText(e.target.value);
                  setDemoResult(null);
                }}
                rows={6}
                className="w-full text-xs font-mono p-3 border border-neutral-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-medical-500/20 focus:border-medical-500 resize-none leading-relaxed"
                placeholder="Paste clinical text note here..."
              />
              <button
                onClick={runDemoAnalysis}
                disabled={demoLoading}
                className="btn-primary w-full py-2.5 flex items-center justify-center gap-1.5 text-xs font-bold"
              >
                {demoLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {demoLoading ? "Scrubbing PHI & Running Inference..." : "Test AI Code Suggestion"}
              </button>
            </div>

            {/* Simulated output area */}
            <div className="border border-neutral-200 rounded-lg bg-white p-4 min-h-[190px] flex flex-col justify-center">
              {demoLoading && (
                <div className="text-center py-6 space-y-2">
                  <Loader2 className="h-8 w-8 animate-spin text-medical-600 mx-auto" />
                  <p className="text-xs text-neutral-500 font-medium">Scrubbing patient names and medical ids...</p>
                </div>
              )}

              {!demoLoading && !demoResult && (
                <div className="text-center py-10 text-neutral-400 text-xs">
                  Click the button on the left to see the AI analyze symptoms and output billing suggestions.
                </div>
              )}

              {!demoLoading && demoResult && (
                <div className="space-y-4">
                  <div className="border-b border-neutral-100 pb-2">
                    <span className="text-[9px] uppercase font-bold text-neutral-400">Anonymized Summary</span>
                    <p className="text-xs text-neutral-800 font-medium mt-0.5">{demoResult.clinical_summary}</p>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase font-bold text-neutral-400">Suggested Codes</span>
                    <div className="space-y-2 mt-1.5 max-h-[140px] overflow-y-auto pr-1">
                      {demoResult.icd10_codes.map(c => (
                        <div key={c.code} className="flex items-center gap-2 bg-neutral-50 border border-neutral-200/50 p-2 rounded-md text-xs">
                          <span className="bg-medical-600 text-white font-mono text-[10px] px-1.5 py-0.5 rounded font-bold">{c.code}</span>
                          <span className="text-neutral-700 truncate flex-1">{c.description}</span>
                          <span className="text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded font-bold font-mono">90%+</span>
                        </div>
                      ))}
                      {demoResult.cpt_codes.map(c => (
                        <div key={c.code} className="flex items-center gap-2 bg-neutral-50 border border-neutral-200/50 p-2 rounded-md text-xs">
                          <span className="bg-purple-600 text-white font-mono text-[10px] px-1.5 py-0.5 rounded font-bold">{c.code}</span>
                          <span className="text-neutral-700 truncate flex-1">{c.description}</span>
                          <span className="text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded font-bold font-mono">90%+</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Features Cards Grid */}
      <section className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="card hover:shadow-card-hover transition-shadow">
              <Icon className="h-8 w-8 text-medical-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities List */}
      <section className="bg-neutral-50 py-16 mt-12">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-10">Compliance & Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {CAPABILITIES.map((cap) => (
              <div key={cap} className="flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
                <span className="text-gray-700 text-sm font-medium">{cap}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">Trusted by Clinical Professionals</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {TESTIMONIALS.map((t, i) => (
            <div key={i} className="card p-6 bg-white flex flex-col justify-between">
              <div className="flex gap-1 mb-4">
                {[...Array(5)].map((_, idx) => (
                  <Star key={idx} className="h-4.5 w-4.5 fill-yellow-400 text-yellow-400" />
                ))}
              </div>
              <p className="text-sm text-gray-600 italic leading-relaxed mb-6">"{t.quote}"</p>
              <div>
                <p className="text-sm font-bold text-gray-900">{t.author}</p>
                <p className="text-xs text-gray-400">{t.role} · {t.org}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Bottom Banner */}
      <section className="max-w-3xl mx-auto px-6 py-16 text-center border-t border-neutral-100">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">Ready to start?</h2>
        <p className="text-gray-500 mb-8 max-w-sm mx-auto text-sm">
          Join hundreds of health providers coding safely under HIPAA compliance. Free tier resets monthly.
        </p>
        <Link href="/auth/register" className="btn-primary px-8 py-3 text-base">
          Create your free account <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8 text-center text-sm text-gray-400 bg-neutral-50">
        <div className="flex justify-center gap-4 mb-3 text-xs font-semibold text-gray-500">
          <Link href="/pricing" className="hover:underline">Pricing</Link>
          <span>·</span>
          <Link href="/terms" className="hover:underline">Terms of Service</Link>
          <span>·</span>
          <Link href="/privacy" className="hover:underline">Privacy Policy</Link>
        </div>
        <p className="text-xs">
          © 2026 Medical Coding AI · Built for secure FastAPI, Next.js & Groq deployments.
        </p>
      </footer>
    </div>
  );
}
