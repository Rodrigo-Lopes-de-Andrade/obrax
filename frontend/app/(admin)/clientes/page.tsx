"use client";

import * as React from "react";
import { Plus, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClienteFormDrawer } from "@/components/modules/cliente/ClienteFormDrawer";
import { useClientes } from "@/lib/hooks/use-clientes";

export default function ClientesPage() {
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const { data, isLoading } = useClientes();
  const clientes = data?.items ?? [];

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Clientes</h1>
        <Button onClick={() => setDrawerOpen(true)}>
          <Plus className="size-4" />
          Novo cliente
        </Button>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : clientes.length === 0 ? (
        <div className="rounded-xl border border-border bg-card px-6 py-16 text-center">
          <span className="mx-auto grid size-11 place-items-center rounded-lg bg-muted text-muted-foreground">
            <Users className="size-5" />
          </span>
          <h2 className="mt-4 font-semibold">Nenhum cliente ainda</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
            Cadastre seu primeiro cliente para poder vinculá-lo a uma obra.
          </p>
          <Button className="mt-5" onClick={() => setDrawerOpen(true)}>
            <Plus className="size-4" />
            Novo cliente
          </Button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Documento</TableHead>
                <TableHead>Contato</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {clientes.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">{c.nome}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{c.tipo_pessoa}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{c.documento}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {c.email ?? c.telefone ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ClienteFormDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
    </div>
  );
}
