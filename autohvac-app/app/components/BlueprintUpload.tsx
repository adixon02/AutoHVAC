import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { ProjectInfo } from '../lib/types';
import BlueprintAnalyzing from './BlueprintAnalyzing';

interface BlueprintUploadProps {
  onUploadComplete: (jobId: string, fileNames: string[]) => void;
  onError: (error: string) => void;
  projectInfo?: ProjectInfo | null;
}

export default function BlueprintUpload({ onUploadComplete, onError, projectInfo }: BlueprintUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentFileName, setCurrentFileName] = useState<string>('');

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    // If no new files and no existing files, return early
    if (acceptedFiles.length === 0 && uploadedFiles.length === 0) return;

    // Use existing files if no new files provided (for "Process Files" button)
    const allFiles = acceptedFiles.length > 0 ? [...uploadedFiles, ...acceptedFiles] : uploadedFiles;
    
    // Only update uploaded files state if we have new files
    if (acceptedFiles.length > 0) {
      setUploadedFiles(allFiles);
    }
    
    setUploading(true);
    setUploadProgress(0);
    setProcessingStatus(`Uploading ${allFiles.length} blueprint${allFiles.length > 1 ? 's' : ''}...`);

    try {
      const formData = new FormData();
      allFiles.forEach((file, index) => {
        formData.append(`files`, file);
      });

      // For MVP, we'll process one file at a time
      const file = allFiles[0];
      const singleFormData = new FormData();
      singleFormData.append('file', file);
      
      // Include project info if available
      if (projectInfo) {
        singleFormData.append('zip_code', projectInfo.zipCode);
        singleFormData.append('project_name', projectInfo.projectName);
        singleFormData.append('project_type', projectInfo.projectType);
        singleFormData.append('construction_type', projectInfo.constructionType);
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      console.log('🚀 Uploading to:', `${apiUrl}/api/blueprint/upload`);
      
      const response = await fetch(`${apiUrl}/api/blueprint/upload`, {
        method: 'POST',
        body: singleFormData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Upload failed:', response.status, response.statusText, errorText);
        throw new Error(`Upload failed: ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ Upload successful, job ID:', data.job_id);
      setProcessingStatus(`Generating professional HVAC analysis...`);
      setCurrentFileName(file.name);
      setIsAnalyzing(true);
      console.log('🔄 Showing analyzing screen for:', file.name);
      
      // Start polling for processing status
      const jobId = data.job_id;
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/blueprint/status/${jobId}`);
          const statusData = await statusResponse.json();

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            setProcessingStatus(`Professional analysis complete! 🎉`);
            onUploadComplete(jobId, [file.name]);
            setTimeout(() => {
              setUploading(false);
              setIsAnalyzing(false);
              setProcessingStatus('');
            }, 2000);
          } else if (statusData.status === 'error') {
            clearInterval(pollInterval);
            throw new Error(statusData.error || 'Processing failed');
          } else {
            // Update progress message
            setProcessingStatus(statusData.message || 'Processing blueprint...');
          }
        } catch (err) {
          clearInterval(pollInterval);
          onError(err instanceof Error ? err.message : 'Processing failed');
          setUploading(false);
          setIsAnalyzing(false);
          setUploadedFiles([]);
        }
      }, 3000);

    } catch (err) {
      onError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
      setIsAnalyzing(false);
      setUploadedFiles([]);
    }
  }, [onUploadComplete, onError, uploadedFiles]);

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
    disabled: uploading
  });

  // Show analyzing screen during processing
  if (isAnalyzing) {
    return (
      <BlueprintAnalyzing 
        processingStatus={processingStatus}
        fileName={currentFileName}
        onComplete={() => setIsAnalyzing(false)}
      />
    );
  }

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <svg
          className="mx-auto h-12 w-12 text-gray-400 mb-4"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {isDragActive ? (
          <p className="text-lg text-blue-600">Drop the blueprint here...</p>
        ) : uploading ? (
          <div>
            <p className="text-lg text-gray-600 mb-4">{processingStatus}</p>
            {uploadProgress > 0 && (
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            )}
          </div>
        ) : (
          <>
            <p className="text-lg text-gray-600">
              {uploadedFiles.length === 0 
                ? 'Drag & drop your blueprints here, or click to select'
                : `${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''} selected - add more or click to process`
              }
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Supports PDF blueprint files - Professional HVAC analysis in 2-3 minutes
            </p>
          </>
        )}
      </div>

      {/* File Preview Section */}
      {uploadedFiles.length > 0 && !uploading && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
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
            <button
              onClick={processFiles}
              disabled={uploadedFiles.length === 0}
              className="bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Process {uploadedFiles.length} File{uploadedFiles.length > 1 ? 's' : ''}
            </button>
          </div>
        </div>
      )}

      {!uploading && (
        <div className="mt-4 text-sm text-gray-600">
          <p className="font-semibold mb-2">Tips for best results:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Upload all related blueprints (floor plans, elevations, details)</li>
            <li>Ensure blueprints are clear and readable</li>
            <li>Include room labels and dimensions when possible</li>
            <li>Higher resolution images work better</li>
            <li>Multiple files will be analyzed together as one project</li>
            <li>Remove any sensitive information before uploading</li>
          </ul>
        </div>
      )}
    </div>
  );
}