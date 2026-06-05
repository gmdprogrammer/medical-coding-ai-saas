"use client";
import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { Activity, Loader2, ArrowLeft, Mail } from "lucide-react";
import { authApi } from "@/lib/api";

const schema = z.object({
  email: z.string().email("Invalid email address"),
});
type FormData = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      await authApi.forgotPassword(data.email);
      setSubmitted(true);
      toast.success("Reset link generated!");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Something went wrong";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3">
            <Activity className="h-10 w-10 text-medical-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Reset your password</h1>
          <p className="text-gray-500 mt-1 text-sm">Medical Coding AI</p>
        </div>

        <div className="card">
          {submitted ? (
            <div className="text-center py-4">
              <div className="h-12 w-12 rounded-full bg-green-50 text-green-600 flex items-center justify-center mx-auto mb-4 border border-green-200">
                <Mail className="h-6 w-6" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Check your mail</h2>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed">
                If an account exists with that email, we have sent instructions to reset your password.
              </p>
              <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 mb-6 text-left">
                <strong>Local Test Mode:</strong> The password reset link has been printed to the backend terminal log.
              </div>
              <Link href="/auth/login" className="btn-secondary w-full text-center">
                Return to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <p className="text-sm text-gray-500 leading-relaxed">
                Enter the email address associated with your account, and we'll send you a link to reset your password.
              </p>

              <div>
                <label className="label">Email address</label>
                <input
                  {...register("email")}
                  type="email"
                  placeholder="you@hospital.com"
                  className="input"
                  autoComplete="email"
                />
                {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
              </div>

              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {loading ? "Sending link..." : "Send reset link"}
              </button>

              <Link href="/auth/login" className="flex items-center justify-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors mt-2 text-center">
                <ArrowLeft className="h-4 w-4" /> Back to sign in
              </Link>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
