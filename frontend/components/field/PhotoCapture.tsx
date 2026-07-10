"use client";

import * as React from "react";
import imageCompression from "browser-image-compression";
import { Camera, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { toast } from "sonner";

/** Foto já comprimida no cliente, pronta p/ hash + fila offline. */
export interface CapturedPhoto {
  file: File;
  /** object URL do arquivo comprimido (preview). O chamador revoga ao descartar. */
  previewUrl: string;
}

/**
 * Compressão no cliente (F8.1): reduz p/ 1600px / q=0.7 / ≤400KB antes de sair
 * do aparelho — economiza dados e cabe no limite de 2 MB do backend. `preserveExif`
 * mantém a orientação/metadados. Roda em Web Worker p/ não travar a UI.
 */
const COMPRESSION = {
  maxWidthOrHeight: 1600,
  initialQuality: 0.7,
  maxSizeMB: 0.4,
  useWebWorker: true,
  preserveExif: true,
} as const;

interface PhotoCaptureProps {
  onCapture: (photo: CapturedPhoto) => void;
  disabled?: boolean;
  /** Rótulo do botão (default "Tirar foto"). */
  children?: React.ReactNode;
  variant?: React.ComponentProps<typeof Button>["variant"];
}

export function PhotoCapture({ onCapture, disabled, children, variant }: PhotoCaptureProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [busy, setBusy] = React.useState(false);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Zera o input para permitir recapturar o mesmo arquivo em seguida.
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      const compressed = await imageCompression(file, COMPRESSION);
      // browser-image-compression devolve um Blob; normaliza p/ File nomeado.
      const named = new File([compressed], file.name || "foto.jpg", {
        type: compressed.type || "image/jpeg",
        lastModified: file.lastModified,
      });
      onCapture({ file: named, previewUrl: URL.createObjectURL(named) });
    } catch {
      toast.error("Não foi possível processar a foto. Tente novamente.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={onFile}
      />
      <Button
        type="button"
        variant={variant ?? "default"}
        size="lg"
        disabled={disabled || busy}
        onClick={() => inputRef.current?.click()}
        className="gap-2"
      >
        {busy ? <Loader2 className="animate-spin" /> : <Camera />}
        {busy ? "Processando…" : (children ?? "Tirar foto")}
      </Button>
    </>
  );
}
