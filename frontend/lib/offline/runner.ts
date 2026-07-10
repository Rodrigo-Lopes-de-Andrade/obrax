/**
 * Loop de sincronização em background (F7.5). Aciona o `flushQueue` a cada 30s,
 * quando a rede volta (`online`) e quando a aba reabre (`visibilitychange`) —
 * garantindo o envio das mutações pendentes sem ação do usuário. O backoff por
 * mutação vive no motor (sync.ts); aqui é só o agendamento.
 */
import { flushQueue } from "./sync";

const INTERVAL_MS = 30_000;

function online(): boolean {
  return typeof navigator === "undefined" || navigator.onLine !== false;
}

/** Inicia o loop e devolve um cleanup (remove timer + listeners). */
export function startSyncLoop(): () => void {
  const tick = () => {
    if (online()) void flushQueue();
  };

  // Drena imediatamente o que sobrou de sessões anteriores.
  tick();
  const interval = setInterval(tick, INTERVAL_MS);

  const onOnline = () => void flushQueue();
  const onVisible = () => {
    if (document.visibilityState === "visible") tick();
  };
  window.addEventListener("online", onOnline);
  document.addEventListener("visibilitychange", onVisible);

  return () => {
    clearInterval(interval);
    window.removeEventListener("online", onOnline);
    document.removeEventListener("visibilitychange", onVisible);
  };
}
