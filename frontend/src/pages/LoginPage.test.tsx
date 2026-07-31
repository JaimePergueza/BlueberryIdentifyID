import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../lib/auth";
import { getStoredToken } from "../lib/api";
import { LoginPage } from "./LoginPage";

const loginResponse = {
  access_token: "opaque-session-token",
  token_type: "bearer",
  expires_at: "2026-07-31T12:00:00Z",
  user: {
    id: "123e4567-e89b-12d3-a456-426614174000",
    username: "especialista",
    role: "specialist",
    is_active: true,
    created_at: "2026-07-31T00:00:00Z",
    updated_at: "2026-07-31T00:00:00Z",
  },
};

describe("LoginPage", () => {
  it("authenticates and returns to the protected destination", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(loginResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={[{ pathname: "/login", state: { from: "/analyses" } }]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/analyses" element={<h1>Historial autenticado</h1>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("Usuario"), "especialista");
    await user.type(screen.getByLabelText("Contraseña"), "Secret-Password-42");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("heading", { name: "Historial autenticado" })).toBeInTheDocument();
    expect(getStoredToken()).toBe("opaque-session-token");
  });

  it("shows the controlled API error without losing the form", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "invalid_credentials", message: "Usuario o contraseña inválidos" },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("Usuario"), "usuario");
    await user.type(screen.getByLabelText("Contraseña"), "Incorrect-Password-42");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Usuario o contraseña inválidos");
    expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
  });
});
