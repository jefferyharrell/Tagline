'use client';

import { useCallback, useState } from 'react';
import { Upload, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';

interface CSVUploaderProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number; // in MB
  uploading?: boolean;
  progress?: number;
  error?: string | null;
}

export function CSVUploader({
  onFileSelect,
  accept = '.csv',
  maxSize = 10,
  uploading = false,
  progress = 0,
  error = null,
}: CSVUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleFile = useCallback((file: File) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return;
    }

    // Validate file size
    if (file.size > maxSize * 1024 * 1024) {
      return;
    }

    setSelectedFile(file);
    onFileSelect(file);
  }, [onFileSelect, maxSize]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFile(e.dataTransfer.files[0]);
      }
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      e.preventDefault();
      if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
      }
    },
    [handleFile]
  );

  const clearFile = () => {
    setSelectedFile(null);
  };

  return (
    <Card>
      <CardContent className="p-6">
        <form onSubmit={(e) => e.preventDefault()}>
          <input
            type="file"
            id="csv-upload"
            accept={accept}
            onChange={handleChange}
            className="hidden"
            disabled={uploading}
          />
          
          <label
            htmlFor="csv-upload"
            className={`
              relative flex flex-col items-center justify-center w-full h-48
              border-2 border-dashed rounded-lg cursor-pointer
              transition-colors duration-200
              ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
              ${uploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary hover:bg-primary/5'}
            `}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <Upload className="w-10 h-10 mb-3 text-muted-foreground" />
              <p className="mb-2 text-sm text-muted-foreground">
                <span className="font-semibold">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-muted-foreground">CSV files only (max {maxSize}MB)</p>
            </div>

            {dragActive && (
              <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-primary/50 backdrop-blur-sm">
                <p className="text-primary-foreground font-semibold text-lg">Drop the file here</p>
              </div>
            )}
          </label>
        </form>

        {selectedFile && !uploading && (
          <div className="mt-4 flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center space-x-3">
              <Upload className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={clearFile}
              type="button"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}

        {uploading && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Uploading...</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} />
          </div>
        )}

        {error && (
          <Alert variant="destructive" className="mt-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}