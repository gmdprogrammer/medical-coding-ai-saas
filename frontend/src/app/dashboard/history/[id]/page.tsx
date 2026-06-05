"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Clock, Shield, Loader2 } from "lucide-react";
import { codingApi } from "@/lib/api";
import ResultsDisplay from "@/components/ResultsDisplay";
import type { CodingResponse } from "@/types";
import { formatDate } from "@/lib/utils";

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    codingApi
      .getSession(id)
      .then(setSession)
      .catch((err) => {
        const msg = err.response?.data?.detail || "Session not found";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-medical-600" />
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        <p className="text-red-500 mb-4">{error || "Session not found"}</p>
        <Link href="/dashboard/history" className="btn-secondary">
          Back to history
        </Link>
      </div>
    );
  }

  // Adapt stored session data to CodingResponse shape for ResultsDisplay
  const asResponse: CodingResponse = {
    session_id: session.id,
    clinical_summary: session.clinical_summary || "",
    icd10_codes: session.icd10_codes || [],
    cpt_codes: session.cpt_codes || [],
    explanation: session.explanation || "",
    processing_time_ms: session.processing_time_ms || 0,
    phi_detected: false,
    created_at: session.created_at,
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/dashboard/history"
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800"
        >
          <ArrowLeft className="h-4 w-4" />
          History
        </Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm text-gray-700 font-medium">
          Session #{id.slice(0, 8)}
        </span>
      </div>

      {/* Meta header */}
      <div className="card mb-6">
        <div className="flex flex-wrap gap-4 items-center text-sm text-gray-500">
          <span className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            {formatDate(session.created_at)}
          </span>
          <span className="flex items-center gap-1.5">
            <Shield className="h-4 w-4 text-green-500" />
            PHI-safe (anonymized before storage)
          </span>
          <span
            className={`badge ${
              session.review_status === "approved"
                ? "bg-green-50 text-green-700 border-green-200"
                : session.review_status === "rejected"
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-yellow-50 text-yellow-700 border-yellow-200"
            }`}
          >
            {session.review_status}
          </span>
        </div>

        {session.anonymized_text && (
          <details className="mt-4">
            <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
              View anonymized input text
            </summary>
            <pre className="mt-2 text-xs text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap font-mono border border-gray-200">
              {session.anonymized_text}
            </pre>
          </details>
        )}
      </div>

      {/* Reuse ResultsDisplay — already handles icd10, cpt, explanation, feedback */}
      <div className="card">
        <h2 className="text-base font-semibold text-gray-900 mb-4">
          Coding Results
        </h2>
        <ResultsDisplay result={asResponse} />
      </div>
    </div>
  );
}
