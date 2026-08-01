import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TaxonomicDifferential } from "./TaxonomicDifferential";

const availableDifferential = {
  engine: { name: "MorphologicalDifferentialEngine", version: "0.1.0" },
  status: "available",
  scope: "diferencial morfológico visual no diagnóstico",
  score_semantics: "Los índices expresan compatibilidad heurística, no probabilidades.",
  summary: "Compatible con hongo filamentoso; Penicillium es una hipótesis posible, no confirmada.",
  broad_interpretation: {
    label: "Compatible con hongo filamentoso",
    compatibility_index: 0.61,
  },
  morphological_description: {
    macroscopy: ["Cuatro regiones coloniales candidatas."],
    microscopy: ["Cobertura filamentosa detectable."],
  },
  candidates: [
    {
      id: "penicillium_like",
      display_name: "Morfología tipo Penicillium",
      compatibility_index: 0.38,
      compatibility_label: "posible, no confirmada",
      supporting_evidence: ["Tonalidad colonial gris-verdosa."],
      missing_or_contradictory_evidence: ["No se han demostrado fiálides."],
      required_confirmation: ["Secuenciación ITS y BenA."],
    },
    {
      id: "aspergillus_like",
      display_name: "Morfología tipo Aspergillus",
      compatibility_index: 0.24,
      compatibility_label: "soporte bajo",
      supporting_evidence: ["Crecimiento filamentoso visible."],
      missing_or_contradictory_evidence: ["No se ha reconocido vesícula terminal."],
      required_confirmation: ["Revisión microscópica dirigida."],
    },
  ],
  confirmation_required: ["Revisión de varios campos microscópicos."],
  limitations: ["No identifica género ni especie."],
};

describe("TaxonomicDifferential", () => {
  it("shows a non-diagnostic Penicillium-like differential with supporting and missing evidence", () => {
    render(<TaxonomicDifferential differential={availableDifferential} />);

    expect(screen.getByRole("heading", { name: "Hipótesis taxonómica explicable" })).toBeInTheDocument();
    expect(screen.getByText("Morfología tipo Penicillium")).toBeInTheDocument();
    expect(screen.getByText("38%")).toBeInTheDocument();
    expect(screen.getByText("Tonalidad colonial gris-verdosa.")).toBeInTheDocument();
    expect(screen.getByText("No se han demostrado fiálides.")).toBeInTheDocument();
    expect(screen.getAllByText(/no es una probabilidad/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/MorphologicalDifferentialEngine 0.1.0/)).toBeInTheDocument();
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
