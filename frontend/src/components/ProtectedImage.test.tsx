import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { storeToken } from "../lib/api";
import { ProtectedImage } from "./ProtectedImage";

function renderImage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ProtectedImage
        endpoint="/api/v1/petri-images/petri-123/content"
        alt="Caja Petri protegida"
        caption="Caja Petri · petri.jpg"
      />
    </QueryClientProvider>,
  );
}

describe("ProtectedImage", () => {
  it("loads binary content with the bearer token and creates a local preview URL", async () => {
    storeToken("protected-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(new Blob(["image-bytes"], { type: "image/jpeg" }), {
        status: 200,
        headers: { "Content-Type": "image/jpeg" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderImage();

    const image = await screen.findByRole("img", { name: "Caja Petri protegida" });
    expect(image).toHaveAttribute("src", "blob:test-preview");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer protected-token");
  });

  it("shows a safe unavailable state instead of a broken image", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "stored_image_unavailable",
              message: "Stored image content is unavailable",
            },
          }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderImage();

    expect(await screen.findByText("Imagen no disponible")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
