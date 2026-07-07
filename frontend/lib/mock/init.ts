/** Inicia o worker MSW no browser (dev). Importado dinamicamente só no client. */
export async function enableMocking(): Promise<void> {
  const { setupWorker } = await import("msw/browser");
  const { handlers } = await import("./handlers");
  const worker = setupWorker(...handlers);
  await worker.start({ onUnhandledRequest: "bypass", quiet: true });
}
