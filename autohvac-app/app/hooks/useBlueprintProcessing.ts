'use client';

import { useState, useCallback } from 'react';
import { ProjectInfo } from '../lib/types';

interface UseBlueprintProcessingReturn {
  // State
  blueprintJobId: string | null;
  professionalAnalysis: any | null;
  isProcessing: boolean;
  processingError: string | null;
  
  // Actions
  handleBlueprintUpload: (jobId: string, fileNames: string[]) => Promise<void>;
  handleBlueprintError: (error: string) => void;
  clearBlueprintData: () => void;
  
  // Computed
  hasAnalysis: boolean;
}

export function useBlueprintProcessing(): UseBlueprintProcessingReturn {
  const [blueprintJobId, setBlueprintJobId] = useState<string | null>(null);
  const [professionalAnalysis, setProfessionalAnalysis] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState<string | null>(null);

  const handleBlueprintUpload = useCallback(async (jobId: string, fileNames: string[]) => {
    console.log('🎯 handleBlueprintUpload called with jobId:', jobId, 'files:', fileNames);
    setBlueprintJobId(jobId);
    setIsProcessing(true);
    setProcessingError(null);
    
    try {
      console.log('📡 Fetching results from:', `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/blueprint/results/${jobId}`);
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/blueprint/results/${jobId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('📊 Professional analysis data received:', data);
      
      if (data.status === 'completed') {
        console.log('✅ Analysis completed successfully!');
        setProfessionalAnalysis(data);
      } else {
        throw new Error(`Analysis status: ${data.status}. Expected 'completed'.`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('❌ Failed to get analysis results:', error);
      setProcessingError(`API Error: ${errorMessage}`);
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const handleBlueprintError = useCallback((error: string) => {
    console.error('Blueprint upload error:', error);
    setProcessingError(`Blueprint processing failed: ${error}`);
    setIsProcessing(false);
  }, []);

  const clearBlueprintData = useCallback(() => {
    setBlueprintJobId(null);
    setProfessionalAnalysis(null);
    setIsProcessing(false);
    setProcessingError(null);
  }, []);

  const hasAnalysis = professionalAnalysis !== null;

  return {
    // State
    blueprintJobId,
    professionalAnalysis,
    isProcessing,
    processingError,
    
    // Actions
    handleBlueprintUpload,
    handleBlueprintError,
    clearBlueprintData,
    
    // Computed
    hasAnalysis,
  };
}