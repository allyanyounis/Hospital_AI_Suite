import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // The browser only talks to this origin; /api/* is proxied to the FastAPI backend, so the session cookie is
  // first-party and no CORS is needed. (WebSockets connect to the backend directly, see lib/api/client.ts.)
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  experimental: {
    // Drafting a note can take longer than the default 30s proxy timeout
    proxyTimeout: 120_000,
  },
};

export default nextConfig;
