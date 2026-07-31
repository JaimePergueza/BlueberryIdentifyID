import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";
import { ErrorState, LoadingState } from "../components/Feedback";
import { apiRequest } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import type {
  CreateUserPayload,
  UpdateUserPayload,
  User,
  UserListResponse,
  UserRole,
} from "../types/api";

const initialCreateForm: CreateUserPayload = {
  username: "",
  password: "",
  role: "specialist",
};

function roleName(role: UserRole): string {
  return role === "admin" ? "Administrador" : "Especialista";
}

export function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const [createForm, setCreateForm] = useState<CreateUserPayload>(initialCreateForm);
  const [passwords, setPasswords] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => apiRequest<UserListResponse>("/api/v1/admin/users"),
  });

  const refreshUsers = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
  };

  const createMutation = useMutation({
    mutationFn: (payload: CreateUserPayload) =>
      apiRequest<User>("/api/v1/admin/users", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: async (created) => {
      setCreateForm(initialCreateForm);
      setMessage(`Usuario ${created.username} creado correctamente.`);
      await refreshUsers();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateUserPayload }) =>
      apiRequest<User>(`/api/v1/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async (updated) => {
      setMessage(`Usuario ${updated.username} actualizado correctamente.`);
      setPasswords((current) => ({ ...current, [updated.id]: "" }));
      await refreshUsers();
    },
  });

  const users = usersQuery.data?.users ?? [];
  const metrics = useMemo(() => ({
    total: users.length,
    active: users.filter((item) => item.is_active).length,
    specialists: users.filter((item) => item.role === "specialist").length,
    admins: users.filter((item) => item.role === "admin").length,
  }), [users]);

  const submitCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(null);
    createMutation.mutate({
      username: createForm.username.trim().toLowerCase(),
      password: createForm.password,
      role: createForm.role,
    });
  };

  const updateUser = (id: string, payload: UpdateUserPayload) => {
    setMessage(null);
    updateMutation.mutate({ id, payload });
  };

  if (usersQuery.isLoading) return <LoadingState message="Cargando cuentas del sistema…" />;
  if (usersQuery.isError) return <ErrorState error={usersQuery.error} title="No fue posible cargar los usuarios" />;

  const mutationError = createMutation.error ?? updateMutation.error;

  return (
    <div className="page admin-users-page">
      <div className="page-header dashboard-header">
        <div>
          <span className="eyebrow">Administración</span>
          <h1>Usuarios y permisos</h1>
          <p>
            Gestiona cuentas operativas sin exponer contraseñas, hashes ni sesiones. El administrador
            conserva también todas las funciones del especialista.
          </p>
        </div>
        <span className="badge badge-label">Acceso exclusivo de administrador</span>
      </div>

      <section className="metric-grid" aria-label="Indicadores de usuarios">
        <article className="metric-card"><span>Total</span><strong>{metrics.total}</strong><small>cuentas registradas</small></article>
        <article className="metric-card metric-success"><span>Activos</span><strong>{metrics.active}</strong><small>pueden iniciar sesión</small></article>
        <article className="metric-card"><span>Especialistas</span><strong>{metrics.specialists}</strong><small>operación del laboratorio</small></article>
        <article className="metric-card"><span>Administradores</span><strong>{metrics.admins}</strong><small>gobierno del sistema</small></article>
      </section>

      {message && <div className="alert alert-info" role="status"><strong>Operación completada</strong><p>{message}</p></div>}
      {mutationError && <ErrorState error={mutationError} title="No fue posible actualizar la cuenta" />}

      <div className="admin-users-layout">
        <section className="card admin-create-card">
          <div className="section-heading">
            <div><span className="eyebrow">Nueva cuenta</span><h2>Crear usuario</h2></div>
          </div>
          <form className="admin-user-form" onSubmit={submitCreate}>
            <label className="field">
              <span>Nombre de usuario</span>
              <input
                autoComplete="off"
                minLength={3}
                maxLength={100}
                required
                value={createForm.username}
                onChange={(event) => setCreateForm((current) => ({ ...current, username: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>Contraseña temporal <small>(mínimo 12 caracteres)</small></span>
              <input
                autoComplete="new-password"
                minLength={12}
                maxLength={256}
                required
                type="password"
                value={createForm.password}
                onChange={(event) => setCreateForm((current) => ({ ...current, password: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>Rol</span>
              <select
                value={createForm.role}
                onChange={(event) => setCreateForm((current) => ({ ...current, role: event.target.value as UserRole }))}
              >
                <option value="specialist">Especialista</option>
                <option value="admin">Administrador</option>
              </select>
            </label>
            <button className="button button-primary button-full" disabled={createMutation.isPending} type="submit">
              {createMutation.isPending ? "Creando…" : "Crear usuario"}
            </button>
          </form>
        </section>

        <section className="card admin-users-table-card">
          <div className="section-heading">
            <div><span className="eyebrow">Control de acceso</span><h2>Cuentas registradas</h2></div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th>Registro</th>
                  <th>Restablecer contraseña</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {users.map((item) => {
                  const isCurrentUser = item.id === currentUser?.id;
                  const newPassword = passwords[item.id] ?? "";
                  return (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.username}</strong>
                        {isCurrentUser && <small className="table-subtext">Sesión actual</small>}
                      </td>
                      <td>
                        <select
                          aria-label={`Rol de ${item.username}`}
                          disabled={updateMutation.isPending || isCurrentUser}
                          value={item.role}
                          onChange={(event) => updateUser(item.id, { role: event.target.value as UserRole })}
                        >
                          <option value="specialist">Especialista</option>
                          <option value="admin">Administrador</option>
                        </select>
                        <small className="table-subtext">{roleName(item.role)}</small>
                      </td>
                      <td><span className={`badge ${item.is_active ? "badge-reviewed" : "badge-failed"}`}>{item.is_active ? "Activo" : "Inactivo"}</span></td>
                      <td>{formatDate(item.created_at)}</td>
                      <td>
                        <div className="inline-password-reset">
                          <input
                            aria-label={`Nueva contraseña para ${item.username}`}
                            autoComplete="new-password"
                            minLength={12}
                            placeholder="Mínimo 12 caracteres"
                            type="password"
                            value={newPassword}
                            onChange={(event) => setPasswords((current) => ({ ...current, [item.id]: event.target.value }))}
                          />
                          <button
                            className="button button-secondary"
                            disabled={updateMutation.isPending || newPassword.length < 12}
                            onClick={() => updateUser(item.id, { password: newPassword })}
                            type="button"
                          >
                            Cambiar
                          </button>
                        </div>
                      </td>
                      <td>
                        <button
                          className="button button-ghost"
                          disabled={updateMutation.isPending || isCurrentUser}
                          onClick={() => updateUser(item.id, { is_active: !item.is_active })}
                          type="button"
                        >
                          {item.is_active ? "Desactivar" : "Activar"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
