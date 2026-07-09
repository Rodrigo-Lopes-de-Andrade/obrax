import { api } from "./client";
import type {
  Documento,
  DocumentoCreateInput,
  DocumentoTipo,
  DocumentoUpdateInput,
  DocumentoUpload,
  Page,
} from "./types";

export interface ListDocumentosParams {
  categoria?: string | null;
  search?: string | null;
  cursor?: string | null;
  limit?: number;
}

function buildQuery(params: ListDocumentosParams): string {
  const q = new URLSearchParams();
  if (params.categoria) q.set("categoria", params.categoria);
  if (params.search) q.set("search", params.search);
  if (params.cursor) q.set("cursor", params.cursor);
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

export const listDocumentos = (
  obraId: string,
  params: ListDocumentosParams = {},
): Promise<Page<Documento>> =>
  api.get<Page<Documento>>(
    `/api/v1/obras/${obraId}/documentos${buildQuery(params)}`,
  );

export const updateDocumento = (
  id: string,
  data: DocumentoUpdateInput,
): Promise<Documento> =>
  api.patch<Documento>(`/api/v1/documentos/${id}`, data);

export const deleteDocumento = (id: string): Promise<void> =>
  api.delete(`/api/v1/documentos/${id}`);

async function sha256Hex(buffer: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export interface UploadOptions {
  tipo: DocumentoTipo;
  categoria?: string | null;
}

/**
 * Upload em duas etapas (docs/ESPEC.md § 7), idêntico p/ mock e backend real:
 * create (metadados + hash) → PUT direto na URL assinada → confirm. O PUT usa
 * `fetch` cru (sem credenciais/JSON) porque vai direto ao storage.
 */
export async function uploadDocumento(
  obraId: string,
  file: File,
  opts: UploadOptions,
): Promise<Documento> {
  const buffer = await file.arrayBuffer();
  const sha256 = await sha256Hex(buffer);

  const created = await api.post<DocumentoUpload>(
    `/api/v1/obras/${obraId}/documentos`,
    {
      nome: file.name,
      tipo: opts.tipo,
      sha256,
      size_bytes: file.size,
      categoria: opts.categoria ?? null,
    } satisfies DocumentoCreateInput,
  );

  const put = await fetch(created.upload_url, {
    method: created.method,
    body: buffer,
  });
  if (!put.ok) throw new Error("Falha no upload do arquivo");

  return api.post<Documento>(
    `/api/v1/documentos/${created.documento_id}/confirm`,
    {},
  );
}
