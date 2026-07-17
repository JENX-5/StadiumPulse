import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/config", () => ({
  config: { apiUrl: "http://test-host/api/v1", wsUrl: "ws://test-host/ws" },
}));

import { apiRequest, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/useAuthStore";

function mockFetchResponse({
  status,
  ok,
  body,
  json = true,
}: {
  status: number;
  ok: boolean;
  body?: unknown;
  json?: boolean;
}) {
  return {
    status,
    ok,
    statusText: "Error",
    headers: {
      get: (name: string) => (json && name === "content-type" ? "application/json" : null),
    },
    json: async () => body,
  } as unknown as Response;
}

describe("apiRequest", () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, user: null, isAuthenticated: false });
    global.fetch = vi.fn();
  });

  it("issues a GET with no Authorization header when unauthenticated", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({ status: 200, ok: true, body: { ok: true } })
    );

    await apiRequest("/zones");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://test-host/api/v1/zones",
      expect.objectContaining({
        method: "GET",
        headers: expect.not.objectContaining({ Authorization: expect.anything() }),
      })
    );
  });

  it("attaches the bearer token from useAuthStore when present", async () => {
    useAuthStore.setState({ token: "abc123", user: null, isAuthenticated: true });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({ status: 200, ok: true, body: {} })
    );

    await apiRequest("/state/venue-1");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://test-host/api/v1/state/venue-1",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer abc123" }),
      })
    );
  });

  it("JSON-encodes a body and sets Content-Type application/json by default", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({ status: 201, ok: true, body: { id: "1" } })
    );

    await apiRequest("/incidents/", { method: "POST", body: { raw_text: "spill" } });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://test-host/api/v1/incidents/",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ raw_text: "spill" }),
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      })
    );
  });

  it("passes a form body through as-is with urlencoded Content-Type", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({ status: 200, ok: true, body: { access_token: "t", token_type: "bearer" } })
    );

    const formBody = new URLSearchParams({ username: "a@b.com", password: "pw" }).toString();
    await apiRequest("/auth/token", { method: "POST", body: formBody, form: true });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://test-host/api/v1/auth/token",
      expect.objectContaining({
        body: formBody,
        headers: expect.objectContaining({
          "Content-Type": "application/x-www-form-urlencoded",
        }),
      })
    );
  });

  it("returns undefined for a 204 response without parsing a body", async () => {
    const response = mockFetchResponse({ status: 204, ok: true });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(response);
    const jsonSpy = vi.spyOn(response, "json");

    const result = await apiRequest("/incidents/1");

    expect(result).toBeUndefined();
    expect(jsonSpy).not.toHaveBeenCalled();
  });

  it("returns the parsed JSON payload on success", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({ status: 200, ok: true, body: { id: "zone-1", risk: 0.5 } })
    );

    const result = await apiRequest("/risk/venue-1/zones/zone-1");

    expect(result).toEqual({ id: "zone-1", risk: 0.5 });
  });

  it("throws an ApiError using the backend's error envelope on failure", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({
        status: 422,
        ok: false,
        body: {
          error: { code: "validation_error", message: "raw_text is required", details: { field: "raw_text" } },
        },
      })
    );

    await expect(apiRequest("/incidents/")).rejects.toMatchObject({
      status: 422,
      code: "validation_error",
      message: "raw_text is required",
      details: { field: "raw_text" },
    });
  });

  it("falls back to statusText and a generic code when there is no error envelope", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({ status: 500, ok: false, json: false })
    );

    try {
      await apiRequest("/incidents/");
      expect.unreachable("apiRequest should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiError = err as ApiError;
      expect(apiError.status).toBe(500);
      expect(apiError.code).toBe("unknown_error");
      expect(apiError.message).toBe("Error");
    }
  });

  it("logs the user out on a 401 response", async () => {
    useAuthStore.setState({ token: "stale-token", user: null, isAuthenticated: true });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({
        status: 401,
        ok: false,
        body: { error: { code: "unauthorized", message: "Invalid or expired token" } },
      })
    );

    await expect(apiRequest("/auth/me")).rejects.toBeInstanceOf(ApiError);

    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("does not log the user out on a non-401 error", async () => {
    useAuthStore.setState({ token: "still-valid", user: null, isAuthenticated: true });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFetchResponse({
        status: 500,
        ok: false,
        body: { error: { code: "internal_error", message: "boom" } },
      })
    );

    await expect(apiRequest("/incidents/")).rejects.toBeInstanceOf(ApiError);

    expect(useAuthStore.getState().token).toBe("still-valid");
  });
});
