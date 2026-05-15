import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { SWRConfig } from "swr";

import { listProjects } from "@/lib/api";
import { useProjects } from "@/lib/hooks/useProjects";

vi.mock("@/lib/api", () => ({
  listProjects: vi.fn(),
  getProject: vi.fn(),
  listResumeBulletSets: vi.fn(),
  listInterviewStories: vi.fn(),
}));

function wrapper({ children }: { children: ReactNode }) {
  return <SWRConfig value={{ provider: () => new Map() }}>{children}</SWRConfig>;
}

describe("useProjects", () => {
  it("passes status filter to listProjects", async () => {
    vi.mocked(listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 100,
      pages: 0,
    });

    renderHook(() => useProjects({ status: "completed" }), { wrapper });

    await waitFor(() => expect(listProjects).toHaveBeenCalled());
    expect(vi.mocked(listProjects).mock.calls[0]?.[0]).toMatchObject({
      status: "completed",
      limit: 100,
    });
  });

  it("handles empty response", async () => {
    vi.mocked(listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 100,
      pages: 0,
    });

    const { result } = renderHook(() => useProjects(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.projects).toEqual([]);
    expect(result.current.total).toBe(0);
  });
});
