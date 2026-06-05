"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navigation from "@/components/Navigation";
import { useAuthStore } from "@/lib/auth";
import { authApi } from "@/lib/api";
import toast from "react-hot-toast";
import { AlertCircle, Loader2 } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, fetchMe } = useAuthStore();
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!user) {
      fetchMe().then(() => {
        if (!useAuthStore.getState().user) {
          router.replace("/auth/login");
        }
      });
    }
  }, [user, fetchMe, router]);

  const handleResend = async () => {
    setResending(true);
    try {
      await authApi.requestEmailVerification();
      toast.success("Verification link sent! Check your inbox.");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to request verification email.";
      toast.error(msg);
    } finally {
      setResending(false);
    }
  };

  if (!user) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin h-8 w-8 border-4 border-medical-600 border-t-transparent rounded-full" />
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <Navigation />
      <main className="flex-1 overflow-auto flex flex-col">
        {user && !user.is_verified && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex items-center justify-between text-amber-800 text-sm gap-2 flex-shrink-0">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0" />
              <span>
                Your email (<strong>{user.email}</strong>) is not verified. Please verify your account.
              </span>
            </div>
            <button
              onClick={handleResend}
              disabled={resending}
              className="inline-flex items-center gap-1 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded px-2.5 py-1 transition-colors disabled:opacity-60 flex-shrink-0"
            >
              {resending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
              {resending ? "Sending..." : "Resend Link"}
            </button>
          </div>
        )}
        <div className="flex-1">
          {children}
        </div>
      </main>
    </div>
  );
}
