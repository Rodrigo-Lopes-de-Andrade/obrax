import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Estado leve do app de campo (persistido em localStorage). Guarda a última
 * obra aberta para a aba "Checklist" da BottomNav levar direto a ela. */
interface FieldState {
  lastObraId: string | null;
  setLastObra: (id: string) => void;
}

export const useFieldStore = create<FieldState>()(
  persist(
    (set) => ({
      lastObraId: null,
      setLastObra: (id) => set({ lastObraId: id }),
    }),
    { name: "obrax-field" },
  ),
);
