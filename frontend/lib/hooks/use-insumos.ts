"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  listCategorias,
  searchInsumos,
  type SearchInsumosParams,
} from "@/lib/api/insumos";

export const insumoKeys = {
  all: ["insumos"] as const,
  search: (params: SearchInsumosParams) => ["insumos", "search", params] as const,
  categorias: ["insumos", "categorias"] as const,
};

export function useInsumos(params: SearchInsumosParams, enabled = true) {
  return useQuery({
    queryKey: insumoKeys.search(params),
    queryFn: () => searchInsumos(params),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export function useInsumoCategorias() {
  return useQuery({
    queryKey: insumoKeys.categorias,
    queryFn: listCategorias,
    staleTime: 5 * 60 * 1000,
  });
}
