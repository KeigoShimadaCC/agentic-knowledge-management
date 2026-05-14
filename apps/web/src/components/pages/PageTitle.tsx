"use client";

import { useRef } from "react";

interface PageTitleProps {
  initialTitle: string;
  onTitleChange: (title: string) => void;
}

export function PageTitle({ initialTitle, onTitleChange }: PageTitleProps) {
  const ref = useRef<HTMLHeadingElement>(null);

  function handleBlur() {
    onTitleChange(ref.current?.textContent ?? "");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      ref.current?.blur();
    }
  }

  return (
    <h1
      ref={ref}
      contentEditable
      suppressContentEditableWarning
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      className="text-4xl font-bold text-white outline-none empty:before:content-['Untitled'] empty:before:text-gray-600 mb-4 leading-tight"
    >
      {initialTitle}
    </h1>
  );
}
