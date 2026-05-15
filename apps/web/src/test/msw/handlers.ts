import { http, HttpResponse } from "msw";

const API_BASE = "http://localhost:8000";

export const handlers = [
  http.get(`${API_BASE}/api/v1/auth/me`, () =>
    HttpResponse.json({
      user: {
        id: "user-1",
        email: "test@example.com",
        display_name: "Test User",
        created_at: "2026-05-15T00:00:00Z",
      },
    })
  ),
];
