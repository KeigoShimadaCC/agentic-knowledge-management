"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { clsx } from "clsx";
import { useUpload } from "@/lib/hooks/useUpload";

interface AssetUploaderProps {
  onUploadComplete?: () => void;
}

export function AssetUploader({ onUploadComplete }: AssetUploaderProps) {
  const { uploads, upload } = useUpload();
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    upload(Array.from(files));
    if (onUploadComplete) {
      setTimeout(onUploadComplete, 1500);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  const activeUploads = uploads.filter((u) => u.status === "uploading" || u.status === "pending");

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
          isDragging
            ? "border-blue-500 bg-blue-500/10"
            : "border-gray-700 hover:border-gray-500 hover:bg-gray-800/50"
        )}
      >
        <Upload size={24} className="mx-auto mb-2 text-gray-400" />
        <p className="text-sm text-gray-400">
          Drop files here or <span className="text-blue-400">browse</span>
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {activeUploads.length > 0 && (
        <div className="space-y-2">
          {activeUploads.map((u, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-sm text-gray-300 truncate flex-1">{u.file.name}</span>
              <div className="w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all"
                  style={{ width: `${u.progress}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 w-8">{u.progress}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
