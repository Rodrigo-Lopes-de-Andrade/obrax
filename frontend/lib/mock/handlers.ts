import { http, HttpResponse, delay } from "msw";

import type { Documento, DocumentoTipo, Obra, ObraStatus } from "@/lib/api/types";
import {
  clientes,
  documentos,
  ensureSeed,
  membros,
  nextId,
  obras,
  usuarios,
  type MockMembro,
} from "./db";

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

  // ── Documentos (GED, B3.1–B3.4) ─────────────────────────────────────
  http.get("/api/v1/obras/:obraId/documentos", async ({ params, request }) => {
    await delay(LATENCY);
    const obraId = params.obraId as string;
    if (!obras.some((o) => o.id === obraId)) return problem(404, "obra não encontrada");
    const url = new URL(request.url);
    const categoria = url.searchParams.get("categoria");
    const search = url.searchParams.get("search")?.trim().toLowerCase() ?? "";
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");

    let rows = documentos.filter((d) => d.obra_id === obraId);
    if (categoria) rows = rows.filter((d) => d.categoria === categoria);
    if (search) rows = rows.filter((d) => d.nome.toLowerCase().includes(search));
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.post("/api/v1/obras/:obraId/documentos", async ({ params, request }) => {
    await delay(LATENCY);
    const obraId = params.obraId as string;
    if (!obras.some((o) => o.id === obraId)) return problem(422, "obra não encontrada");
    const body = (await request.json()) as {
      nome: string;
      tipo: DocumentoTipo;
      sha256: string;
      size_bytes: number;
      categoria?: string | null;
    };
    if (documentos.some((d) => d.obra_id === obraId && d.sha256 === body.sha256)) {
      return problem(409, "documento duplicado", "mesmo conteúdo já enviado nesta obra");
    }
    const doc: Documento = {
      id: nextId(),
      obra_id: obraId,
      nome: body.nome,
      tipo: body.tipo,
      categoria: body.categoria ?? null,
      visivel_cliente: false,
      size_bytes: body.size_bytes,
      sha256: body.sha256,
      confirmed: false,
      created_at: new Date().toISOString(),
    };
    documentos.push(doc);
    return HttpResponse.json(
      {
        documento_id: doc.id,
        upload_url: `/_mock/storage/${doc.id}`,
        method: "PUT",
        expires_in: 900,
      },
      { status: 201 },
    );
  }),

  // Mock do PUT direto no storage (URL assinada) — só confirma o recebimento.
  http.put("/_mock/storage/:id", async () => {
    await delay(150);
    return new HttpResponse(null, { status: 200 });
  }),

  http.post("/api/v1/documentos/:id/confirm", async ({ params }) => {
    await delay(LATENCY);
    const doc = documentos.find((d) => d.id === params.id);
    if (!doc) return problem(404, "documento não encontrado");
    doc.confirmed = true;
    return HttpResponse.json(doc);
  }),

  http.patch("/api/v1/documentos/:id", async ({ params, request }) => {
    await delay(LATENCY);
    const doc = documentos.find((d) => d.id === params.id);
    if (!doc) return problem(404, "documento não encontrado");
    const p = (await request.json()) as {
      categoria?: string | null;
      visivel_cliente?: boolean;
    };
    if (p.categoria !== undefined) doc.categoria = p.categoria;
    if (p.visivel_cliente !== undefined) doc.visivel_cliente = p.visivel_cliente;
    return HttpResponse.json(doc);
  }),

  http.delete("/api/v1/documentos/:id", async ({ params }) => {
    await delay(LATENCY);
    const idx = documentos.findIndex((d) => d.id === params.id);
    if (idx === -1) return problem(404, "documento não encontrado");
    documentos.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  // ── Equipes (B3.5–B3.6) ─────────────────────────────────────────────
  http.get("/api/v1/usuarios", async ({ request }) => {
    await delay(LATENCY);
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.trim().toLowerCase() ?? "";
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");
    let rows = usuarios;
    if (search) {
      rows = rows.filter(
        (u) =>
          u.nome.toLowerCase().includes(search) ||
          u.email.toLowerCase().includes(search),
      );
    }
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.get("/api/v1/obras/:obraId/membros", async ({ params, request }) => {
    await delay(LATENCY);
    const obraId = params.obraId as string;
    if (!obras.some((o) => o.id === obraId)) return problem(404, "obra não encontrada");
    const url = new URL(request.url);
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");
    const rows = membros.filter((m) => m.obra_id === obraId);
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.post("/api/v1/obras/:obraId/membros", async ({ params, request }) => {
    await delay(LATENCY);
    const obraId = params.obraId as string;
    if (!obras.some((o) => o.id === obraId)) return problem(404, "obra não encontrada");
    const body = (await request.json()) as { user_id: string; papel: string };
    const u = usuarios.find((x) => x.id === body.user_id);
    if (!u) return problem(422, "usuário não encontrado");
    if (membros.some((m) => m.obra_id === obraId && m.user_id === body.user_id)) {
      return problem(409, "usuário já é membro ativo desta obra");
    }
    const membro: MockMembro = {
      id: nextId(),
      obra_id: obraId,
      user_id: u.id,
      nome: u.nome,
      email: u.email,
      papel: body.papel,
      created_at: new Date().toISOString(),
    };
    membros.push(membro);
    return HttpResponse.json(membro, { status: 201 });
  }),

  http.delete("/api/v1/obras/:obraId/membros/:userId", async ({ params }) => {
    await delay(LATENCY);
    const idx = membros.findIndex(
      (m) => m.obra_id === params.obraId && m.user_id === params.userId,
    );
    if (idx === -1) return problem(404, "membro não encontrado");
    membros.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];
