import type { Metadata, Viewport } from "next";
import { Manrope, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { WebVitals } from "@/lib/observability/WebVitals";

const manrope = Manrope({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Obrax",
  description: "Mini-ERP para pequenas construtoras e reformadoras",
  // PWA (F7.2): habilita "adicionar à tela inicial" no iOS com barra imersiva.
  appleWebApp: { capable: true, title: "Obrax", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  themeColor: "#1a1c24",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="dark">
      <body
        className={`${manrope.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <WebVitals />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
