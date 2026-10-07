import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ColonyCount } from "./ColonyCount";

describe("ColonyCount", () => {
  it("preserves zero as a preliminary count", () => {
    render(<ColonyCount assessment={{ status: "preliminary", estimated_count: 0 }} />);
    expect(screen.getByRole("heading", { name: "Conteo visual preliminar" })).toBeInTheDocument();
    expect(screen.getByText("regiones candidatas").parentElement).toHaveTextContent("0 regiones candidatas");
  });

  it("shows abstention instead of a count for confluent growth", () => {
    render(<ColonyCount assessment={{ status: "not_countable", estimated_count: null,
      reason_codes: ["connected_growth"] }} />);
    expect(screen.getByRole("heading", { name: "Conteo automático no disponible" })).toBeInTheDocument();
    expect(screen.getByText("Hay crecimiento conectado o confluente.")).toBeInTheDocument();
  });

  it("does not invent a count for historical analyses", () => {
    const { container } = render(<ColonyCount assessment={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
