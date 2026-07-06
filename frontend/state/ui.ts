import { create } from "zustand";
import type { ImportState, OrcamentoTab, PdfState } from "@/lib/types/orcamento";

interface UiState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  avatarMenuOpen: boolean;
  toggleAvatarMenu: () => void;
  closeAvatarMenu: () => void;

  budgetModalOpen: boolean;
  openBudgetModal: () => void;
  closeBudgetModal: () => void;

  activeTab: OrcamentoTab;
  setActiveTab: (tab: OrcamentoTab) => void;

  compareOpen: boolean;
  toggleCompare: () => void;

  pdfState: PdfState;
  generatePdf: () => void;

  markupPct: number;
  setMarkupPct: (pct: number) => void;
  admPct: number;
  setAdmPct: (pct: number) => void;

  importModalOpen: boolean;
  importState: ImportState;
  importDrag: boolean;
  hasTriedImportOnce: boolean;
  openImportModal: () => void;
  closeImportModal: () => void;
  resetImport: () => void;
  setImportDrag: (dragging: boolean) => void;
  startImportValidation: () => void;
  confirmImport: () => void;
}

export const useUiStore = create<UiState>((set, get) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  avatarMenuOpen: false,
  toggleAvatarMenu: () => set((s) => ({ avatarMenuOpen: !s.avatarMenuOpen })),
  closeAvatarMenu: () => set({ avatarMenuOpen: false }),

  budgetModalOpen: false,
  openBudgetModal: () => set({ budgetModalOpen: true }),
  closeBudgetModal: () => set({ budgetModalOpen: false }),

  activeTab: "Custos",
  setActiveTab: (tab) => set({ activeTab: tab }),

  compareOpen: false,
  toggleCompare: () => set((s) => ({ compareOpen: !s.compareOpen })),

  pdfState: "idle",
  generatePdf: () => {
    if (get().pdfState === "loading") return;
    if (get().pdfState === "done") {
      set({ pdfState: "idle" });
      return;
    }
    set({ pdfState: "loading" });
    setTimeout(() => set({ pdfState: "done" }), 2000);
  },

  markupPct: 25,
  setMarkupPct: (pct) => set({ markupPct: pct }),
  admPct: 8,
  setAdmPct: (pct) => set({ admPct: pct }),

  importModalOpen: false,
  importState: "closed",
  importDrag: false,
  hasTriedImportOnce: false,
  openImportModal: () => set({ importModalOpen: true, importState: "upload", importDrag: false }),
  closeImportModal: () => set({ importModalOpen: false, importState: "closed" }),
  resetImport: () => set({ importState: "upload", importDrag: false }),
  setImportDrag: (dragging) => set({ importDrag: dragging }),
  startImportValidation: () => {
    set({ importState: "processing" });
    const next = get().hasTriedImportOnce ? "clean" : "errors";
    set({ hasTriedImportOnce: true });
    setTimeout(() => set({ importState: next }), 1600);
  },
  confirmImport: () => {
    if (get().importState !== "clean") return;
    set({ importState: "done" });
  },
}));
