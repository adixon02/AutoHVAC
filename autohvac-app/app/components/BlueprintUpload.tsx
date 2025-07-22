import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface BlueprintUploadProps {
  onUploadComplete: (jobId: string, fileName: string) => void;
  onError: (error: string) => void;
}

export default function BlueprintUpload({ onUploadComplete, onError }: BlueprintUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState<string>('');

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploading(true);
    setUploadProgress(0);
    setProcessingStatus('Uploading blueprint...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/blueprint/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setProcessingStatus('Processing blueprint...');
      
      // Start polling for processing status
      const jobId = data.job_id;
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/blueprint/status/${jobId}`);
          const statusData = await statusResponse.json();

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            setProcessingStatus('Blueprint processed successfully!');
            onUploadComplete(jobId, file.name);
            setTimeout(() => {
              setUploading(false);
              setProcessingStatus('');
            }, 2000);
          } else if (statusData.status === 'error') {
            clearInterval(pollInterval);
            throw new Error(statusData.error || 'Processing failed');
          }
        } catch (err) {
          clearInterval(pollInterval);
          onError(err instanceof Error ? err.message : 'Processing failed');
          setUploading(false);
        }
      }, 2000);

    } catch (err) {
      onError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  }, [onUploadComplete, onError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'application/acad': ['.dwg'],
      'application/dxf': ['.dxf']
    },
    maxFiles: 1,
    disabled: uploading
  });

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
              Drag & drop your blueprint here, or click to select
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Supports PDF, PNG, JPG, DWG, and DXF files
            </p>
          </>
        )}
      </div>

      {!uploading && (
        <div className="mt-4 text-sm text-gray-600">
          <p className="font-semibold mb-2">Tips for best results:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Ensure blueprints are clear and readable</li>
            <li>Include floor plan with room labels</li>
            <li>Higher resolution images work better</li>
            <li>Remove any sensitive information before uploading</li>
          </ul>
        </div>
      )}
    </div>
  );
}