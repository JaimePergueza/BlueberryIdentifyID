import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { AuthProvider } from "../lib/auth";
import { storeToken } from "../lib/api";
import type { User } from "../types/api";
import { AppShell } from "./AppShell";

function renderShell(user: User) {
  storeToken("test-token");
  sessionStorage.setItem("blueberry-microid.user", JSON.stringify(user));
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <AuthProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<h1>Contenido</h1>} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

const baseUser: User = {
  id: "123e4567-e89b-12d3-a456-426614174000",
  username: "usuario-demo",
  role: "specialist",
  is_active: true,
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T00:00:00Z",
};

describe("AppShell role navigation", () => {
  beforeEach(() => sessionStorage.clear());

  it("does not expose user administration to a specialist", () => {
    renderShell(baseUser);
    expect(screen.queryByRole("link", { name: /Usuarios/i })).not.toBeInTheDocument();
    expect(screen.getByText("Especialista")).toBeInTheDocument();
  });

  it("shows user administration to an administrator", () => {
    renderShell({ ...baseUser, role: "admin", username: "admin-demo" });
    expect(screen.getByRole("link", { name: /Usuarios/i })).toHaveAttribute("href", "/admin/users");
    expect(screen.getByText("Administrador")).toBeInTheDocument();
  });
});
