import { http, HttpResponse, delay } from "msw";

import type { Obra, ObraStatus } from "@/lib/api/types";
import { clientes, ensureSeed, nextId, obras } from "./db";

ensureSeed();

/** Latência artificial para os skeletons/estados de loading aparecerem. */
const LATENCY = 350;

function problem(status: number, title: string, detail?: string) {
  return HttpResponse.json(
    { type: "about:blank", title, status, detail },
    { status },
  );
}

function paginate<T extends { id: string }>(
  rows: T[],
  cursor: string | null,
  limit: number,
) {
  const desc = [...rows].sort((a, b) =>
    a.id < b.id ? 1 : a.id > b.id ? -1 : 0,
  );
  const after = cursor ? desc.filter((r) => r.id < cursor) : desc;
  const items = after.slice(0, limit);
  const hasMore = after.length > limit;
  return { items, next_cursor: hasMore ? items[items.length - 1].id : null };
}

export const handlers = [
  http.get("/api/v1/clientes", async ({ request }) => {
    await delay(LATENCY);
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";
    const tipo = url.searchParams.get("type");
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");

    let rows = clientes;
    if (tipo) rows = rows.filter((c) => c.tipo_pessoa === tipo);
    if (search) {
      rows = rows.filter(
        (c) =>
          c.nome.toLowerCase().includes(search) || c.documento.includes(search),
      );
    }
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.get("/api/v1/obras", async ({ request }) => {
    await delay(LATENCY);
    const url = new URL(request.url);
    const status = url.searchParams.get("status") as ObraStatus | null;
    const clienteId = url.searchParams.get("cliente_id");
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");

    let rows = obras;
    if (status) rows = rows.filter((o) => o.status === status);
    if (clienteId) rows = rows.filter((o) => o.cliente_id === clienteId);
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.get("/api/v1/obras/:id", async ({ params }) => {
    await delay(LATENCY);
    const obra = obras.find((o) => o.id === params.id);
    return obra ? HttpResponse.json(obra) : problem(404, "obra não encontrada");
  }),

  http.post("/api/v1/obras", async ({ request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as Partial<Obra>;
    if (!body.cliente_id || !clientes.some((c) => c.id === body.cliente_id)) {
      return problem(422, "cliente não encontrado", "cliente_id inválido para o tenant");
    }
    const obra: Obra = {
      id: nextId(),
      cliente_id: body.cliente_id,
      status: body.status ?? "planejamento",
      codigo: body.codigo ?? "",
      nome: body.nome ?? "",
      data_inicio: body.data_inicio ?? null,
      data_prevista_fim: body.data_prevista_fim ?? null,
      data_real_fim: body.data_real_fim ?? null,
      valor_contrato: body.valor_contrato ?? null,
      created_at: new Date().toISOString(),
    };
    obras.push(obra);
    return HttpResponse.json(obra, { status: 201 });
  }),

  http.patch("/api/v1/obras/:id", async ({ params, request }) => {
    await delay(LATENCY);
    const obra = obras.find((o) => o.id === params.id);
    if (!obra) return problem(404, "obra não encontrada");
    const p = (await request.json()) as Partial<Obra>;
    Object.assign(obra, {
      codigo: p.codigo ?? obra.codigo,
      nome: p.nome ?? obra.nome,
      status: p.status ?? obra.status,
      data_inicio: p.data_inicio !== undefined ? p.data_inicio : obra.data_inicio,
      data_prevista_fim:
        p.data_prevista_fim !== undefined ? p.data_prevista_fim : obra.data_prevista_fim,
      data_real_fim: p.data_real_fim !== undefined ? p.data_real_fim : obra.data_real_fim,
      valor_contrato:
        p.valor_contrato !== undefined ? p.valor_contrato : obra.valor_contrato,
    });
    return HttpResponse.json(obra);
  }),

  http.delete("/api/v1/obras/:id", async ({ params }) => {
    await delay(LATENCY);
    const idx = obras.findIndex((o) => o.id === params.id);
    if (idx === -1) return problem(404, "obra não encontrada");
    obras.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];
