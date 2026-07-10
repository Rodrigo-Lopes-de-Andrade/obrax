/**
 * Motor de sincronização da fila offline (F7.4/F7.5). Drena as mutações
 * `pending` cujo backoff já venceu, despacha cada uma para a API por `type`,
 * remove da fila em caso de sucesso e aplica backoff exponencial no erro.
 *
 * Reentrância: um único flush corre por vez (`running`) — o timer (F7.5) e o
 * disparo imediato pós-toggle compartilham este drain sem duplicar envios.
 */
import { ApiError } from "@/lib/api/client";
import { deleteChecklistItem, updateChecklistItem } from "@/lib/api/checklist";
import { confirmPhoto, syncPhoto, uploadToStorage } from "@/lib/api/fotos";
import { deletePhotoUpload, getPhotoUpload, offlineDB, type QueuedMutation } from "./db";

const MAX_ATTEMPTS = 6;
const BASE_BACKOFF_MS = 2_000; // 2s, 4s, 8s, ... (teto ~1min)
const MAX_BACKOFF_MS = 60_000;

export interface FlushResult {
  sent: number;
  failed: number;
}

/**
 * Upload de foto em 3 etapas (F8.3/F8.4): sync (presigned) → PUT no storage →
 * confirm. Idempotente pelo `clientPhotoId` (= entityId). 409 (já sincronizada
 * ou conteúdo duplicado) e 404 (sumiu no servidor) são terminais: descarta o
 * blob e trata como sucesso (retry seria inútil). Erros transitórios propagam
 * para o backoff. O blob é removido ao confirmar.
 */
async function dispatchPhoto(m: QueuedMutation): Promise<void> {
  const upload = await getPhotoUpload(m.entityId);
  if (!upload) return; // blob já processado/ausente — nada a fazer
  try {
    const { photo_id, upload_url } = await syncPhoto(
      {
        obra_id: upload.obraId,
        sha256: upload.sha256,
        size_bytes: upload.sizeBytes,
        captured_at: upload.capturedAt,
      },
      upload.clientPhotoId,
    );
    await uploadToStorage(upload_url, upload.blob);
    await confirmPhoto(photo_id);
  } catch (err) {
    if (err instanceof ApiError && (err.status === 409 || err.status === 404)) {
      await deletePhotoUpload(m.entityId);
      return;
    }
    throw err;
  }
  await deletePhotoUpload(m.entityId);
}

async function dispatch(m: QueuedMutation): Promise<void> {
  switch (m.type) {
    case "checklist.toggle":
      await updateChecklistItem(m.entityId, { completed: Boolean(m.payload.completed) });
      return;
    case "checklist.delete":
      await deleteChecklistItem(m.entityId);
      return;
    case "checklist.create":
      // Reservado p/ criação offline (temp-id) — ainda não usado.
      throw new Error("checklist.create ainda não suportado offline");
    case "photo.upload":
      await dispatchPhoto(m);
      return;
  }
}

function errMsg(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

let running = false;

/** Drena a fila uma vez. Seguro chamar concorrentemente (no-op se já em curso). */
export async function flushQueue(): Promise<FlushResult> {
  if (running) return { sent: 0, failed: 0 };
  running = true;
  let sent = 0;
  let failed = 0;
  try {
    const now = Date.now();
    const ready = await offlineDB.mutations
      .where("status")
      .equals("pending")
      .filter((m) => m.nextAttemptAt <= now)
      .toArray();

    for (const m of ready) {
      if (m.id == null) continue;
      await offlineDB.mutations.update(m.id, { status: "uploading" });
      try {
        await dispatch(m);
        await offlineDB.mutations.delete(m.id);
        sent += 1;
      } catch (err) {
        failed += 1;
        const attempts = m.attempts + 1;
        // 404 = alvo não existe mais no servidor → descarta (retry é inútil).
        if (err instanceof ApiError && err.status === 404) {
          await offlineDB.mutations.delete(m.id);
          continue;
        }
        if (attempts >= MAX_ATTEMPTS) {
          await offlineDB.mutations.update(m.id, {
            status: "failed",
            attempts,
            lastError: errMsg(err),
          });
        } else {
          const backoff = Math.min(BASE_BACKOFF_MS * 2 ** (attempts - 1), MAX_BACKOFF_MS);
          await offlineDB.mutations.update(m.id, {
            status: "pending",
            attempts,
            nextAttemptAt: Date.now() + backoff,
            lastError: errMsg(err),
          });
        }
      }
    }
  } finally {
    running = false;
  }
  return { sent, failed };
}
