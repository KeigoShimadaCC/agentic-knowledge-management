import { mergeAttributes, Node } from "@tiptap/react";
import type { CommandProps } from "@tiptap/react";

export type CalloutTone = "info" | "warning" | "danger" | "success";

declare module "@tiptap/react" {
  interface Commands<ReturnType> {
    callout: {
      insertCallout: (tone?: CalloutTone) => ReturnType;
    };
  }
}

export const CalloutExtension = Node.create({
  name: "callout",
  group: "block",
  content: "block+",
  defining: true,

  addAttributes() {
    return {
      tone: {
        default: "info" as CalloutTone,
        parseHTML: (element: HTMLElement) => (element as HTMLElement).dataset.tone ?? "info",
        renderHTML: (attributes: { tone: CalloutTone }) => ({ "data-tone": attributes.tone }),
      },
    };
  },

  parseHTML() {
    return [{ tag: "div[data-callout]" }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["div", mergeAttributes({ "data-callout": "" }, HTMLAttributes), 0];
  },

  addCommands() {
    return {
      insertCallout:
        (tone: CalloutTone = "info") =>
        ({ commands }: CommandProps) =>
          commands.insertContent({
            type: this.name,
            attrs: { tone },
            content: [{ type: "paragraph" }],
          }),
    };
  },
});
