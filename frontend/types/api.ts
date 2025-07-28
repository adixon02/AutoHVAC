// Shared API type definitions

export interface UploadRequest {
  file: File;
  email: string;
}

export interface UploadResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  request_id?: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    rooms?: Array<{
      name: string;
      area: number;
      heating_load?: number;
      cooling_load?: number;
    }>;
    loads?: {
      total_heating_btu: number;
      total_cooling_btu: number;
    };
  };
  error?: string;
}

export interface PaymentRequiredResponse {
  message: string;
  session_url: string;
}

export interface HealthCheckResponse {
  status: 'ok' | 'healthy';
  timestamp?: string;
}