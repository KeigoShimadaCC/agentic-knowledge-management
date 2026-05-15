export interface ShortcutEntry {
  key: string;
  description: string;
  area: "Global" | "Search" | "Editor" | "Lists";
}

export const SHORTCUTS: ShortcutEntry[] = [
  // Global
  { key: "⌘K", description: "Open search", area: "Global" },
  { key: "⌘\\", description: "Collapse / expand sidebar", area: "Global" },
  { key: "?", description: "Show keyboard shortcuts", area: "Global" },

  // Search
  { key: "↑ / ↓", description: "Navigate results", area: "Search" },
  { key: "Enter", description: "Open selected result", area: "Search" },
  { key: "Esc", description: "Close search", area: "Search" },

  // Editor
  { key: "/", description: "Open slash menu (V2 mode)", area: "Editor" },
  { key: "⌘B", description: "Bold", area: "Editor" },
  { key: "⌘I", description: "Italic", area: "Editor" },
  { key: "⌘Shift+X", description: "Strikethrough", area: "Editor" },

  // Lists
  { key: "j / ↓", description: "Move highlight down", area: "Lists" },
  { key: "k / ↑", description: "Move highlight up", area: "Lists" },
  { key: "Enter", description: "Open highlighted item", area: "Lists" },
  { key: "o", description: "Open in side pane", area: "Lists" },
  { key: "Backspace", description: "Soft-delete highlighted item", area: "Lists" },
  { key: "Esc", description: "Clear highlight", area: "Lists" },
];

export const SHORTCUT_AREAS = ["Global", "Search", "Editor", "Lists"] as const;
export type ShortcutArea = (typeof SHORTCUT_AREAS)[number];
