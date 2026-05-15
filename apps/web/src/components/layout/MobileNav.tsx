"use client";
import { Menu } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";

interface MobileNavProps {
  onOpen: () => void;
}

export function MobileNav({ onOpen }: MobileNavProps) {
  return (
    <div className="flex items-center border-b border-gray-800 bg-gray-900 px-4 py-2 md:hidden">
      <IconButton aria-label="Open navigation" onClick={onOpen}>
        <Menu size={18} />
      </IconButton>
      <span className="ml-3 text-sm font-semibold text-white">KnowledgeOS</span>
    </div>
  );
}
