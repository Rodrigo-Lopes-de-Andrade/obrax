"use client";

import * as React from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  deleteDocumento,
  listDocumentos,
  updateDocumento,
  uploadDocumento,
  type ListDocumentosParams,
  type UploadOptions,
} from "@/lib/api/documentos";
import type { Documento, DocumentoUpdateInput, Page } from "@/lib/api/types";

export const documentosKeys = {
  all: (obraId: string) => ["documentos", obraId] as const,
  list: (obraId: string, params: ListDocumentosParams) =>
    ["documentos", obraId, "list", params] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export function useDocumentos(obraId: string, params: ListDocumentosParams) {
  return useQuery({
    queryKey: documentosKeys.list(obraId, params),
    queryFn: () => listDocumentos(obraId, params),
    placeholderData: keepPreviousData,
  });
}

export type UploadStatus = "uploading" | "done" | "error";

export interface UploadItem {
  key: string;
  name: string;
  status: UploadStatus;
}

/**
 * Fila de uploads: processa os arquivos em paralelo, expõe o status por arquivo
 * (para a barra de progresso) e invalida a listagem ao concluir.
 */
export function useUploadDocumentos(obraId: string) {
  const qc = useQueryClient();
  const [uploads, setUploads] = React.useState<UploadItem[]>([]);
  const seq = React.useRef(0);

  const upload = React.useCallback(
    async (files: File[], opts: UploadOptions) => {
      if (files.length === 0) return;
      const items: UploadItem[] = files.map((f) => ({
        key: `u${seq.current++}`,
        name: f.name,
        status: "uploading" as const,
      }));
      setUploads((prev) => [...items, ...prev]);

      const patch = (key: string, status: UploadStatus) =>
        setUploads((prev) =>
          prev.map((u) => (u.key === key ? { ...u, status } : u)),
        );

      let ok = 0;
      await Promise.all(
        files.map(async (file, i) => {
          try {
            await uploadDocumento(obraId, file, opts);
            patch(items[i].key, "done");
            ok += 1;
          } catch (error) {
            patch(items[i].key, "error");
            toast.error(`${file.name}: ${errorMessage(error)}`);
          }
        }),
      );

      if (ok > 0) {
        qc.invalidateQueries({ queryKey: documentosKeys.all(obraId) });
        toast.success(ok === 1 ? "Documento enviado" : `${ok} documentos enviados`);
      }
      // Limpa os concluídos após um instante; mantém os que falharam à vista.
      setTimeout(
        () => setUploads((prev) => prev.filter((u) => u.status === "error")),
        1500,
      );
    },
    [obraId, qc],
  );

  const dismiss = React.useCallback(
    (key: string) => setUploads((prev) => prev.filter((u) => u.key !== key)),
    [],
  );

  return { upload, uploads, dismiss };
}

export function useUpdateDocumento(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DocumentoUpdateInput }) =>
      updateDocumento(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: documentosKeys.all(obraId) });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteDocumento(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocumento(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: documentosKeys.all(obraId) });
      toast.success("Documento excluído");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

/** Escreve `visivel_cliente` em todas as listas em cache desta obra. */
function patchCaches(
  qc: ReturnType<typeof useQueryClient>,
  obraId: string,
  ids: Set<string>,
  visivel: boolean,
) {
  qc.setQueriesData<Page<Documento>>(
    { queryKey: documentosKeys.all(obraId) },
    (old) =>
      old
        ? {
            ...old,
            items: old.items.map((d) =>
              ids.has(d.id) ? { ...d, visivel_cliente: visivel } : d,
            ),
          }
        : old,
  );
}

/** Toggle otimista da visibilidade ao cliente (US-06): reflete imediato,
 * reverte no erro. A auditoria roda no backend via trigger (D3.2). */
export function useToggleVisibilidade(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, visivel }: { id: string; visivel: boolean }) =>
      updateDocumento(id, { visivel_cliente: visivel }),
    onMutate: async ({ id, visivel }) => {
      await qc.cancelQueries({ queryKey: documentosKeys.all(obraId) });
      const prev = qc.getQueriesData<Page<Documento>>({
        queryKey: documentosKeys.all(obraId),
      });
      patchCaches(qc, obraId, new Set([id]), visivel);
      return { prev };
    },
    onError: (error, _vars, ctx) => {
      ctx?.prev.forEach(([key, data]) => qc.setQueryData(key, data));
      toast.error(errorMessage(error));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: documentosKeys.all(obraId) });
    },
  });
}

/** Aplica visibilidade em lote (PATCH por documento — o backend ainda não tem
 * endpoint de bulk; contagens de documentos são pequenas no MVP). */
export function useBulkVisibilidade(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, visivel }: { ids: string[]; visivel: boolean }) =>
      Promise.all(
        ids.map((id) => updateDocumento(id, { visivel_cliente: visivel })),
      ),
    onSuccess: (_data, { ids, visivel }) => {
      qc.invalidateQueries({ queryKey: documentosKeys.all(obraId) });
      toast.success(
        `${ids.length} documento(s) marcado(s) como ${visivel ? "visível ao cliente" : "interno"}`,
      );
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
