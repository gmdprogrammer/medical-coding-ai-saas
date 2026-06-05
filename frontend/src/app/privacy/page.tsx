"use client";
import Link from "next/link";
import { Activity, ArrowLeft, ShieldAlert } from "lucide-react";

export default function PrivacyPage() {
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

        <h1 className="text-3xl font-extrabold text-gray-900 mb-2">Privacy Policy</h1>
        <p className="text-xs text-gray-400 mb-8 font-mono">Last Updated: June 3, 2026</p>

        <div className="prose prose-sm text-gray-600 space-y-6 leading-relaxed">
          <div className="bg-medical-50/50 border border-medical-200/60 rounded-xl p-4 flex gap-3 text-xs text-medical-800 mb-6">
            <ShieldAlert className="h-5 w-5 text-medical-600 flex-shrink-0 mt-0.5" />
            <div>
              <strong>Privacy First:</strong> We operate under a zero-retention PHI policy. We do not store raw clinical text, and all AI queries are routed through an anonymous pre-processing gateway.
            </div>
          </div>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">1. Information We Collect</h2>
            <p>
              We collect user account identifiers (such as name, email address, password hash, and organization name) to manage platform authentication and billing access. We do NOT collect patient clinical records or identities.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">2. Processing of Clinical Notes (PHI)</h2>
            <p>
              When clinical text is entered into our analyzer:
            </p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>A local scrubbing regex client strips obvious identifiers.</li>
              <li>A backend server-side anonymization middleware filters names, SSNs, phone numbers, and location strings.</li>
              <li>Only the anonymized clinical symptoms/assessments are sent to the Groq inference engine.</li>
              <li>We do NOT store or log the raw clinical text in our databases. We only store the generated ICD-10 code outputs and metadata (such as timestamps and confidence averages) for audit histories.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">3. Third-Party Data Sharing</h2>
            <p>
              We do not sell, rent, or trade your personal data. We utilize third-party sub-processors (such as Stripe for payments and secure cloud hosting providers) only to deliver critical app infrastructure. These providers are strictly bound by confidentiality and HIPAA-aligned security controls.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">4. Data Security</h2>
            <p>
              We implement industry-standard administrative, physical, and technical safeguards. All data in transit is encrypted using HTTPS (TLS 1.3), and static data is encrypted under AES-256 standards.
            </p>
          </section>

          <section>
            <h2 className="text-base font-bold text-gray-900 mb-2">5. Access and Deletion Rights</h2>
            <p>
              You have the right to request deletion of your account and all associated audit histories. To request account deletion, contact our support team.
            </p>
          </section>
        </div>

        <div className="mt-12 border-t border-neutral-100 pt-6 text-center text-xs text-gray-400">
          © 2026 Medical Coding AI · <Link href="/terms" className="hover:underline text-medical-600">Terms of Service</Link>
        </div>
      </div>
    </div>
  );
}
