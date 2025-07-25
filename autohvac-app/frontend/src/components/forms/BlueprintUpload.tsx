'use client';

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button, Card, CardHeader, CardTitle, CardContent, ProgressBar, Alert } from '@/components/ui';
import { ProjectData } from './ProjectForm';

export interface BlueprintUploadProps {
  projectData: ProjectData;
  onUploadComplete: (jobId: string, fileNames: string[]) => void;
  onError: (error: string) => void;
  onBack: () => void;
  onSwitchToManual: () => void;
}

const BlueprintUpload: React.FC<BlueprintUploadProps> = ({
  projectData,
  onUploadComplete,
  onError,
  onBack,
  onSwitchToManual
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0 && uploadedFiles.length === 0) return;

    // Check file size limits (100MB max)
    const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
    for (const file of acceptedFiles) {
      if (file.size > MAX_FILE_SIZE) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
        onError(`File "${file.name}" is too large (${sizeMB}MB). Maximum file size is 100MB. Please compress your blueprint or split into smaller files.`);
        return;
      }
    }

    // Use existing files if no new files provided (for "Process Files" button)
    const allFiles = acceptedFiles.length > 0 ? [...uploadedFiles, ...acceptedFiles] : uploadedFiles;
    
    // Only update uploaded files state if we have new files
    if (acceptedFiles.length > 0) {
      setUploadedFiles(allFiles);
    }
    
    setUploading(true);
    setUploadProgress(0);
    const fileSize = allFiles[0]?.size || 0;
    const fileSizeMB = (fileSize / (1024 * 1024)).toFixed(1);
    setProcessingStatus(`Uploading ${fileSizeMB}MB blueprint... This may take a few minutes for large files.`);

    try {
      // For MVP, we'll process one file at a time
      const file = allFiles[0];
      const formData = new FormData();
      formData.append('file', file);
      
      // Include project info
      formData.append('zip_code', projectData.zipCode);
      formData.append('project_name', projectData.projectName);
      formData.append('building_type', projectData.buildingType);
      formData.append('construction_type', projectData.constructionType);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      console.log('🚀 Uploading to V2 API:', `${apiUrl}/api/v2/blueprint/upload`);
      
      // Add timeout to fetch request - increased for large files
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout for large files
      
      const response = await fetch(`${apiUrl}/api/v2/blueprint/upload`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'omit',
      }).finally(() => clearTimeout(timeoutId));

      if (!response.ok) {
        let errorMessage = `Upload failed with status ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.user_message || errorData.message || errorMessage;
        } catch {
          const errorText = await response.text();
          errorMessage = errorText || errorMessage;
        }
        console.error('❌ Upload failed:', response.status, response.statusText, errorMessage);
        
        if (response.status === 413) {
          throw new Error(`File too large. Blueprint files must be under 100MB. Please compress your PDF or split into smaller files.`);
        } else if (response.status === 408 || response.status === 504) {
          throw new Error(`Upload timeout. Large files may take several minutes to upload. Please check your connection and try again.`);
        } else if (response.status === 400) {
          throw new Error(errorMessage);
        } else if (response.status === 500) {
          throw new Error(`Server error: ${errorMessage}. Our team has been notified.`);
        } else {
          throw new Error(`Upload failed: ${errorMessage}`);
        }
      }

      const data = await response.json();
      console.log('✅ Upload successful, job ID:', data.job_id);
      setProcessingStatus(`AI is analyzing your blueprint...`);
      
      // Start polling for processing status
      const jobId = data.job_id;
      const startTime = Date.now();
      const POLLING_TIMEOUT = 10 * 60 * 1000; // 10 minutes timeout
      
      const pollInterval = setInterval(async () => {
        // Check for timeout
        if (Date.now() - startTime > POLLING_TIMEOUT) {
          clearInterval(pollInterval);
          onError('Analysis timeout. Large blueprints may take longer than expected. Please try again or contact support.');
          setUploading(false);
          setUploadedFiles([]);
          return;
        }
        
        try {
          const statusResponse = await fetch(`${apiUrl}/api/v2/blueprint/status/${jobId}`);
          const statusData = await statusResponse.json();

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            setProcessingStatus(`Professional analysis complete! 🎉`);
            
            // Fetch the actual results to ensure they're ready
            try {
              const resultsResponse = await fetch(`${apiUrl}/api/v2/blueprint/results/${jobId}`);
              if (!resultsResponse.ok) {
                throw new Error(`Results not ready: ${resultsResponse.status}`);
              }
              
              const resultsData = await resultsResponse.json();
              console.log('✅ Results confirmed ready:', resultsData);
              
              // Pass the results data directly to avoid race condition
              onUploadComplete(jobId, [file.name]);
              
              setTimeout(() => {
                setUploading(false);
                setProcessingStatus('');
              }, 1000);
            } catch (resultsError) {
              console.error('❌ Results not ready yet, continuing to poll:', resultsError);
              // Continue polling - results might not be ready yet
              setProcessingStatus('Finalizing analysis results...');
            }
          } else if (statusData.status === 'error') {
            clearInterval(pollInterval);
            throw new Error(statusData.error || 'Processing failed');
          } else {
            // Update progress message
            setProcessingStatus(statusData.message || 'Processing blueprint...');
            setUploadProgress(statusData.progress || 50);
          }
        } catch (err) {
          clearInterval(pollInterval);
          onError(err instanceof Error ? err.message : 'Processing failed');
          setUploading(false);
          setUploadedFiles([]);
        }
      }, 3000);

    } catch (err) {
      console.error('❌ Upload error:', err);
      let errorMessage = 'Upload failed';
      
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMessage = 'Upload timed out after 5 minutes. Please check your connection and try again with a smaller file.';
        } else if (err.message.includes('Failed to fetch')) {
          errorMessage = 'Connection failed. Please check your internet connection and try again.';
        } else {
          errorMessage = err.message;
        }
      }
      
      onError(errorMessage);
      setUploading(false);
      setUploadedFiles([]);
    }
  }, [onUploadComplete, onError, uploadedFiles, projectData]);

  const processFiles = useCallback(async () => {
    if (uploadedFiles.length === 0) return;
    await onDrop([]);
  }, [uploadedFiles, onDrop]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: true,
    disabled: uploading,
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
  });

  if (uploading) {
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Analyzing Blueprint</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-center">
            <div className="animate-pulse">
              <div className="mx-auto h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <svg className="h-8 w-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Processing Your Blueprint</h3>
            <p className="text-gray-600 mb-4">{processingStatus}</p>
          </div>
          
          <ProgressBar progress={uploadProgress} />
          
          <div className="text-sm text-gray-500 space-y-1">
            <p>• AI is extracting room dimensions and details</p>
            <p>• Analyzing building characteristics</p>
            <p>• Preparing HVAC load calculations</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Upload Your Blueprint</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-colors duration-200
            ${isDragActive || dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
            ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />
          
          <div className="mx-auto h-12 w-12 text-gray-400 mb-4">
            <svg fill="none" stroke="currentColor" viewBox="0 0 48 48" aria-hidden="true">
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          {isDragActive ? (
            <p className="text-lg text-blue-600">Drop the blueprint here...</p>
          ) : (
            <>
              <p className="text-lg text-gray-600">
                {uploadedFiles.length === 0 
                  ? 'Drag & drop your blueprints here, or click to select'
                  : `${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''} selected - add more or click to process`
                }
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Supports PDF blueprint files up to 100MB - Large files may take 3-5 minutes to upload and analyze
              </p>
            </>
          )}
        </div>

        {/* File Preview Section */}
        {uploadedFiles.length > 0 && (
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold text-gray-700 mb-3">Selected Files ({uploadedFiles.length}):</h4>
            <div className="space-y-2">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-white p-3 rounded border">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{file.name}</p>
                      <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      const newFiles = uploadedFiles.filter((_, i) => i !== index);
                      setUploadedFiles(newFiles);
                    }}
                    className="text-red-500 hover:text-red-700 p-1"
                    title="Remove file"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-3 flex justify-between items-center">
              <button
                onClick={() => setUploadedFiles([])}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Clear All
              </button>
              <Button
                onClick={processFiles}
                disabled={uploadedFiles.length === 0}
              >
                Process {uploadedFiles.length} File{uploadedFiles.length > 1 ? 's' : ''}
              </Button>
            </div>
          </div>
        )}

        {/* Tips for best results */}
        <div className="text-sm text-gray-600">
          <p className="font-semibold mb-2">Tips for best results:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Upload all related blueprints (floor plans, elevations, details)</li>
            <li>Ensure blueprints are clear and readable</li>
            <li>Include room labels and dimensions when possible</li>
            <li>Higher resolution images work better</li>
            <li>Multiple files will be analyzed together as one project</li>
          </ul>
        </div>

        {/* Troubleshooting */}
        <Alert variant="info">
          <div className="space-y-2">
            <p><strong>Having trouble?</strong></p>
            <ul className="text-sm space-y-1">
              <li>• Blueprint not processing correctly? Try the manual entry option below</li>
              <li>• File too large? Compress your PDF or split into smaller files</li>
              <li>• Low quality scan? Consider re-scanning at higher resolution</li>
            </ul>
          </div>
        </Alert>

        {/* Form Actions */}
        <div className="flex justify-between pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={onBack}
          >
            Back to Project
          </Button>
          
          <Button
            type="button"
            variant="ghost"
            onClick={onSwitchToManual}
          >
            Switch to Manual Entry Instead
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export { BlueprintUpload };