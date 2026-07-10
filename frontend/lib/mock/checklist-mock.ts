/**
 * Mock do checklist de campo (B7.2, US-16). Espelha gestao/checklist: itens por
 * obra com sort_order incremental, toggle carimbando completed_at no servidor e
 * soft delete. Semeia alguns itens nas obras para o app de campo já ter conteúdo.
 */
import type { ChecklistItem } from "@/lib/api/types";
import { nextId, obras } from "./db";

interface MockChecklistItem extends ChecklistItem {
  deleted: boolean;
}

export const checklistItems: MockChecklistItem[] = [];

export class ChecklistMockError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
  }
}

function nowIso(): string {
  return new Date().toISOString();
}

function assertObra(obraId: string): void {
  if (!obras.some((o) => o.id === obraId)) {
    throw new ChecklistMockError(404, "obra não encontrada");
  }
}

function itemsDaObra(obraId: string): MockChecklistItem[] {
  return checklistItems
    .filter((i) => i.obra_id === obraId && !i.deleted)
    .sort((a, b) => a.sort_order - b.sort_order || (a.id < b.id ? -1 : 1));
}

export function listChecklist(obraId: string): { items: ChecklistItem[]; next_cursor: null } {
  assertObra(obraId);
  return { items: itemsDaObra(obraId).map(strip), next_cursor: null };
}

export function createChecklistItem(obraId: string, titulo: string): ChecklistItem {
  assertObra(obraId);
  if (!titulo.trim()) throw new ChecklistMockError(422, "título obrigatório");
  const maxOrder = itemsDaObra(obraId).reduce((m, i) => Math.max(m, i.sort_order), -1);
  const item: MockChecklistItem = {
    id: nextId(),
    obra_id: obraId,
    titulo: titulo.trim(),
    completed: false,
    completed_at: null,
    sort_order: maxOrder + 1,
    created_at: nowIso(),
    deleted: false,
  };
  checklistItems.push(item);
  return strip(item);
}

export function updateChecklistItem(
  itemId: string,
  patch: { titulo?: string; completed?: boolean; sort_order?: number },
): ChecklistItem {
  const item = checklistItems.find((i) => i.id === itemId && !i.deleted);
  if (!item) throw new ChecklistMockError(404, "item de checklist não encontrado");
  if (Object.keys(patch).length === 0) throw new ChecklistMockError(422, "nada para atualizar");
  if (patch.titulo !== undefined) item.titulo = patch.titulo;
  if (patch.sort_order !== undefined) item.sort_order = patch.sort_order;
  if (patch.completed !== undefined) {
    item.completed = patch.completed;
    // Servidor carimba completed_at no toggle (relógio do cliente não conta).
    item.completed_at = patch.completed ? nowIso() : null;
  }
  return strip(item);
}

export function deleteChecklistItem(itemId: string): void {
  const item = checklistItems.find((i) => i.id === itemId && !i.deleted);
  if (!item) throw new ChecklistMockError(404, "item de checklist não encontrado");
  item.deleted = true;
}

function strip(item: MockChecklistItem): ChecklistItem {
  const { deleted: _drop, ...rest } = item;
  void _drop;
  return rest;
}

const SEED_TITULOS = [
  "Conferir uso de EPIs pela equipe",
  "Registrar avanço da concretagem",
  "Verificar limpeza e organização do canteiro",
  "Checar recebimento de materiais do dia",
  "Fotografar frente de serviço concluída",
];

let seeded = false;
export function ensureChecklistSeed(): void {
  if (seeded) return;
  seeded = true;
  // Semeia as 3 obras mais recentes (topo da listagem) para a demo de campo.
  for (const obra of obras.slice(-3)) {
    SEED_TITULOS.forEach((titulo, idx) => {
      checklistItems.push({
        id: nextId(),
        obra_id: obra.id,
        titulo,
        completed: idx < 2, // dois já concluídos
        completed_at: idx < 2 ? nowIso() : null,
        sort_order: idx,
        created_at: nowIso(),
        deleted: false,
      });
    });
  }
}
