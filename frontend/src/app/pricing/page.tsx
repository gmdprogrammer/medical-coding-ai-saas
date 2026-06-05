"use client";
import { useState } from "react";
import Link from "next/link";
import { Check, ShieldCheck, HelpCircle, Activity, Loader2, ArrowRight } from "lucide-react";
import toast from "react-hot-toast";

const PLANS = [
  {
    name: "Developer Free",
    price: "$0",
    desc: "For small practices and developers getting started.",
    features: [
      "50 analyses per month",
      "ICD-10-CM / PCS recommendations",
      "CPT / HCPCS Level II suggestions",
      "Automated HIPAA PHI scrubbing",
      "Audit trail history logging",
      "Community support",
    ],
    cta: "Current Plan",
    popular: false,
    allowed: false,
  },
  {
    name: "Professional Pro",
    price: "$79",
    period: "/month",
    desc: "Perfect for busy medical coders and clinics.",
    features: [
      "Unlimited AI analyses",
      "Prioritized Groq speed (llama-3 70b)",
      "Smart code explanation audit trails",
      "Export to CSV / Excel reports",
      "Direct code correction feedback loop",
      "Priority email & chat support",
      "100% HIPAA Business Associate (BAA) aligned",
    ],
    cta: "Upgrade to Pro",
    popular: true,
    allowed: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    desc: "For hospitals, large clinics, and custom EHR integrations.",
    features: [
      "Custom fine-tuned AI model weights",
      "Full API endpoints access",
      "Direct EHR integrations (Epic, Cerner, etc.)",
      "Dedicated account manager",
      "99.9% uptime SLA guarantee",
      "Single Sign-On (SAML / SSO)",
      "On-premises offline hosting options",
    ],
    cta: "Contact Sales",
    popular: false,
    allowed: true,
  },
];

const FAQS = [
  {
    q: "Is this platform really HIPAA-compliant?",
    a: "Yes. Our client-side and server-side PHI anonymization pipeline detects and redacts patient identifiers (names, phone numbers, SSNs, dates of birth, and emails) before any data is sent to the AI model. No Protected Health Information (PHI) is ever logged or stored on our servers.",
  },
  {
    q: "Can I cancel or change my plan later?",
    a: "Absolutely. You can change your plan or cancel your monthly subscription at any time directly from your Account Settings Billing panel. No questions asked.",
  },
  {
    q: "Do you offer hospital enterprise billing?",
    a: "Yes, we support hospital group licenses, purchase orders, customized SLAs, and direct invoicing. Contact our sales team for custom procurement contracts.",
  },
];

export default function PricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [checkoutPlan, setCheckoutPlan] = useState<string | null>(null);

  const handleSelectPlan = (planName: string, isAllowed: boolean) => {
    if (!isAllowed) return;
    if (planName === "Enterprise") {
      window.location.href = "mailto:sales@medicalcodingai.com?subject=Enterprise%20Plan%20Inquiry";
      return;
    }
    setLoadingPlan(planName);
    setTimeout(() => {
      setCheckoutPlan(planName);
      setLoadingPlan(null);
    }, 1200);
  };

  const handleSimulatePayment = () => {
    setLoadingPlan("payment");
    setTimeout(() => {
      toast.success("Successfully upgraded to Pro! Your account limits have been lifted.");
      setCheckoutPlan(null);
      setLoadingPlan(null);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-neutral-50 py-12 px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-4xl mx-auto text-center mb-16">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-medical-600 hover:text-medical-700 font-bold mb-4">
          <Activity className="h-5 w-5" /> Medical Coding AI
        </Link>
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight sm:text-5xl">
          Simple, transparent pricing
        </h1>
        <p className="mt-4 text-xl text-gray-500">
          Scrub PHI, suggest ICD-10 codes, and speed up clinical billing in seconds.
        </p>
      </div>

      {/* Grid */}
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 items-start mb-20">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`card flex flex-col justify-between h-full transition-transform hover:-translate-y-1 relative ${
              plan.popular ? "border-medical-500 shadow-md ring-2 ring-medical-500/20" : ""
            }`}
          >
            {plan.popular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-medical-600 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                Most Popular
              </span>
            )}
            <div>
              <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
              <p className="mt-2 text-sm text-gray-500 min-h-[40px]">{plan.desc}</p>
              <div className="my-6">
                <span className="text-4xl font-extrabold text-gray-900">{plan.price}</span>
                {plan.period && <span className="text-sm font-medium text-gray-500">{plan.period}</span>}
              </div>

              <ul className="space-y-3 mb-8 border-t border-neutral-100 pt-6">
                {plan.features.map((feat) => (
                  <li key={feat} className="flex items-start gap-2.5 text-sm text-gray-700">
                    <Check className="h-4.5 w-4.5 text-medical-600 mt-0.5 flex-shrink-0" />
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            <button
              onClick={() => handleSelectPlan(plan.name, plan.allowed)}
              disabled={!plan.allowed || loadingPlan !== null}
              className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm transition-colors flex items-center justify-center gap-1.5 ${
                !plan.allowed
                  ? "bg-neutral-100 text-neutral-400 cursor-not-allowed"
                  : plan.popular
                  ? "bg-medical-600 text-white hover:bg-medical-700 shadow-sm"
                  : "bg-white border border-neutral-300 text-neutral-700 hover:bg-neutral-50"
              }`}
            >
              {loadingPlan === plan.name ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {plan.cta}
            </button>
          </div>
        ))}
      </div>

      {/* Security notice */}
      <div className="max-w-3xl mx-auto bg-white border border-neutral-200/80 rounded-2xl p-6 mb-20 flex flex-col sm:flex-row items-center gap-4">
        <div className="h-12 w-12 rounded-full bg-medical-50 border border-medical-200 flex items-center justify-center flex-shrink-0">
          <ShieldCheck className="h-6 w-6 text-medical-600" />
        </div>
        <div>
          <h4 className="text-sm font-bold text-gray-900">Secure Payment Guarantee</h4>
          <p className="text-sm text-gray-500 mt-0.5 leading-relaxed">
            All subscriptions are processed securely using bank-grade AES-256 SSL encryption. We never store your full credit card credentials. Cancel online anytime with one click.
          </p>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="max-w-3xl mx-auto mb-16">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Frequently Asked Questions</h2>
        <div className="space-y-6">
          {FAQS.map((faq, i) => (
            <div key={i} className="card p-5 bg-white">
              <h3 className="text-base font-semibold text-gray-900 flex items-start gap-2">
                <HelpCircle className="h-5 w-5 text-medical-500 mt-0.5 flex-shrink-0" />
                {faq.q}
              </h3>
              <p className="mt-2 text-sm text-gray-600 pl-7 leading-relaxed">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="text-center text-xs text-gray-400">
        © 2024 Medical Coding AI · All rights reserved. <Link href="/terms" className="hover:underline">Terms</Link> · <Link href="/privacy" className="hover:underline">Privacy</Link>
      </div>

      {/* Payment checkout simulation Modal */}
      {checkoutPlan && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="card w-full max-w-md p-6 bg-white shadow-2xl relative" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Simulate Stripe Checkout</h3>
            <p className="text-xs text-gray-500 mb-6">
              You are subscribing to the <strong>{checkoutPlan}</strong> plan ($79/mo).
            </p>

            <div className="space-y-4 mb-6">
              <div>
                <label className="label text-xs">Card Number</label>
                <input type="text" className="input text-sm" value="4242 •••• •••• 4242" disabled />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label text-xs">Expires</label>
                  <input type="text" className="input text-sm" value="12 / 28" disabled />
                </div>
                <div>
                  <label className="label text-xs">CVC</label>
                  <input type="text" className="input text-sm" value="***" disabled />
                </div>
              </div>
            </div>

            <div className="flex gap-3 justify-end border-t border-neutral-100 pt-4">
              <button
                onClick={() => setCheckoutPlan(null)}
                disabled={loadingPlan === "payment"}
                className="btn-secondary text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSimulatePayment}
                disabled={loadingPlan === "payment"}
                className="btn-primary text-xs flex items-center gap-1.5"
              >
                {loadingPlan === "payment" ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                {loadingPlan === "payment" ? "Processing..." : "Complete Payment"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
