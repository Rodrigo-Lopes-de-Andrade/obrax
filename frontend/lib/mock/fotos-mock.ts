/**
 * Mock das fotos de campo (B8.2/B8.3, US-09/US-17). Espelha gestao/fotos: sync
 * idempotente por client_photo_id, dedup por sha256, confirm marcando
 * sincronizado. O "storage" é uma Map em memória: o PUT guarda os bytes e o
 * GET os serve — assim a galeria mostra a miniatura real da foto enviada.
 */
import type { Photo, PhotoSyncResult } from "@/lib/api/types";
import { nextId, obras } from "./db";

export const photos: Photo[] = [];

/** Bytes "no bucket", chaveados pelo id da foto (o PUT do cliente popula aqui). */
export const storageBlobs = new Map<string, { bytes: ArrayBuffer; type: string }>();

export class FotosMockError extends Error {
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
    throw new FotosMockError(422, "obra não encontrada");
  }
}

function presign(photoId: string): PhotoSyncResult {
  return { photo_id: photoId, upload_url: `/_mock/storage/${photoId}`, method: "PUT", expires_in: 900 };
}

export function syncPhotoMock(
  obraId: string,
  clientPhotoId: string,
  sha256: string,
  sizeBytes: number,
  capturedAt: string,
): PhotoSyncResult {
  assertObra(obraId);
  const existing = photos.find((p) => p.client_photo_id === clientPhotoId);
  if (existing) {
    if (existing.sync_status === "sincronizado") {
      throw new FotosMockError(409, "foto já sincronizada");
    }
    return presign(existing.id); // retry idempotente (ainda pendente)
  }
  if (photos.some((p) => p.sha256 === sha256)) {
    throw new FotosMockError(409, "foto duplicada: mesmo conteúdo já enviado");
  }
  const photo: Photo = {
    id: nextId(),
    obra_id: obraId,
    ocorrencia_id: null,
    client_photo_id: clientPhotoId,
    sha256,
    size_bytes: sizeBytes,
    sync_status: "pendente",
    captured_at: capturedAt,
    synced_at: null,
    created_at: nowIso(),
    download_url: null,
  };
  photos.push(photo);
  return presign(photo.id);
}

export function confirmPhotoMock(photoId: string): Photo {
  const p = photos.find((x) => x.id === photoId);
  if (!p) throw new FotosMockError(404, "foto não encontrada");
  p.sync_status = "sincronizado";
  p.synced_at = nowIso();
  p.download_url = `/_mock/storage/${p.id}`;
  return p;
}

export function listPhotosMock(obraId: string): { items: Photo[]; next_cursor: null } {
  if (!obras.some((o) => o.id === obraId)) {
    throw new FotosMockError(404, "obra não encontrada");
  }
  const rows = [...photos]
    .filter((p) => p.obra_id === obraId)
    .sort((a, b) => (a.id < b.id ? 1 : a.id > b.id ? -1 : 0));
  return { items: rows, next_cursor: null };
}

/** SVG "polaroide" como bytes — semeia fotos sincronizadas p/ a galeria da demo. */
function seedImage(label: string, hue: number): ArrayBuffer {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
    <rect width="400" height="400" fill="hsl(${hue} 45% 30%)"/>
    <rect x="40" y="40" width="320" height="240" fill="hsl(${hue} 40% 55%)"/>
    <circle cx="200" cy="160" r="60" fill="hsl(${hue} 30% 75%)"/>
    <text x="200" y="340" font-family="sans-serif" font-size="26" fill="#fff"
      text-anchor="middle">${label}</text>
  </svg>`;
  return new TextEncoder().encode(svg).buffer as ArrayBuffer;
}

let seeded = false;
export function ensureFotosSeed(): void {
  if (seeded) return;
  seeded = true;
  const obra = obras[obras.length - 1];
  if (!obra) return;
  ["Fachada", "Laje concretada"].forEach((label, i) => {
    const id = nextId();
    storageBlobs.set(id, { bytes: seedImage(label, i === 0 ? 210 : 150), type: "image/svg+xml" });
    photos.push({
      id,
      obra_id: obra.id,
      ocorrencia_id: null,
      client_photo_id: nextId(),
      sha256: "seed" + i,
      size_bytes: 120_000,
      sync_status: "sincronizado",
      captured_at: nowIso(),
      synced_at: nowIso(),
      created_at: nowIso(),
      download_url: `/_mock/storage/${id}`,
    });
  });
}
