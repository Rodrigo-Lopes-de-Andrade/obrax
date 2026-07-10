import type { MetadataRoute } from "next";

/** Web App Manifest (F7.2) — servido em /manifest.webmanifest. O app de campo é
 * instalável (display standalone) e abre direto em /campo. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Obrax Campo",
    short_name: "Obrax",
    description: "Checklist e registro de obra em campo, com suporte offline",
    start_url: "/campo",
    scope: "/campo",
    display: "standalone",
    orientation: "portrait",
    background_color: "#1a1c24",
    theme_color: "#1a1c24",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
