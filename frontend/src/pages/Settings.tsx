// Settings: roles (governance admin) and personal preferences.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, HeaderBand, ModuleError, Select, Skeleton, DataTable, useToast } from "../components/ui";
import { useSession } from "../components/Shell";
import { api, type Role } from "../lib/api";
import { label } from "../lib/format";

interface UserRow {
  email: string;
  role: Role;
  active: boolean;
  security_reviewer: boolean;
}

const ROLES: Role[] = ["app_owner", "reviewer", "governance_admin", "executive_viewer"];

export default function SettingsPage() {
  const { me } = useSession();
  const qc = useQueryClient();
  const toast = useToast();
  const admin = me?.role === "governance_admin";
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.get<UserRow[]>("/settings/users"), enabled: admin });
  const save = useMutation({
    mutationFn: (u: UserRow) => api.post(`/settings/users/${encodeURIComponent(u.email)}`, { role: u.role, active: u.active, security_reviewer: u.security_reviewer }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["users"] });
      toast({ kind: "success", message: "Role saved" });
    },
    onError: (e: Error) => toast({ kind: "error", message: e.message }),
  });
  return (
    <>
      <HeaderBand page="settings" title="Settings" summary="Roles come from the user directory, never from a request or a model." />
      <div className="flex flex-col gap-6">
        <Card title="Your account">
          <p className="t-body">{me ? `${me.email} · ${label(me.role)}` : "Not signed in"}</p>
          <p className="t-label mt-1 text-muted">Theme follows your choice in the top bar and is remembered for this account on this device.</p>
        </Card>
        <Card title="Roles">
          {!admin ? (
            <p className="t-body text-muted">Only a governance admin can manage roles.</p>
          ) : users.isLoading ? (
            <Skeleton className="h-64" />
          ) : users.error ? (
            <ModuleError error={users.error} onRetry={() => void users.refetch()} />
          ) : (
            <DataTable
              caption="Users and roles"
              columns={["User", "Role", "Security reviewer", "Active"]}
              rows={(users.data ?? []).map((u) => [
                u.email,
                <Select key="r" label={`Role for ${u.email}`} value={u.role} onChange={(v) => save.mutate({ ...u, role: v as Role })} options={ROLES.map((r) => ({ value: r, label: label(r) }))} />,
                <input key="s" type="checkbox" aria-label={`${u.email} is a security reviewer`} checked={u.security_reviewer} onChange={(e) => save.mutate({ ...u, security_reviewer: e.target.checked })} className="size-5" />,
                <input key="a" type="checkbox" aria-label={`${u.email} is active`} checked={u.active} onChange={(e) => save.mutate({ ...u, active: e.target.checked })} className="size-5" />,
              ])}
            />
          )}
        </Card>
      </div>
    </>
  );
}
