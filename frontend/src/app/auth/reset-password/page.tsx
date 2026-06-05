"use client";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { Activity, Loader2, KeyRound } from "lucide-react";
import { authApi } from "@/lib/api";

const schema = z.object({
  password: z.string()
    .min(8, "At least 8 characters")
    .regex(/[A-Z]/, "Must contain uppercase")
    .regex(/[0-9]/, "Must contain a number"),
  confirmPassword: z.string().min(1, "Please confirm password"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type FormData = z.infer<typeof schema>;

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    if (!token) {
      toast.error("Missing reset token");
      return;
    }
    setLoading(true);
    try {
      await authApi.resetPassword(token, data.password);
      setSuccess(true);
      toast.success("Password reset successfully!");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Password reset failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="text-center py-6">
        <p className="text-red-500 mb-4 font-medium">Invalid or missing password reset token.</p>
        <Link href="/auth/forgot-password" className="btn-primary inline-flex">
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <div className="card">
      {success ? (
        <div className="text-center py-4">
          <div className="h-12 w-12 rounded-full bg-green-50 text-green-600 flex items-center justify-center mx-auto mb-4 border border-green-200">
            <KeyRound className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Password changed</h2>
          <p className="text-sm text-gray-500 mb-6 leading-relaxed">
            Your password has been reset successfully. You can now sign in using your new credentials.
          </p>
          <Link href="/auth/login" className="btn-primary w-full text-center">
            Sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <p className="text-sm text-gray-500 leading-relaxed">
            Enter your new secure password below to update your account access.
          </p>

          <div>
            <label className="label">New Password</label>
            <input
              {...register("password")}
              type="password"
              placeholder="••••••••"
              className="input"
              autoComplete="new-password"
            />
            {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>}
          </div>

          <div>
            <label className="label">Confirm New Password</label>
            <input
              {...register("confirmPassword")}
              type="password"
              placeholder="••••••••"
              className="input"
              autoComplete="new-password"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-xs text-red-500">{errors.confirmPassword.message}</p>
            )}
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {loading ? "Resetting password..." : "Reset password"}
          </button>
        </form>
      )}
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3">
            <Activity className="h-10 w-10 text-medical-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Set new password</h1>
          <p className="text-gray-500 mt-1 text-sm">Medical Coding AI</p>
        </div>

        <Suspense fallback={
          <div className="card flex justify-center py-10">
            <Loader2 className="h-8 w-8 animate-spin text-medical-600" />
          </div>
        }>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
