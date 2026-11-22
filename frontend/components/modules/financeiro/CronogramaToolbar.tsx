"use client";

import { Info, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ToolbarProps {
  /** `undefined` enquanto o papel (GET /auth/me) carrega: não mostra aviso nenhum. */
  podeEditar: boolean | undefined;
  /** ISO de `cronograma.bloqueado_em`; não nulo = só leitura. */
  bloqueadoEm: string | null;
  alterado: boolean;
  /** Motivos que impedem salvar (fase que não soma 100%, célula inválida). */
  problemas: string[];
  salvando: boolean;
  /** Mensagem do backend ao recusar o PUT (traz a fase e a diferença). */
  erroServidor: string | null;
  onSalvar: () => void;
  onDescartar: () => void;
}

function dataBr(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

export function CronogramaToolbar({
  podeEditar,
  bloqueadoEm,
  alterado,
  problemas,
  salvando,
  erroServidor,
  onSalvar,
  onDescartar,
}: ToolbarProps) {
  const erro = erroServidor ? (
    <p role="alert" className="text-sm font-medium text-foreground">
      Não foi possível salvar: {erroServidor}
    </p>
  ) : null;

  if (podeEditar === undefined) return <div className="h-5" aria-hidden="true" />;

  if (bloqueadoEm) {
    return (
      <div className="space-y-2">
      <div role="status" className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm">
        <Lock className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <p>
          <strong>Cronograma bloqueado para edição</strong> desde {dataBr(bloqueadoEm)}. Existe medição aprovada, e
          mudar a linha de base depois disso invalidaria a comparação. A grade abre somente para leitura.
        </p>
      </div>
      {erro}
      </div>
    );
  }
  if (!podeEditar) {
    return (
      <div role="status" className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm">
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <p>Seu papel permite apenas consultar o cronograma. A edição é de owner, admin e financeiro.</p>
      </div>
    );
  }

  const motivo =
    problemas.length > 0
      ? "Não é possível salvar enquanto houver pendências:"
      : !alterado
        ? "Nenhuma alteração para salvar."
        : null;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          onClick={onSalvar}
          disabled={salvando || motivo !== null}
          aria-describedby="cronograma-motivo"
        >
          {salvando ? "Salvando..." : "Salvar cronograma"}
        </Button>
        <Button variant="outline" onClick={onDescartar} disabled={salvando || !alterado}>
          Descartar alterações
        </Button>
      </div>
      <div id="cronograma-motivo" className="text-sm">
        {motivo ? <p className="text-muted-foreground">{motivo}</p> : null}
        {problemas.length > 0 ? (
          <ul className="list-disc pl-5 text-foreground">
            {problemas.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        ) : null}
      </div>
      {erro}
    </div>
  );
}
