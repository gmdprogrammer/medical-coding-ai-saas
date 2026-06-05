"use client";
import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Activity, Loader2, CheckCircle, XCircle } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth";

function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { fetchMe } = useAuthStore();
  const [verifying, setVerifying] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Verification token is missing.");
      setVerifying(false);
      return;
    }

    authApi.verifyEmail(token)
      .then(async () => {
        setSuccess(true);
        setVerifying(false);
        // Refresh authenticated user state if they are logged in
        await fetchMe();
        setTimeout(() => {
          router.push("/dashboard");
        }, 3000);
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || "Email verification failed.";
        setError(msg);
        setVerifying(false);
      });
  }, [token, fetchMe, router]);

  return (
    <div className="card">
      {verifying && (
        <div className="text-center py-6">
          <Loader2 className="h-8 w-8 animate-spin text-medical-600 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Verifying your email</h2>
          <p className="text-sm text-gray-500">Please wait while we confirm your verification link...</p>
        </div>
      )}

      {!verifying && success && (
        <div className="text-center py-6">
          <div className="h-12 w-12 rounded-full bg-green-50 text-green-600 flex items-center justify-center mx-auto mb-4 border border-green-200">
            <CheckCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Email verified successfully!</h2>
          <p className="text-sm text-gray-500 mb-6">
            Thank you for verifying your email. You will be redirected to your dashboard in 3 seconds.
          </p>
          <Link href="/dashboard" className="btn-primary w-full text-center">
            Go to Dashboard
          </Link>
        </div>
      )}

      {!verifying && error && (
        <div className="text-center py-6">
          <div className="h-12 w-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mx-auto mb-4 border border-red-200">
            <XCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Verification failed</h2>
          <p className="text-sm text-red-500 mb-6 font-medium">{error}</p>
          <div className="space-y-2">
            <Link href="/dashboard" className="btn-primary w-full text-center block">
              Go to Dashboard
            </Link>
            <Link href="/auth/login" className="btn-secondary w-full text-center block">
              Back to Sign In
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3">
            <Activity className="h-10 w-10 text-medical-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Email Verification</h1>
          <p className="text-gray-500 mt-1 text-sm">Medical Coding AI</p>
        </div>

        <Suspense fallback={
          <div className="card flex justify-center py-10">
            <Loader2 className="h-8 w-8 animate-spin text-medical-600" />
          </div>
        }>
          <VerifyEmailForm />
        </Suspense>
      </div>
    </div>
  );
}
