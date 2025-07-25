/**
 * JavaScript-compatible configuration
 * For use in API routes and other JS files
 */

export const config = {
  // API Configuration
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    timeout: 10000, // 10 seconds
  },

  // Backend URLs
  backend: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  },

  // Upload Configuration
  upload: {
    maxFileSizeMB: 150,
    allowedTypes: ['application/pdf'],
  },
};