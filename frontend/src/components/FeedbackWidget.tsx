"use client";
import { useState } from "react";
import { Star } from "lucide-react";
import toast from "react-hot-toast";
import { codingApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  sessionId: string;
}

export default function FeedbackWidget({ sessionId }: Props) {
  const [rating, setRating] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!rating) return;
    setLoading(true);
    try {
      await codingApi.submitFeedback({ session_id: sessionId, rating: rating as any, notes: notes || undefined });
      setSubmitted(true);
      toast.success("Feedback submitted — thank you!");
    } catch {
      toast.error("Failed to submit feedback");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
        <Star className="h-4 w-4 fill-green-500 text-green-500" />
        Feedback recorded. Thank you for helping improve accuracy!
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <p className="text-sm font-medium text-gray-700 mb-3">How accurate were these codes?</p>
      <div className="flex gap-1 mb-3">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => setRating(star)}
            className="transition-transform hover:scale-110"
          >
            <Star
              className={cn(
                "h-6 w-6 transition-colors",
                (hovered ?? rating ?? 0) >= star
                  ? "fill-yellow-400 text-yellow-400"
                  : "text-gray-300"
              )}
            />
          </button>
        ))}
        {rating && (
          <span className="ml-2 text-sm text-gray-500">
            {["", "Poor", "Fair", "Good", "Very good", "Excellent"][rating]}
          </span>
        )}
      </div>

      {rating && (
        <>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Optional: any corrections or notes..."
            className="input text-sm h-20 resize-none"
          />
          <button onClick={submit} disabled={loading} className="btn-primary mt-2 text-sm">
            {loading ? "Submitting..." : "Submit feedback"}
          </button>
        </>
      )}
    </div>
  );
}
