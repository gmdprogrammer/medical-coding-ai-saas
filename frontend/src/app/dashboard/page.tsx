"use client";
import { useState } from "react";
import CodingForm from "@/components/CodingForm";
import ResultsDisplay from "@/components/ResultsDisplay";
import type { CodingResponse } from "@/types";
import { useAuthStore } from "@/lib/auth";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [result, setResult] = useState<CodingResponse | null>(null);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.full_name?.split(" ")[0]} 👋
        </h1>
        <p className="text-gray-500 mt-1">
          Paste clinical text below to get AI-powered ICD-10 and CPT code suggestions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Left: Input */}
        <div className="card">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Clinical Text Input</h2>
          <CodingForm onResult={setResult} />
        </div>

        {/* Right: Results */}
        <div>
          {result ? (
            <div className="card">
              <h2 className="text-base font-semibold text-gray-900 mb-4">
                Coding Results
                <span className="ml-2 text-xs font-normal text-gray-400">
                  Session #{result.session_id.slice(0, 8)}
                </span>
              </h2>
              <ResultsDisplay result={result} />
            </div>
          ) : (
            <div className="card flex flex-col items-center justify-center py-20 text-center">
              <div className="h-16 w-16 rounded-full bg-medical-50 flex items-center justify-center mb-4">
                <svg className="h-8 w-8 text-medical-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-700 mb-1">No results yet</h3>
              <p className="text-sm text-gray-400 max-w-xs">
                Enter clinical text on the left and click "Analyze & Code" to get ICD-10 and CPT suggestions.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
