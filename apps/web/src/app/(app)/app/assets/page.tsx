"use client";

import { useObjects } from "@/lib/hooks/useObjects";
import { AssetUploader } from "@/components/assets/AssetUploader";
import { AssetGrid } from "@/components/assets/AssetGrid";

export default function AssetsPage() {
  const { objects, mutate } = useObjects({ kind: "asset", limit: 100 });

  // For AssetGrid we need content_type and size_bytes — stored in the asset record
  // Since objects don't carry asset-specific fields, we render with placeholder data for now
  // Full integration requires fetching asset metadata separately (Phase 1 pragmatic approach)
  const assetData = objects.map((obj) => ({
    object: obj,
    contentType: "application/octet-stream",
    sizeBytes: 0,
  }));

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-4">Assets</h1>
        <AssetUploader onUploadComplete={() => mutate()} />
      </div>
      <AssetGrid assets={assetData} />
    </div>
  );
}
