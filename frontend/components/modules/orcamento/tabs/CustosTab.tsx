"use client";

import { useState } from "react";
import { EapTree } from "@/components/modules/orcamento/EapTree";
import { eapInicial } from "@/lib/mock/dashboard-obra";
import { useUiStore } from "@/state/ui";

export function CustosTab() {
  const [fases, setFases] = useState(eapInicial);
  const openImportModal = useUiStore((s) => s.openImportModal);

  return <EapTree fases={fases} onChange={setFases} onOpenImport={openImportModal} />;
}
