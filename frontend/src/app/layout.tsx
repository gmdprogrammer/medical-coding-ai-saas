import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "Medical Coding AI",
  description: "HIPAA-aligned ICD-10 & CPT coding assistant powered by AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-neutral-50 text-neutral-900 antialiased font-sans">
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: { background: "#1e293b", color: "#f8fafc", fontSize: "14px" },
          }}
        />
      </body>
    </html>
  );
}
