import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { storeToken } from "../lib/api";
import { ProtectedImage } from "./ProtectedImage";

function renderImage(overlay?: unknown) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ProtectedImage
        endpoint="/api/v1/petri-images/petri-123/content"
        alt="Caja Petri protegida"
        caption="Caja Petri · petri.jpg"
        overlay={overlay}
      />
    </QueryClientProvider>,
  );
}

describe("ProtectedImage", () => {
  it("loads binary content with the bearer token and creates a local preview URL", async () => {
    storeToken("protected-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("image-bytes", {
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

  it("renders normalized detections and allows the user to hide them", async () => {
    storeToken("protected-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("image-bytes", {
          status: 200,
          headers: { "Content-Type": "image/jpeg" },
        }),
      ),
    );

    renderImage({
      kind: "petri",
      coordinate_space: "normalized",
      image_width: 800,
      image_height: 600,
      outline: { type: "ellipse", cx: 0.5, cy: 0.5, rx: 0.42, ry: 0.48 },
      regions: [
        {
          id: 1,
          role: "candidate_colony",
          bbox: { x: 0.2, y: 0.25, width: 0.15, height: 0.18 },
          polygon: [
            { x: 0.2, y: 0.25 },
            { x: 0.35, y: 0.25 },
            { x: 0.3, y: 0.43 },
          ],
        },
      ],
      branch_points: [{ x: 0.3, y: 0.31 }],
    });

    await screen.findByRole("img", { name: "Caja Petri protegida" });
    expect(screen.getByRole("img", { name: "Regiones detectadas por el motor" })).toBeInTheDocument();
    expect(screen.getByText(/2 elemento\(s\) visualizados/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ocultar detección" }));

    expect(screen.queryByRole("img", { name: "Regiones detectadas por el motor" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mostrar detección" })).toBeInTheDocument();
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
