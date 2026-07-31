import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "../lib/auth";
import { storeToken } from "../lib/api";
import { ProtectedRoute } from "./ProtectedRoute";

const storedUser = {
  id: "123e4567-e89b-12d3-a456-426614174000",
  username: "especialista",
  role: "specialist",
  is_active: true,
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T00:00:00Z",
};

describe("ProtectedRoute", () => {
  it("redirects an anonymous visitor to login", async () => {
    render(
      <MemoryRouter initialEntries={["/analyses"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<h1>Acceso requerido</h1>} />
            <Route
              path="/analyses"
              element={
                <ProtectedRoute>
                  <h1>Historial privado</h1>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Acceso requerido" })).toBeInTheDocument();
    expect(screen.queryByText("Historial privado")).not.toBeInTheDocument();
  });

  it("blocks a specialist from an administrator-only route", async () => {
    storeToken("valid-token");
    sessionStorage.setItem("blueberry-microid.user", JSON.stringify(storedUser));

    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<h1>Resumen operativo</h1>} />
            <Route
              path="/admin"
              element={
                <ProtectedRoute roles={["admin"]}>
                  <h1>Administración</h1>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Resumen operativo" })).toBeInTheDocument();
    expect(screen.queryByText("Administración")).not.toBeInTheDocument();
  });
});
