import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { SWRConfig } from "swr";
import { useAuth } from "@/lib/hooks/useAuth";
import { server } from "@/test/msw/server";

const API_BASE = "http://localhost:8000";

function wrapper({ children }: { children: React.ReactNode }) {
  return <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>{children}</SWRConfig>;
}

describe("useAuth", () => {
  it("loads the current user and clears when the auth cache is reset", async () => {
    const user = {
      id: "user-1",
      email: "test@example.com",
      display_name: "Test User",
      created_at: "2026-05-15T00:00:00Z",
    };

    server.use(
      http.get(`${API_BASE}/api/v1/auth/me`, () => HttpResponse.json({ user }))
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.user).toEqual(user));
    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => {
      await result.current.mutate(undefined, { revalidate: false });
    });

    expect(result.current.user).toBeUndefined();
    expect(result.current.isAuthenticated).toBe(false);
  });
});
