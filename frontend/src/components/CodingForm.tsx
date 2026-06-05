"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { Loader2, Sparkles, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { codingApi } from "@/lib/api";
import type { CodingResponse } from "@/types";

const schema = z.object({
  clinical_text: z.string().min(10, "Enter at least 10 characters").max(10000, "Text too long"),
  top_k_codes: z.number().int().min(1).max(10).default(5),
  include_explanation: z.boolean().default(true),
});
type FormData = z.infer<typeof schema>;

const EXAMPLE_NOTE = `Patient is a 62-year-old female presenting for a 25-minute established office visit.
PMH: Type 2 diabetes mellitus (A1C 8.4%), hypertension, hyperlipidemia.
Current medications: Metformin 1000mg BID, lisinopril 10mg daily, atorvastatin 40mg.
Vitals: BP 148/92, HR 82, SpO2 98%, BMI 31.2.
Labs reviewed: Comprehensive metabolic panel and CBC ordered. Chest X-ray (2 views) ordered for new productive cough x 2 weeks.
Assessment: Poorly controlled T2DM, essential hypertension, hyperlipidemia.
Plan: Increase metformin, add amlodipine 5mg. Follow up in 6 weeks.`;

interface Props {
  onResult: (result: CodingResponse) => void;
}

export default function CodingForm({ onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [showOptions, setShowOptions] = useState(false);

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { top_k_codes: 5, include_explanation: true },
  });

  const charCount = watch("clinical_text")?.length ?? 0;

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      const result = await codingApi.analyze(
        data.clinical_text,
        data.top_k_codes,
        data.include_explanation,
      );
      onResult(result);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Analysis failed. Please try again.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="label">Clinical Text</label>
          <span className="text-xs text-gray-400">{charCount}/10,000</span>
        </div>
        <textarea
          {...register("clinical_text")}
          rows={10}
          placeholder="Paste clinical notes, discharge summaries, procedure descriptions, or diagnosis text here...

PHI (patient names, dates of birth, phone numbers, SSNs) will be automatically detected and removed before AI processing."
          className="input resize-none font-mono text-sm leading-relaxed"
        />
        {errors.clinical_text && (
          <p className="mt-1 text-xs text-red-500">{errors.clinical_text.message}</p>
        )}
      </div>

      {/* PHI notice */}
      <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
        <span>
          Automatic PHI detection removes names, phone numbers, addresses, and IDs before
          AI processing. Raw text is never stored.
        </span>
      </div>

      {/* Advanced options */}
      <div>
        <button
          type="button"
          onClick={() => setShowOptions(!showOptions)}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700"
        >
          {showOptions ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          Advanced options
        </button>

        {showOptions && (
          <div className="mt-3 grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div>
              <label className="label text-xs">Max codes per type</label>
              <input
                type="number"
                min={1}
                max={10}
                {...register("top_k_codes", { valueAsNumber: true })}
                className="input text-sm"
              />
            </div>
            <div className="flex items-center gap-2 mt-5">
              <input type="checkbox" id="explanation" {...register("include_explanation")} className="h-4 w-4 accent-medical-600" />
              <label htmlFor="explanation" className="text-sm text-gray-700">Include explanation</label>
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <button type="submit" className="btn-primary flex-1" disabled={loading}>
          {loading
            ? <><Loader2 className="h-4 w-4 animate-spin" /> Analyzing...</>
            : <><Sparkles className="h-4 w-4" /> Analyze & Code</>
          }
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setValue("clinical_text", EXAMPLE_NOTE)}
        >
          Load example
        </button>
      </div>
    </form>
  );
}
