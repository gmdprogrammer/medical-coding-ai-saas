"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, ChevronRight, Star, CheckCircle, AlertCircle } from "lucide-react";
import { codingApi } from "@/lib/api";
import type { CodingSession } from "@/types";
import { formatDate, formatConfidence, cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
  approved: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
  needs_revision: "bg-orange-50 text-orange-700 border-orange-200",
};

export default function HistoryPage() {
  const [sessions, setSessions] = useState<CodingSession[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    codingApi.getSessions(page).then((data) => {
      setSessions(data.sessions);
      setTotal(data.total);
    }).finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Coding History</h1>
        <p className="text-gray-500 mt-1">{total} total sessions</p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card animate-pulse h-24 bg-gray-100" />
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <div className="card text-center py-16">
          <Clock className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No sessions yet. Start by analyzing some clinical text.</p>
          <Link href="/dashboard" className="btn-primary mt-4 inline-flex">Start coding</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((s) => (
            <Link
              key={s.id}
              href={`/dashboard/history/${s.id}`}
              className="card hover:shadow-card-hover transition-shadow flex items-start gap-4 group"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 line-clamp-2 mb-2">
                  {s.clinical_summary || "No summary available"}
                </p>
                <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                    {s.icd10_count} ICD-10
                  </span>
                  <span className="flex items-center gap-1">
                    <AlertCircle className="h-3.5 w-3.5 text-purple-500" />
                    {s.cpt_count} CPT
                  </span>
                  {s.avg_icd_confidence != null && (
                    <span>ICD avg: {formatConfidence(s.avg_icd_confidence)}</span>
                  )}
                  {s.feedback_rating && (
                    <span className="flex items-center gap-0.5">
                      <Star className="h-3.5 w-3.5 text-yellow-400 fill-yellow-400" />
                      {s.feedback_rating}/5
                    </span>
                  )}
                  <span className={cn("badge", STATUS_STYLES[s.review_status] || STATUS_STYLES.pending)}>
                    {s.review_status}
                  </span>
                  <span className="ml-auto">{formatDate(s.created_at)}</span>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-gray-600 flex-shrink-0 mt-1" />
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="btn-secondary disabled:opacity-40"
          >
            Previous
          </button>
          <span className="flex items-center text-sm text-gray-500">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page * 20 >= total}
            className="btn-secondary disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
