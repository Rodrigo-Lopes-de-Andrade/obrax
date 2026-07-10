"use client";

import * as React from "react";

import { startSyncLoop } from "@/lib/offline/runner";

/** Sobe o loop de sync enquanto o app de campo está montado. Renderiza nada. */
export function SyncProvider() {
  React.useEffect(() => startSyncLoop(), []);
  return null;
}
