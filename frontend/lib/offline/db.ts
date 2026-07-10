/**
 * Fila de mutações offline (F7.3). O app de campo grava as ações localmente
 * (IndexedDB via Dexie) e um worker (F7.5) as envia ao servidor quando há rede.
 * Cada linha carrega `status` (pending/uploading/failed) e o backoff
 * (`nextAttemptAt` + `attempts`), então a fila sobrevive a reload e offline.
 *
 * O módulo só toca o IndexedDB no browser — os componentes que o usam são
 * client-only; `new Dexie()` em si é inerte até a primeira query.
 */
import Dexie, { type Table } from "dexie";

export type MutationStatus = "pending" | "uploading" | "failed";

/** Tipos de mutação enfileiráveis. O worker despacha por `type`. */
export type MutationType =
  | "checklist.toggle"
  | "checklist.create"
  | "checklist.delete"
  | "photo.upload";

export interface QueuedMutation {
  id?: number;
  type: MutationType;
  /** Entidade alvo (ex.: id do checklist_item) — usado p/ dedup e UI. */
  entityId: string;
  /** Rótulo humano p/ a lista de pendências ("Concluir: Conferir EPIs"). */
  label: string;
  payload: Record<string, unknown>;
  status: MutationStatus;
  attempts: number;
  lastError?: string;
  /** Epoch ms: o worker só tenta a partir deste instante (backoff). */
  nextAttemptAt: number;
  createdAt: number;
}

/**
 * Blob da foto capturada, guardado no IndexedDB até o upload confirmar (F8.2).
 * Fica separado da fila de mutações (blobs são grandes; a fila é leve) e é
 * chaveado pelo `clientPhotoId` — a mesma chave de idempotência da mutação
 * `photo.upload` (entityId) e do header Idempotency-Key no sync.
 */
export interface PhotoUpload {
  clientPhotoId: string;
  obraId: string;
  blob: Blob;
  sha256: string;
  sizeBytes: number;
  capturedAt: string;
  createdAt: number;
}

class OfflineDB extends Dexie {
  mutations!: Table<QueuedMutation, number>;
  photos!: Table<PhotoUpload, string>;

  constructor() {
    super("obrax-offline");
    // Índices: status (fila do worker/badge), entityId (dedup), nextAttemptAt.
    this.version(1).stores({
      mutations: "++id, status, entityId, type, nextAttemptAt",
    });
    // v2 (F8.2): tabela de blobs de foto, chaveada por clientPhotoId.
    this.version(2).stores({
      mutations: "++id, status, entityId, type, nextAttemptAt",
      photos: "clientPhotoId, obraId",
    });
  }
}

export const offlineDB = new OfflineDB();

/** Enfileira uma mutação nova como `pending` (pronta p/ envio imediato). */
export async function enqueue(
  input: Pick<QueuedMutation, "type" | "entityId" | "label" | "payload">,
): Promise<number> {
  const now = Date.now();
  return offlineDB.mutations.add({
    ...input,
    status: "pending",
    attempts: 0,
    nextAttemptAt: now,
    createdAt: now,
  });
}

/**
 * Toggle de checklist com dedup: colapsa toggles pendentes/falhos do mesmo item
 * num único registro (last-write-wins) — evita a fila inflar com idas e vindas
 * do mesmo item e mantém a idempotência (o servidor só precisa do estado final).
 * Mutações já em `uploading` não são tocadas (estão em voo).
 */
export async function enqueueChecklistToggle(input: {
  itemId: string;
  completed: boolean;
  label: string;
}): Promise<void> {
  await offlineDB.transaction("rw", offlineDB.mutations, async () => {
    await offlineDB.mutations
      .where("entityId")
      .equals(input.itemId)
      .filter((m) => m.type === "checklist.toggle" && m.status !== "uploading")
      .delete();
    await enqueue({
      type: "checklist.toggle",
      entityId: input.itemId,
      label: input.label,
      payload: { completed: input.completed },
    });
  });
}

/** Recoloca uma mutação falha na fila (retry manual — F7.6). */
export async function retryMutation(id: number): Promise<void> {
  await offlineDB.mutations.update(id, {
    status: "pending",
    nextAttemptAt: Date.now(),
    lastError: undefined,
  });
}

/** Reagenda todas as falhas para envio imediato (botão "tentar agora"). */
export async function retryAllFailed(): Promise<void> {
  await offlineDB.mutations
    .where("status")
    .equals("failed")
    .modify({ status: "pending", nextAttemptAt: Date.now(), lastError: undefined });
}

/** Remove uma mutação da fila (descartar). */
export async function discardMutation(id: number): Promise<void> {
  await offlineDB.mutations.delete(id);
}

/**
 * Enfileira o upload de uma foto (F8.2): guarda o blob e cria a mutação
 * `photo.upload` numa única transação. O `clientPhotoId` liga as duas e garante
 * idempotência ponta a ponta (fila → Idempotency-Key → dedup no backend).
 */
export async function enqueuePhotoUpload(input: {
  clientPhotoId: string;
  obraId: string;
  blob: Blob;
  sha256: string;
  sizeBytes: number;
  capturedAt: string;
  label: string;
}): Promise<void> {
  const now = Date.now();
  await offlineDB.transaction("rw", offlineDB.mutations, offlineDB.photos, async () => {
    await offlineDB.photos.put({
      clientPhotoId: input.clientPhotoId,
      obraId: input.obraId,
      blob: input.blob,
      sha256: input.sha256,
      sizeBytes: input.sizeBytes,
      capturedAt: input.capturedAt,
      createdAt: now,
    });
    await offlineDB.mutations.add({
      type: "photo.upload",
      entityId: input.clientPhotoId,
      label: input.label,
      payload: { obraId: input.obraId },
      status: "pending",
      attempts: 0,
      nextAttemptAt: now,
      createdAt: now,
    });
  });
}

export function getPhotoUpload(clientPhotoId: string): Promise<PhotoUpload | undefined> {
  return offlineDB.photos.get(clientPhotoId);
}

/** Descarta o blob após o upload confirmar (ou o servidor reportar duplicata). */
export async function deletePhotoUpload(clientPhotoId: string): Promise<void> {
  await offlineDB.photos.delete(clientPhotoId);
}
