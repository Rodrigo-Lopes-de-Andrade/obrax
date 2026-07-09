import { api } from "./client";
import type { DashboardSummary } from "./types";

/** KPIs agregados do tenant (B4.4). Cacheados 60s no backend. */
export const getDashboardSummary = (): Promise<DashboardSummary> =>
  api.get<DashboardSummary>("/api/v1/dashboard/summary");
