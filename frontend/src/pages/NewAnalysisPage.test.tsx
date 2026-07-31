import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { NewAnalysisPage } from "./NewAnalysisPage";

const uploadResponse = {
  analysis_run_id: "run-123",
  prediction_id: "prediction-123",
  sample_id: "sample-123",
  petri_image_id: "petri-123",
  micro_image_id: "micro-123",
  predicted_label: "suspicious_growth",
  confidence_score: 0.65,
  class_probabilities: { suspicious_growth: 0.65 },
  requires_human_review: true,
  disclaimer: "Resultado preliminar",
  explanation: "Se observaron señales visuales.",
  feature_summary: {},
  quality_summary: {},
  decision_trace: [],
  warnings: [],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/analyses/new"]}>
        <Routes>
          <Route path="/analyses/new" element={<NewAnalysisPage />} />
          <Route path="/analyses/:analysisRunId/preliminary" element={<h1>Resultado recibido</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NewAnalysisPage", () => {
  it("submits both images and opens the preliminary result", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(uploadResponse), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPage();

    const petri = new File(["petri-image"], "petri.jpg", { type: "image/jpeg" });
    const micro = new File(["micro-image"], "micro.png", { type: "image/png" });
    await user.type(screen.getByLabelText(/Código de muestra/), "BB-TEST-01");
    await user.upload(screen.getByLabelText(/Imagen de caja Petri/), petri);
    await user.upload(screen.getByLabelText(/Imagen microscópica/), micro);
    await user.click(screen.getByRole("button", { name: "Ejecutar análisis preliminar" }));

    expect(await screen.findByRole("heading", { name: "Resultado recibido" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("sample_code")).toBe("BB-TEST-01");
    expect((init.body as FormData).get("petri_image")).toBe(petri);
    expect((init.body as FormData).get("micro_image")).toBe(micro);
  });

  it("shows a controlled error when the API rejects the upload", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: "invalid_image", message: "La imagen Petri no es válida" } }),
          { status: 400, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    const user = userEvent.setup();
    renderPage();

    await user.upload(
      screen.getByLabelText(/Imagen de caja Petri/),
      new File(["bad"], "petri.jpg", { type: "image/jpeg" }),
    );
    await user.upload(
      screen.getByLabelText(/Imagen microscópica/),
      new File(["micro"], "micro.jpg", { type: "image/jpeg" }),
    );
    await user.click(screen.getByRole("button", { name: "Ejecutar análisis preliminar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("La imagen Petri no es válida");
  });
});
