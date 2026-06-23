// /** @type {import('next').NextConfig} */
// const nextConfig = {
//   output: "standalone",
//   reactStrictMode: true,
//   env: {
//     NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
//   },
//   async headers() {
//     return [
//       {
//         source: "/(.*)",
//         headers: [
//           { key: "X-Frame-Options", value: "DENY" },
//           { key: "X-Content-Type-Options", value: "nosniff" },
//           { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
//           {
//             key: "Content-Security-Policy",
//             value: [
//               "default-src 'self'",
//               "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
//               "style-src 'self' 'unsafe-inline'",
//               "img-src 'self' data: blob:",
//               "connect-src 'self' http://localhost:8000",
//             ].join("; "),
//           },
//         ],
//       },
//     ];
//   },
// };

// module.exports = nextConfig;
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,

  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      "https://gmdprogrammer-medical-coding-ai-saas.hf.space/api/v1",
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              "font-src 'self' data:",
              "connect-src 'self' http://localhost:8000 https://gmdprogrammer-medical-coding-ai-saas.hf.space",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;