"use client";

import { useState } from "react";
import type { ObjectOut } from "@/types";
import { AssetCard } from "./AssetCard";
import { AssetPreview } from "./AssetPreview";

interface AssetData {
  object: ObjectOut;
  contentType: string;
  sizeBytes: number;
}

interface AssetGridProps {
  assets: AssetData[];
}

export function AssetGrid({ assets }: AssetGridProps) {
  const [preview, setPreview] = useState<AssetData | null>(null);

  if (assets.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p>No assets yet. Upload files above.</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {assets.map((asset) => (
          <AssetCard
            key={asset.object.id}
            object={asset.object}
            contentType={asset.contentType}
            sizeBytes={asset.sizeBytes}
            assetId={asset.object.id}
            onClick={() => setPreview(asset)}
          />
        ))}
      </div>
      {preview && (
        <AssetPreview
          object={preview.object}
          contentType={preview.contentType}
          assetId={preview.object.id}
          onClose={() => setPreview(null)}
        />
      )}
    </>
  );
}
