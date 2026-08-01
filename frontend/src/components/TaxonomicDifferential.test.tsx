import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TaxonomicDifferential } from "./TaxonomicDifferential";

const availableDifferential = {
  engine: { name: "MorphologicalDifferentialEngine", version: "0.2.0" },
  status: "available",
  scope: "diferencial morfológico visual orientado a microorganismos asociados con arándanos",
  score_semantics: "Los índices expresan compatibilidad heurística, no probabilidades.",
  summary: "Compatible con hongo filamentoso; varios perfiles se superponen.",
  broad_interpretation: {
    label: "Compatible con hongo filamentoso",
    compatibility_index: 0.61,
  },
  morphological_description: {
    macroscopy: ["Cuatro regiones coloniales candidatas."],
    microscopy: ["Cobertura filamentosa moderada."],
  },
  candidates: [
    {
      id: "penicillium_like",
      display_name: "Morfología tipo Penicillium",
      reported_blueberry_examples: ["Penicillium expansum", "Penicillium crustosum"],
      compatibility_index: 0.38,
      compatibility_label: "posible, no confirmada",
      supporting_evidence: ["Tonalidad colonial gris-verdosa."],
      missing_or_contradictory_evidence: ["No se han demostrado fiálides."],
      required_confirmation: ["Secuenciación ITS y BenA."],
    },
    {
      id: "botrytis_like",
      display_name: "Morfología tipo Botrytis",
      reported_blueberry_examples: ["Botrytis cinerea"],
      compatibility_index: 0.31,
      compatibility_label: "evidencia limitada",
      supporting_evidence: ["Coloración grisácea."],
      missing_or_contradictory_evidence: ["No se reconocieron conidióforos botrioides."],
      required_confirmation: ["Revisión microscópica dirigida."],
    },
  ],
  confirmation_required: ["Revisión de varios campos microscópicos."],
  limitations: ["No identifica género ni especie."],
};

describe("TaxonomicDifferential", () => {
  it("shows several blueberry-associated morphology profiles and their limitations", () => {
    render(<TaxonomicDifferential differential={availableDifferential} />);

    expect(screen.getByRole("heading", { name: "Diferencial morfológico para arándanos" })).toBeInTheDocument();
    expect(screen.getByText("Morfología tipo Penicillium")).toBeInTheDocument();
    expect(screen.getByText("Morfología tipo Botrytis")).toBeInTheDocument();
    expect(screen.getByText(/Penicillium expansum/)).toBeInTheDocument();
    expect(screen.getByText("Botrytis cinerea")).toBeInTheDocument();
    expect(screen.getByText("38%")).toBeInTheDocument();
    expect(screen.getByText("Tonalidad colonial gris-verdosa.")).toBeInTheDocument();
    expect(screen.getByText("No se han demostrado fiálides.")).toBeInTheDocument();
    expect(screen.getAllByText(/no es una probabilidad/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/MorphologicalDifferentialEngine 0.2.0/)).toBeInTheDocument();
  });

  it("does not fabricate candidates when the differential is unavailable", () => {
    render(
      <TaxonomicDifferential
        differential={{
          ...availableDifferential,
          status: "unavailable",
          summary: "No se genera una hipótesis taxonómica porque la captura fue rechazada.",
          candidates: [],
          broad_interpretation: {},
        }}
      />,
    );

    expect(screen.getByText("Diferencial no disponible")).toBeInTheDocument();
    expect(screen.getByText(/captura fue rechazada/)).toBeInTheDocument();
    expect(screen.queryByText("Morfología tipo Penicillium")).not.toBeInTheDocument();
  });
});
