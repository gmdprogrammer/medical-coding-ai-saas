"use client";
import Link from "next/link";
import { Activity, ArrowLeft } from "lucide-react";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-neutral-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white border border-neutral-200 rounded-2xl p-8 sm:p-10 shadow-sm">
        {/* Back Link */}
        <div className="mb-8 flex items-center justify-between">
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors">
            <ArrowLeft className="h-4 w-4" /> Back to Home
          </Link>
          <div className="flex items-center gap-1.5 font-bold text-gray-900 text-sm">
            <Activity className="h-5 w-5 text-medical-600" /> Medical Coding AI
          </div>
        </div>

        <h1 className="text-3xl font-extrabold text-gray-900 mb-2">Terms of Service</h1>
        <p className="text-xs text-gray-400 mb-8 font-mono">Last Updated: June 3, 2026</p>

        <div className="prose prose-sm text-gray-600 space-y-6 leading-relaxed">
          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">1. Agreement to Terms</h2>
            <p>
              By accessing or using Medical Coding AI (the "Service"), you agree to be bound by these Terms of Service. If you do not agree, you are prohibited from using the platform.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">2. Clinical Coding Assistant Status</h2>
            <p>
              Medical Coding AI is an artificial intelligence decision-support tool. It is NOT a replacement for qualified medical professionals, clinical documentation improvement (CDI) specialists, or certified medical coders. All code suggestions, confidence values, and audits provided must be reviewed, edited, and approved by a certified human coder before submission to insurance claims or EHR files. The licensee assumes full responsibility for claim accuracy.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">3. HIPAA and PHI</h2>
            <p>
              The Service employs client-side and server-side anonymization pipelines to detect and strip Protected Health Information (PHI) before AI ingestion. Users are strictly prohibited from bypassing these filters or manually inserting raw patient identifiers where they are not automatically redacted.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">4. User Registration and Account Security</h2>
            <p>
              You must provide accurate information when registering. You are entirely responsible for maintaining the confidentiality of your credentials and account access. Unauthorized sharing of credentials (including shared logins) is strictly prohibited.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">5. Billing, Upgrades, and Usage</h2>
            <p>
              Free accounts are limited to 50 coding sessions per month. Upgraded monthly plans are subject to recurring credit card charges. All payments are non-refundable unless specified under our premium guarantee. Quotas reset automatically on the 1st of each month.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">6. Limitation of Liability</h2>
            <p>
              Under no circumstances shall Medical Coding AI be liable for any direct, indirect, consequential, or punitive damages (including claim rejections, insurance audit penalties, billing delays, or lost revenues) arising from your use of clinical suggestions.
            </p>
          </section>
        </div>

        <div className="mt-12 border-t border-neutral-100 pt-6 text-center text-xs text-gray-400">
          © 2026 Medical Coding AI · <Link href="/privacy" className="hover:underline text-medical-600">Privacy Policy</Link>
        </div>
      </div>
    </div>
  );
}
