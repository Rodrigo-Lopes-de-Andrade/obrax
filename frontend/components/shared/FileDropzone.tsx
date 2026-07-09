"use client";

import * as React from "react";
import { UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";

/** Extensões aceitas no GED (docs/SPRINTS.md F3.1). */
export const DEFAULT_ACCEPT = [
  "pdf",
  "dwg",
  "jpg",
  "jpeg",
  "png",
  "xlsx",
  "docx",
];

interface FileDropzoneProps {
  onFiles: (files: File[]) => void;
  accept?: string[];
  disabled?: boolean;
  className?: string;
}

function ext(name: string): string {
  return name.slice(name.lastIndexOf(".") + 1).toLowerCase();
}

export function FileDropzone({
  onFiles,
  accept = DEFAULT_ACCEPT,
  disabled = false,
  className,
}: FileDropzoneProps) {
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handle = React.useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      const all = Array.from(fileList);
      const valid = all.filter((f) => accept.includes(ext(f.name)));
      const rejected = all.length - valid.length;
      if (rejected > 0) {
        toast.error(
          `${rejected} arquivo(s) ignorado(s): tipo não suportado (${accept.join(", ")})`,
        );
      }
      if (valid.length) onFiles(valid);
    },
    [accept, onFiles],
  );

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) handle(e.dataTransfer.files);
      }}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-8 text-center transition-colors outline-none",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        dragging
          ? "border-primary bg-primary/5"
          : "border-border hover:border-muted-foreground/40 hover:bg-muted/40",
        disabled && "pointer-events-none opacity-60",
        className,
      )}
    >
      <div className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <UploadCloud className="size-5" />
      </div>
      <div className="space-y-0.5">
        <p className="text-sm font-medium">
          Arraste arquivos ou{" "}
          <span className="text-primary">clique para selecionar</span>
        </p>
        <p className="text-xs text-muted-foreground uppercase">
          {accept.join(" · ")}
        </p>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept.map((e) => `.${e}`).join(",")}
        className="hidden"
        onChange={(e) => {
          handle(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
