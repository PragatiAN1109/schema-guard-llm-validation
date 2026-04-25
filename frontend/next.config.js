/** @type {import('next').NextConfig} */
const path = require('path');

// In production (Render/Vercel/Railway), set NEXT_PUBLIC_API_URL to your backend URL.
// Locally it falls back to http://localhost:8000.
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_URL}/:path*`,
      },
    ];
  },
  webpack(config) {
    config.resolve.alias['@'] = path.resolve(__dirname);
    return config;
  },
};

module.exports = nextConfig;
