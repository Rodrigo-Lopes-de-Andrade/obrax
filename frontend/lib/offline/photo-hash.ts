/**
 * SHA-256 hex do conteúdo de um Blob (F8.2), via Web Crypto. Calculado no
 * cliente antes do upload: alimenta a dedup por conteúdo e a checagem de
 * integridade no confirm do servidor. Requer contexto seguro (https/localhost).
 */
export async function sha256Hex(blob: Blob): Promise<string> {
  const buf = await blob.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
