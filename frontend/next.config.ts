import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // Remove console logs in production (security best practice)
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },

  // Note: Error overlay is development-only and automatically disabled in production.
  // Production errors are handled by app/error.tsx and ErrorBoundary components.
};

export default nextConfig;
