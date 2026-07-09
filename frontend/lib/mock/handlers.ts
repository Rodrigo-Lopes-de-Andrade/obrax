import Decimal from "decimal.js";
import { http, HttpResponse, delay } from "msw";

import type {
  DashboardSummary,
  Documento,
  DocumentoTipo,
  Obra,
  ObraStatus,
  OrcamentoStatus,
  Ticket,
  TicketMensagem,
  TicketStatus,
} from "@/lib/api/types";
import {
  clientes,
  currentUser,
  documentos,
  ensureSeed,
  membros,
  mensagens,
  nextId,
  obras,
  tickets,
  usuarios,
  type MockMembro,
} from "./db";
import {
  bulkCreate,
  createOrcamento,
  deleteItem,
  detailOf,
  duplicateItem,
  ensureOrcamentoSeed,
  importPlanilhaMock,
  insumos,
  MockError,
  orcamentos,
  reorder,
  setPrecificacao,
  softDeleteOrcamento,
  treeOf,
  updateItem,
  updateStatus,
} from "./orcamento-mock";

ensureSeed();
ensureOrcamentoSeed();

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

/** Converte um MockError (do orcamento-mock) numa resposta RFC 7807. `detail`
 * pode ser objeto (ex.: erros de importação linha-a-linha). */
function mockErrorResponse(e: unknown) {
  if (e instanceof MockError) {
    return HttpResponse.json(
      { type: "about:blank", title: "erro", status: e.status, detail: e.detail },
      { status: e.status },
    );
  }
  throw e;
}

/** Executa uma operação do mock e serializa o resultado (ou o erro). */
function runMock<T extends object>(fn: () => T, okStatus = 200) {
  try {
    return HttpResponse.json(fn() as Record<string, unknown>, { status: okStatus });
  } catch (e) {
    return mockErrorResponse(e);
  }
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

  // ── Sessão ──────────────────────────────────────────────────────────
  http.get("/api/v1/me", async () => {
    await delay(80);
    return HttpResponse.json(currentUser());
  }),

  // ── Dashboard (KPIs, B4.4) ──────────────────────────────────────────
  http.get("/api/v1/dashboard/summary", async () => {
    await delay(LATENCY);
    const ativas = obras.filter(
      (o) => o.status !== "concluida" && o.status !== "cancelada",
    );
    const valorTotal = ativas.reduce(
      (acc, o) => acc.plus(o.valor_contrato ?? 0),
      new Decimal(0),
    );
    const body: DashboardSummary = {
      obras_ativas: ativas.length,
      obras_valor_total: valorTotal.toFixed(2),
      tickets_abertos: tickets.filter((t) => t.status === "aberto").length,
      orcamentos_pendentes: 0,
    };
    return HttpResponse.json(body);
  }),

  // ── Tickets (chamados, B4.2–B4.5) ───────────────────────────────────
  http.get("/api/v1/tickets", async ({ request }) => {
    await delay(LATENCY);
    const url = new URL(request.url);
    const obraId = url.searchParams.get("obra_id");
    const status = url.searchParams.get("status") as TicketStatus | null;
    const search = url.searchParams.get("search")?.trim().toLowerCase() ?? "";
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");

    let rows = tickets;
    if (obraId) rows = rows.filter((t) => t.obra_id === obraId);
    if (status) rows = rows.filter((t) => t.status === status);
    if (search) {
      rows = rows.filter(
        (t) =>
          t.titulo.toLowerCase().includes(search) ||
          (t.descricao?.toLowerCase().includes(search) ?? false),
      );
    }
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.get("/api/v1/tickets/:id", async ({ params }) => {
    await delay(LATENCY);
    const t = tickets.find((x) => x.id === params.id);
    return t ? HttpResponse.json(t) : problem(404, "ticket não encontrado");
  }),

  http.post("/api/v1/obras/:obraId/tickets", async ({ params, request }) => {
    await delay(LATENCY);
    const obraId = params.obraId as string;
    if (!obras.some((o) => o.id === obraId)) return problem(422, "obra não encontrada");
    const body = (await request.json()) as { titulo?: string; descricao?: string | null };
    if (!body.titulo || !body.titulo.trim()) return problem(422, "título obrigatório");
    const t: Ticket = {
      id: nextId(),
      obra_id: obraId,
      titulo: body.titulo,
      descricao: body.descricao ?? null,
      status: "aberto",
      created_by: currentUser().id,
      created_at: new Date().toISOString(),
    };
    tickets.push(t);
    return HttpResponse.json(t, { status: 201 });
  }),

  http.patch("/api/v1/tickets/:id/status", async ({ params, request }) => {
    await delay(LATENCY);
    const t = tickets.find((x) => x.id === params.id);
    if (!t) return problem(404, "ticket não encontrado");
    const body = (await request.json()) as { status: TicketStatus };
    const valid: TicketStatus[] = ["aberto", "andamento", "resolvido", "fechado"];
    if (!valid.includes(body.status)) return problem(422, "status inválido");
    t.status = body.status;
    return HttpResponse.json(t);
  }),

  http.delete("/api/v1/tickets/:id", async ({ params }) => {
    await delay(LATENCY);
    const idx = tickets.findIndex((x) => x.id === params.id);
    if (idx === -1) return problem(404, "ticket não encontrado");
    tickets.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("/api/v1/tickets/:ticketId/mensagens", async ({ params, request }) => {
    await delay(LATENCY);
    const ticketId = params.ticketId as string;
    if (!tickets.some((t) => t.id === ticketId)) return problem(404, "ticket não encontrado");
    const url = new URL(request.url);
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");
    const rows = mensagens.filter((m) => m.ticket_id === ticketId);
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.post("/api/v1/tickets/:ticketId/mensagens", async ({ params, request }) => {
    await delay(LATENCY);
    const ticketId = params.ticketId as string;
    if (!tickets.some((t) => t.id === ticketId)) return problem(404, "ticket não encontrado");
    const body = (await request.json()) as {
      content?: string;
      attachment_paths?: string[];
    };
    if (!body.content || !body.content.trim()) return problem(422, "conteúdo obrigatório");
    const msg: TicketMensagem = {
      id: nextId(),
      ticket_id: ticketId,
      author_id: currentUser().id,
      content: body.content,
      attachment_paths: body.attachment_paths ?? [],
      created_at: new Date().toISOString(),
    };
    mensagens.push(msg);
    return HttpResponse.json(msg, { status: 201 });
  }),

  /* -------------------- Módulo 2 — Orçamentos (EAP) -------------------- */
  http.get("/api/v1/orcamentos", async ({ request }) => {
    await delay(LATENCY);
    const url = new URL(request.url);
    const obraId = url.searchParams.get("obra_id");
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "50");
    const rows = orcamentos.filter(
      (o) => !o.deleted && (!obraId || o.obra_id === obraId),
    );
    return HttpResponse.json(paginate(rows, cursor, limit));
  }),

  http.get("/api/v1/orcamentos/importar/modelo", async () => {
    await delay(150);
    return new HttpResponse(new Blob(["modelo-orcamento-mock"]), {
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": 'attachment; filename="modelo_orcamento.xlsx"',
      },
    });
  }),

  http.get("/api/v1/orcamentos/:id", async ({ params }) => {
    await delay(LATENCY);
    return runMock(() => detailOf(params.id as string));
  }),

  http.post("/api/v1/obras/:obraId/orcamentos", async ({ params, request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as { titulo?: string };
    if (!body.titulo || !body.titulo.trim()) return problem(422, "título obrigatório");
    if (!obras.some((o) => o.id === params.obraId)) return problem(422, "obra não encontrada");
    return runMock(() => createOrcamento(params.obraId as string, body.titulo!.trim()), 201);
  }),

  http.patch("/api/v1/orcamentos/:id/status", async ({ params, request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as { status?: OrcamentoStatus };
    if (!body.status) return problem(422, "status obrigatório");
    return runMock(() => updateStatus(params.id as string, body.status!));
  }),

  http.delete("/api/v1/orcamentos/:id", async ({ params }) => {
    await delay(LATENCY);
    try {
      softDeleteOrcamento(params.id as string);
      return new HttpResponse(null, { status: 204 });
    } catch (e) {
      return mockErrorResponse(e);
    }
  }),

  http.get("/api/v1/orcamentos/versoes/:vid/itens", async ({ params }) => {
    await delay(LATENCY);
    return runMock(() => treeOf(params.vid as string));
  }),

  http.post("/api/v1/orcamentos/versoes/:vid/itens/bulk", async ({ params, request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as { itens?: unknown[] };
    return runMock(() => bulkCreate(params.vid as string, (body.itens ?? []) as never), 201);
  }),

  http.patch("/api/v1/orcamentos/itens/:itemId", async ({ params, request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as Record<string, unknown>;
    return runMock(() => updateItem(params.itemId as string, body as never));
  }),

  http.delete("/api/v1/orcamentos/itens/:itemId", async ({ params }) => {
    await delay(LATENCY);
    return runMock(() => deleteItem(params.itemId as string));
  }),

  http.post("/api/v1/orcamentos/itens/:itemId/duplicar", async ({ params }) => {
    await delay(LATENCY);
    return runMock(() => duplicateItem(params.itemId as string), 201);
  }),

  http.put("/api/v1/orcamentos/versoes/:vid/itens/ordem", async ({ params, request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as { itens?: unknown[] };
    return runMock(() => reorder(params.vid as string, (body.itens ?? []) as never));
  }),

  http.put("/api/v1/orcamentos/versoes/:vid/precificacao", async ({ params, request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as { markup_global?: string; taxa_adm?: string };
    return runMock(() =>
      setPrecificacao(params.vid as string, body.markup_global ?? "0", body.taxa_adm ?? "0"),
    );
  }),

  http.post("/api/v1/orcamentos/versoes/:vid/importar-planilha", async ({ params, request }) => {
    await delay(700);
    const form = await request.formData();
    const file = form.get("arquivo");
    const name = file instanceof File ? file.name : "planilha.xlsx";
    return runMock(() => importPlanilhaMock(params.vid as string, name), 201);
  }),

  /* ---------------------- Catálogo de insumos ------------------------- */
  http.get("/api/v1/insumos/categorias", async () => {
    await delay(LATENCY);
    const cats = Array.from(
      new Set(insumos.map((i) => i.categoria).filter((c): c is string => !!c)),
    ).sort();
    return HttpResponse.json({ categorias: cats });
  }),

  http.get("/api/v1/insumos", async ({ request }) => {
    await delay(LATENCY);
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.trim().toLowerCase();
    const categoria = url.searchParams.get("categoria");
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") ?? "20");
    let rows = insumos.filter((i) => {
      if (categoria && i.categoria !== categoria) return false;
      if (search) {
        return (
          i.descricao.toLowerCase().includes(search) ||
          i.codigo.toLowerCase().includes(search)
        );
      }
      return true;
    });
    rows = rows.sort((a, b) =>
      a.descricao < b.descricao
        ? -1
        : a.descricao > b.descricao
          ? 1
          : a.id < b.id
            ? -1
            : 1,
    );
    const start = cursor ? rows.findIndex((r) => r.id === cursor) + 1 : 0;
    const page = rows.slice(start, start + limit);
    const hasMore = start + limit < rows.length;
    return HttpResponse.json({
      items: page,
      next_cursor: hasMore && page.length ? page[page.length - 1].id : null,
    });
  }),
];
