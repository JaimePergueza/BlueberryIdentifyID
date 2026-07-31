import { describe, expect, it, vi } from "vitest";
import { apiRequest, clearStoredToken, getStoredToken, storeToken } from "./api";

describe("apiRequest", () => {
  it("adds the stored bearer token to authenticated requests", async () => {
    storeToken("test-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest<{ ok: boolean }>("/api/v1/analysis-runs");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer test-token");
  });

  it("clears the session and broadcasts expiration after an authenticated 401", async () => {
    storeToken("expired-token");
    const listener = vi.fn();
    window.addEventListener("blueberry-auth-expired", listener);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "authentication_required", message: "Sesión expirada" },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(apiRequest("/api/v1/analysis-runs")).rejects.toMatchObject({
      status: 401,
      code: "authentication_required",
    });
    expect(getStoredToken()).toBeNull();
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener("blueberry-auth-expired", listener);
  });

  it("does not attach a token to public requests", async () => {
    storeToken("test-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/health", {}, { authenticated: false });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).has("Authorization")).toBe(false);
    clearStoredToken();
  });
});
