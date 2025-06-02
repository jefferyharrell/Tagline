import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  serverExternalPackages: [],
  // Fix Docker file watching issues
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        ...config.watchOptions,
        poll: 1000,
        aggregateTimeout: 300,
        ignored: [
          "**/node_modules/**",
          "**/.next/**",
          "**/next.config.*",
          "**/.git/**",
          "**/docker-compose*.yml",
          "**/Dockerfile*",
          "**/.dockerignore",
        ],
      };
    }
    return config;
  },
};

export default nextConfig;
