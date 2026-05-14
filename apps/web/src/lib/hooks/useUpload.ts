"use client";

import { useState } from "react";
import type { AssetOut, ObjectOut } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UploadState {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  asset?: AssetOut;
  object?: ObjectOut;
  error?: string;
}

export function useUpload() {
  const [uploads, setUploads] = useState<UploadState[]>([]);

  function upload(files: File[]) {
    const newUploads: UploadState[] = files.map((file) => ({
      file,
      progress: 0,
      status: "pending",
    }));

    setUploads((prev) => [...prev, ...newUploads]);

    files.forEach((file, idx) => {
      const uploadIdx = uploads.length + idx;
      uploadFile(file, uploadIdx);
    });
  }

  function uploadFile(file: File, idx: number) {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const progress = Math.round((e.loaded / e.total) * 100);
        setUploads((prev) =>
          prev.map((u, i) =>
            i === idx ? { ...u, progress, status: "uploading" as const } : u
          )
        );
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText) as { object: ObjectOut; asset: AssetOut };
        setUploads((prev) =>
          prev.map((u, i) =>
            i === idx
              ? { ...u, progress: 100, status: "done" as const, asset: data.asset, object: data.object }
              : u
          )
        );
      } else {
        setUploads((prev) =>
          prev.map((u, i) =>
            i === idx ? { ...u, status: "error" as const, error: "Upload failed" } : u
          )
        );
      }
    };

    xhr.onerror = () => {
      setUploads((prev) =>
        prev.map((u, i) =>
          i === idx ? { ...u, status: "error" as const, error: "Network error" } : u
        )
      );
    };

    xhr.open("POST", `${BASE}/api/v1/assets/upload`);
    xhr.withCredentials = true;
    xhr.send(formData);
  }

  function clear() {
    setUploads([]);
  }

  return { uploads, upload, clear };
}
