export interface TutorialStep {
  id: string;
  title: string;
  body: string;
  target?: string;
  position?: "top" | "bottom" | "left" | "right" | "center";
  navigateTo?: string;
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: "welcome",
    title: "Welcome to KnowledgeOS",
    body: "Take a quick tour through pages, sources, search, graph links, chats, and MCP access.",
    position: "center",
  },
  {
    id: "sidebar",
    title: "Your Sidebar",
    body: "Use the sidebar to move between the main KnowledgeOS surfaces.",
    target: '[data-tutorial="sidebar"]',
    position: "right",
  },
  {
    id: "pages",
    title: "Pages — Your Notes",
    body: "Pages are where your durable notes and working documents live.",
    target: '[data-tutorial="nav-pages"]',
    position: "right",
    navigateTo: "/app/pages",
  },
  {
    id: "new-page",
    title: "Create a Page",
    body: "Create a blank page when you want to capture or develop an idea.",
    target: '[data-tutorial="new-page-btn"]',
    position: "bottom",
  },
  {
    id: "search",
    title: "Search Everything",
    body: "Search across your pages, sources, chats, and other objects from anywhere.",
    target: '[data-tutorial="search-trigger"]',
    position: "bottom",
  },
  {
    id: "sources",
    title: "Sources — Ingest the Web",
    body: "Sources hold imported web pages, PDFs, and other reference material.",
    target: '[data-tutorial="nav-sources"]',
    position: "right",
    navigateTo: "/app/sources",
  },
  {
    id: "graph",
    title: "Knowledge Graph",
    body: "Graph panels show how objects connect through backlinks, related items, and AI-suggested links.",
    target: '[data-tutorial="related-panel"]',
    position: "left",
  },
  {
    id: "chats",
    title: "AI Assistant",
    body: "Chats let you bring assistant conversations into your searchable workspace.",
    target: '[data-tutorial="nav-chats"]',
    position: "right",
    navigateTo: "/app/chats",
  },
  {
    id: "mcp",
    title: "MCP Agent Access",
    body: "This footer area is where account, appearance, and tour controls live while MCP access evolves.",
    target: '[data-tutorial="sidebar-footer"]',
    position: "top",
  },
  {
    id: "done",
    title: "You're all set!",
    body: "You can replay this tour from the sidebar footer whenever you need a refresher.",
    position: "center",
  },
];
