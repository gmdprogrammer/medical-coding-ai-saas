"use client";
import { useState } from "react";
import { CheckCircle, AlertCircle, Info, ChevronDown, ChevronUp, Clock, Shield, Copy, Check } from "lucide-react";
import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip } from "recharts";
import type { CodingResponse, MedicalCode } from "@/types";
import { cn, confidenceColor, formatConfidence } from "@/lib/utils";
import FeedbackWidget from "./FeedbackWidget";
import toast from "react-hot-toast";

interface Props {
  result: CodingResponse;
}

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.85 ? "bg-green-500" : score >= 0.65 ? "bg-yellow-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-500 w-9 text-right">{pct}%</span>
    </div>
  );
}

function CodeCard({ code }: { code: MedicalCode }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(code.code);
    setCopied(true);
    toast.success(`Copied code ${code.code}`);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <div className="flex items-start gap-3 p-4">
        <div className="flex-shrink-0 flex items-center gap-1.5">
          <span className="inline-block rounded-md bg-medical-600 text-white text-xs font-mono px-2 py-1 font-bold">
            {code.code}
          </span>
          <button
            type="button"
            onClick={copyToClipboard}
            className="text-gray-400 hover:text-gray-600 p-0.5 rounded transition-colors"
            title="Copy code"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 leading-snug">{code.description}</p>
          <div className="mt-2">
            <ConfidenceBar score={code.confidence} />
          </div>
          <div className="mt-1 flex items-center gap-1">
            <span className={cn("badge text-xs", confidenceColor(code.confidence_label))}>
              {code.confidence_label} confidence
            </span>
          </div>
        </div>
        {code.supporting_evidence.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        )}
      </div>

      {expanded && code.supporting_evidence.length > 0 && (
        <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
          <p className="text-xs font-medium text-gray-500 mb-2">Supporting evidence:</p>
          <ul className="space-y-1">
            {code.supporting_evidence.map((ev, i) => (
              <li key={i} className="text-xs text-gray-600 flex gap-2">
                <span className="text-medical-400 font-bold mt-0.5">›</span>
                <span className="italic">"{ev}"</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function ResultsDisplay({ result }: Props) {
  const [showExplanation, setShowExplanation] = useState(false);
  const [allCopied, setAllCopied] = useState(false);

  const avgICD = result.icd10_codes.length
    ? result.icd10_codes.reduce((s, c) => s + c.confidence, 0) / result.icd10_codes.length
    : 0;
  const avgCPT = result.cpt_codes.length
    ? result.cpt_codes.reduce((s, c) => s + c.confidence, 0) / result.cpt_codes.length
    : 0;

  const copyAllCodes = () => {
    const lines = [
      "=== ICD-10 CODES ===",
      ...result.icd10_codes.map(c => `- ${c.code}: ${c.description} (${c.confidence_label} confidence)`),
      "",
      "=== CPT / HCPCS CODES ===",
      ...result.cpt_codes.map(c => `- ${c.code}: ${c.description} (${c.confidence_label} confidence)`),
    ].join("\n");
    navigator.clipboard.writeText(lines);
    setAllCopied(true);
    toast.success("Copied all codes to clipboard!");
    setTimeout(() => setAllCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Metadata bar */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <Clock className="h-3.5 w-3.5" />
          {result.processing_time_ms}ms
        </div>
        {result.phi_detected && (
          <div className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 border border-green-200 rounded-full px-2.5 py-0.5">
            <Shield className="h-3.5 w-3.5" />
            PHI removed
          </div>
        )}
        <div className="flex items-center gap-1.5 text-xs text-medical-600 bg-medical-50 border border-medical-200 rounded-full px-2.5 py-0.5">
          ICD-10 avg: {formatConfidence(avgICD)}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-purple-600 bg-purple-50 border border-purple-200 rounded-full px-2.5 py-0.5">
          CPT avg: {formatConfidence(avgCPT)}
        </div>
        <button
          type="button"
          onClick={copyAllCodes}
          className="ml-auto inline-flex items-center gap-1 text-xs text-medical-600 hover:text-medical-700 font-semibold transition-colors"
          title="Copy all codes to clipboard"
        >
          {allCopied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
          {allCopied ? "Copied!" : "Copy All"}
        </button>
      </div>

      {/* Clinical Summary */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
          <Info className="h-4 w-4 text-medical-500" /> Clinical Summary
        </h3>
        <p className="text-sm text-gray-700 leading-relaxed">{result.clinical_summary}</p>
      </div>

      {/* ICD-10 Codes */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-green-500" />
          ICD-10 Codes
          <span className="ml-auto text-xs text-gray-400 font-normal">{result.icd10_codes.length} suggested</span>
        </h3>
        <div className="space-y-2">
          {result.icd10_codes.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No ICD-10 codes identified</p>
          ) : (
            result.icd10_codes.map((c) => <CodeCard key={c.code} code={c} />)
          )}
        </div>
      </div>

      {/* CPT Codes */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-purple-500" />
          CPT / HCPCS Codes
          <span className="ml-auto text-xs text-gray-400 font-normal">{result.cpt_codes.length} suggested</span>
        </h3>
        <div className="space-y-2">
          {result.cpt_codes.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No CPT codes identified</p>
          ) : (
            result.cpt_codes.map((c) => <CodeCard key={c.code} code={c} />)
          )}
        </div>
      </div>

      {/* Explanation */}
      {result.explanation && (
        <div>
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900"
          >
            {showExplanation ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            Coding Explanation
          </button>
          {showExplanation && (
            <div className="mt-3 p-4 bg-blue-50 border border-blue-100 rounded-lg">
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                {result.explanation}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Feedback */}
      <FeedbackWidget sessionId={result.session_id} />
    </div>
  );
}
