import { mergeAttributes, Node } from "@tiptap/react";

declare module "@tiptap/react" {
  interface Commands<ReturnType> {
    citation: {
      insertCitation: (sourceId: string, sourceTitle: string) => ReturnType;
    };
  }
}

export const CitationExtension = Node.create({
  name: "citation",
  group: "inline",
  inline: true,
  atom: true,

  addAttributes() {
    return {
      sourceId: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute("data-source-id"),
        renderHTML: (attributes: { sourceId: string | null }) => ({
          "data-source-id": attributes.sourceId,
        }),
      },
      sourceTitle: {
        default: "Source",
        parseHTML: (element: HTMLElement) => element.textContent?.replace(/^📎\s*/, "") || "Source",
      },
    };
  },

  parseHTML() {
    return [{ tag: "span[data-source-id]" }];
  },

  renderHTML({ HTMLAttributes }) {
    const sourceTitle =
      typeof HTMLAttributes.sourceTitle === "string" ? HTMLAttributes.sourceTitle : "Source";

    return [
      "span",
      mergeAttributes(HTMLAttributes, {
        "data-source-id": HTMLAttributes.sourceId,
        class:
          "citation-chip inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-sm cursor-default",
      }),
      `📎 ${sourceTitle}`,
    ];
  },

  addCommands() {
    return {
      insertCitation:
        (sourceId: string, sourceTitle: string) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: { sourceId, sourceTitle },
          }),
    };
  },
});
