import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Editor } from "@tiptap/react";
import { applyAiAction } from "../AiSlashCommand";

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));

import { toast } from "sonner";

function makeEditor(from = 10, to = 10) {
  const chain: Record<string, unknown> = {};
  chain.focus = vi.fn(() => chain);
  chain.deleteRange = vi.fn(() => chain);
  chain.insertContentAt = vi.fn(() => chain);
  chain.run = vi.fn();

  return {
    state: { selection: { from, to } },
    chain: vi.fn(() => chain),
    _chain: chain,
  } as unknown as Editor & { _chain: typeof chain };
}

describe("applyAiAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("inserts placeholder then replaces with result on success", async () => {
    const editor = makeEditor(10, 10);
    const chain = (editor as unknown as { _chain: Record<string, unknown> })._chain;
    const action = vi.fn().mockResolvedValue("Generated text");

    await applyAiAction(editor, "[AI writing…]", action);

    // placeholder was inserted at cursor
    expect(chain.insertContentAt).toHaveBeenCalledWith(10, "[AI writing…]");
    // action was called
    expect(action).toHaveBeenCalledOnce();
    // placeholder deleted and result inserted
    const placeholderTo = 10 + "[AI writing…]".length;
    expect(chain.deleteRange).toHaveBeenCalledWith({ from: 10, to: placeholderTo });
    expect(chain.insertContentAt).toHaveBeenCalledWith(10, "Generated text");
  });

  it("removes placeholder and calls toast.error on failure", async () => {
    const editor = makeEditor(10, 10);
    const chain = (editor as unknown as { _chain: Record<string, unknown> })._chain;
    const action = vi.fn().mockRejectedValue(new Error("Network error"));

    await applyAiAction(editor, "[AI writing…]", action);

    // placeholder was inserted
    expect(chain.insertContentAt).toHaveBeenCalledWith(10, "[AI writing…]");
    // placeholder deleted on error
    const placeholderTo = 10 + "[AI writing…]".length;
    expect(chain.deleteRange).toHaveBeenCalledWith({ from: 10, to: placeholderTo });
    // toast error shown
    expect(toast.error).toHaveBeenCalledWith("AI failed — try again");
    // result was NOT inserted
    expect(chain.insertContentAt).not.toHaveBeenCalledWith(10, "Generated text");
  });

  it("deletes existing selection before inserting placeholder", async () => {
    // from=5, to=15 means text is selected
    const editor = makeEditor(5, 15);
    const chain = (editor as unknown as { _chain: Record<string, unknown> })._chain;
    const action = vi.fn().mockResolvedValue("result");

    await applyAiAction(editor, "[AI writing…]", action);

    // selection deleted first
    expect(chain.deleteRange).toHaveBeenCalledWith({ from: 5, to: 15 });
    // placeholder inserted at selection start
    expect(chain.insertContentAt).toHaveBeenCalledWith(5, "[AI writing…]");
  });
});
