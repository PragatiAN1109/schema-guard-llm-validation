/** @type {import('next').NextConfig} */
const path = require('path');

// NEXT_PUBLIC_API_URL is set in Render/Vercel/Railway dashboard.
// Falls back to localhost:8000 for local development.
// Must be a full URL with protocol (https://...) for production.
const API_URL = process.env.NEXT_PUBLIC_API_URL
  ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '') // strip trailing slash
  : 'http://localhost:8000';

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_URL}/api/:path*`,
      },
    ];
  },
  webpack(config) {
    config.resolve.alias['@'] = path.resolve(__dirname);
    return config;
  },
};

module.exports = nextConfig;
