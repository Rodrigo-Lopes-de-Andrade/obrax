import { api, ApiError } from "./client";
import type { Page, Photo, PhotoSyncInput, PhotoSyncResult } from "./types";

/** Etapa 1 do upload (US-09): registra a foto e recebe a URL de PUT assinada. O
 * `client_photo_id` (chave de idempotência do aparelho) viaja no Idempotency-Key. */
export function syncPhoto(input: PhotoSyncInput, clientPhotoId: string): Promise<PhotoSyncResult> {
  return api.post("/api/v1/photos/sync", input, { "Idempotency-Key": clientPhotoId });
}

/** Etapa 2: PUT direto no storage (fora da API). Corpo binário, sem JSON. */
export async function uploadToStorage(url: string, blob: Blob): Promise<void> {
  const res = await fetch(url, { method: "PUT", body: blob });
  if (!res.ok) {
    throw new ApiError(res.status, { status: res.status, title: "falha no upload ao storage" });
  }
}

/** Etapa 3: confirma o upload (valida tamanho/hash no servidor, marca sincronizada). */
export function confirmPhoto(photoId: string): Promise<Photo> {
  return api.post(`/api/v1/photos/${photoId}/confirm`, {});
}

export function getPhotos(obraId: string): Promise<Page<Photo>> {
  return api.get(`/api/v1/obras/${obraId}/photos?limit=100`);
}
