import { File, FileText, Image, Receipt, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { DocumentoTipo } from "@/lib/api/types";

const TIPO_META: Record<
  DocumentoTipo,
  { label: string; Icon: LucideIcon; dot: string; iconColor: string }
> = {
  projeto: { label: "Projeto", Icon: FileText, dot: "bg-sky-400", iconColor: "text-sky-400" },
  contrato: { label: "Contrato", Icon: FileText, dot: "bg-violet-400", iconColor: "text-violet-400" },
  nota_fiscal: { label: "Nota fiscal", Icon: Receipt, dot: "bg-amber-400", iconColor: "text-amber-400" },
  foto: { label: "Foto", Icon: Image, dot: "bg-emerald-400", iconColor: "text-emerald-400" },
  outro: { label: "Outro", Icon: File, dot: "bg-muted-foreground", iconColor: "text-muted-foreground" },
};

/** Opções na ordem do enum `documento_tipo` (backend). */
export const DOC_TIPO_OPTIONS = (Object.keys(TIPO_META) as DocumentoTipo[]).map(
  (value) => ({ value, label: TIPO_META[value].label }),
);

/** Categorias sugeridas (o backend aceita texto livre — isto é só a UI). */
export const CATEGORIAS_SUGERIDAS = [
  "Projetos",
  "Contratos",
  "Notas Fiscais",
  "Registro de Obra",
  "Licenças",
  "Outros",
];

export function tipoLabel(tipo: DocumentoTipo): string {
  return TIPO_META[tipo].label;
}

export function DocTipoIcon({
  tipo,
  className,
}: {
  tipo: DocumentoTipo;
  className?: string;
}) {
  const { Icon, iconColor } = TIPO_META[tipo];
  return <Icon className={className ?? `size-4 ${iconColor}`} />;
}

export function DocTipoBadge({ tipo }: { tipo: DocumentoTipo }) {
  const meta = TIPO_META[tipo];
  return (
    <Badge variant="outline" className="gap-1.5 font-normal">
      <span className={`size-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </Badge>
  );
}
