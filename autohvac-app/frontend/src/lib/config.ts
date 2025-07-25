/**
 * Centralized Configuration
 * Single source of truth for all application settings
 */

export const config = {
  // API Configuration
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    timeout: 10000, // 10 seconds
    retries: 3,
  },

  // Backend URLs
  backend: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  },

  // Upload Configuration
  upload: {
    maxFileSizeMB: 150,
    allowedTypes: ['application/pdf'],
    chunkSize: 1024 * 1024, // 1MB chunks
  },

  // UI Configuration
  ui: {
    polling: {
      interval: 2000, // 2 seconds
      maxRetries: 150, // 5 minutes total
    },
    toast: {
      duration: 5000, // 5 seconds
    },
  },

  // Development flags
  dev: {
    enableDebugLogs: process.env.NODE_ENV === 'development',
    enableMockData: false,
  },
} as const;

export type Config = typeof config;