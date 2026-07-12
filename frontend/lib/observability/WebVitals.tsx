"use client";

import { useEffect } from "react";
import { useReportWebVitals } from "next/web-vitals";

import { capture } from "./analytics";
import { installGlobalErrorHandlers } from "./errors";

/**
 * Ponto único de observabilidade no client (F11.5). Reporta Core Web Vitals
 * (LCP/INP/CLS/FCP/TTFB) pro sink de analytics via o hook nativo do Next e liga
 * os handlers globais de erro. Sem env de analytics configurada, tudo vira
 * no-op — pode ficar montado no layout sem custo em dev/CI.
 */
export function WebVitals() {
  useReportWebVitals((metric) => {
    capture("$web_vitals", {
      metric_name: metric.name,
      metric_value: metric.value,
      metric_rating: metric.rating,
      metric_id: metric.id,
      navigation_type: metric.navigationType,
    });
  });
  useEffect(() => {
    installGlobalErrorHandlers();
  }, []);
  return null;
}
