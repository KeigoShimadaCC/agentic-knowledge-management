"use client";

import { useEffect } from "react";
import { X, Download } from "lucide-react";
import type { ObjectOut } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AssetPreviewProps {
  object: ObjectOut;
  contentType: string;
  assetId: string;
  onClose: () => void;
}

export function AssetPreview({ object, contentType, assetId, onClose }: AssetPreviewProps) {
  const isImage = contentType.startsWith("image/");
  const downloadUrl = `${BASE}/api/v1/assets/${assetId}/download`;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <div
        className="relative bg-gray-900 rounded-xl border border-gray-700 max-w-3xl w-full mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <span className="text-white font-medium truncate">{object.title}</span>
          <button onClick={onClose} className="text-gray-400 hover:text-white ml-2">
            <X size={18} />
          </button>
        </div>

        <div className="p-4">
          {isImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={downloadUrl}
              alt={object.title}
              className="max-h-[60vh] mx-auto object-contain rounded"
            />
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p className="mb-4">{contentType}</p>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-800">
          <a
            href={downloadUrl}
            download={object.title}
            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
          >
            <Download size={14} />
            Download
          </a>
        </div>
      </div>
    </div>
  );
}
