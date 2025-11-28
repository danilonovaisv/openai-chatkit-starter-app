import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Turbopack is the default in Next 16; keep the config empty to opt in without custom webpack overrides.
  turbopack: {},
};

export default nextConfig;
