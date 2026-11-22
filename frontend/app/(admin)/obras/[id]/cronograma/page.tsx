"use client";

import { CalendarRange } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import {
  CronogramaGrid,
  calcularModelo,
  igualAoBase,
  montarAlocacoes,
  type Draft,
} from "@/components/modules/financeiro/CronogramaGrid";
import { CronogramaToolbar } from "@/components/modules/financeiro/CronogramaToolbar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import type { CronogramaGradeOut, Periodicidade } from "@/lib/api/types";
import {
  mensagemErro,
  podeEditarCronograma,
  useCriarCronograma,
  useCronograma,
  useSalvarAlocacoes,
} from "@/lib/hooks/use-cronograma";
import { useMe } from "@/lib/hooks/use-session";

const SEM_RASCUNHO: Draft = {};

export default function CronogramaPage() {
  const { id } = useParams<{ id: string }>();
  const me = useMe();
  const cron = useCronograma(id);
  const semCronograma = cron.error instanceof ApiError && cron.error.status === 404;
  // `undefined` = papel ainda carregando (nenhum aviso de permissão até saber).
  const podeEditar = me.isPending ? undefined : podeEditarCronograma(me.data?.role);

  return (
    <section aria-labelledby="cronograma-titulo" className="space-y-4">
      <div>
        <h2 id="cronograma-titulo" className="text-lg font-semibold tracking-tight">
          Cronograma físico-financeiro
        </h2>
        <p className="text-sm text-muted-foreground">
          Quanto de cada fase acontece em cada período. Cada fase precisa somar exatamente 100%.
        </p>
      </div>

      {cron.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : cron.data ? (
        <Editor key={cron.data.cronograma.id} obraId={id} grade={cron.data} podeEditar={podeEditar} />
      ) : semCronograma ? (
        podeEditar === undefined ? (
          <Skeleton className="h-64 w-full" />
        ) : podeEditar ? (
          <CriarCronograma obraId={id} />
        ) : (
          <p role="status" className="rounded-lg border border-border bg-muted/40 p-3 text-sm">
            Esta obra ainda não tem cronograma. A geração é de owner, admin e financeiro.
          </p>
        )
      ) : (
        <div role="alert" className="space-y-2 text-sm">
          <p>Não foi possível carregar o cronograma: {mensagemErro(cron.error)}</p>
          <Button variant="outline" onClick={() => void cron.refetch()} disabled={cron.isFetching}>
            Tentar novamente
          </Button>
        </div>
      )}
    </section>
  );
}

function Editor({
  obraId,
  grade,
  podeEditar,
}: {
  obraId: string;
  grade: CronogramaGradeOut;
  podeEditar: boolean | undefined;
}) {
  const [draft, setDraft] = useState<Draft>({});
  const salvar = useSalvarAlocacoes(obraId, grade.cronograma.id);
  const bloqueado = grade.cronograma.bloqueado_em !== null;
  // Bloqueou no meio da edição (409): a grade do servidor vence o rascunho.
  const efetivo = bloqueado ? SEM_RASCUNHO : draft;
  const modelo = useMemo(() => calcularModelo(grade, efetivo), [grade, efetivo]);
  const somenteLeitura = bloqueado || podeEditar !== true;

  function onChange(faseId: string, periodoId: string, texto: string) {
    const chave = `${faseId}|${periodoId}`;
    setDraft((d) => {
      const { [chave]: _antigo, ...resto } = d;
      void _antigo;
      return igualAoBase(grade, faseId, periodoId, texto) ? resto : { ...resto, [chave]: texto };
    });
    salvar.reset();
  }

  function onSalvar() {
    salvar.mutate({ alocacoes: montarAlocacoes(grade, modelo) }, { onSuccess: () => setDraft({}) });
  }

  return (
    <div className="space-y-4">
      <CronogramaToolbar
        podeEditar={podeEditar}
        bloqueadoEm={grade.cronograma.bloqueado_em}
        alterado={Object.keys(efetivo).length > 0}
        problemas={modelo.problemas}
        salvando={salvar.isPending}
        erroServidor={salvar.isError ? mensagemErro(salvar.error) : null}
        onSalvar={onSalvar}
        onDescartar={() => {
          setDraft({});
          salvar.reset();
        }}
      />
      <CronogramaGrid grade={grade} modelo={modelo} somenteLeitura={somenteLeitura} onChange={onChange} />
    </div>
  );
}

function CriarCronograma({ obraId }: { obraId: string }) {
  const criar = useCriarCronograma(obraId);
  const [periodicidade, setPeriodicidade] = useState<Periodicidade>("mensal");
  const [dataInicio, setDataInicio] = useState("");
  const [periodos, setPeriodos] = useState("");
  const router = useRouter();
  // O backend recusa (422) com a mensagem do que falta; só oferece o CTA quando é o orçamento.
  const erro = criar.error;
  const faltaOrcamento = erro instanceof ApiError && erro.status === 422 && /orçamento aprovado/i.test(erro.message);

  return (
    <form
      className="max-w-md space-y-3 rounded-xl border border-border p-4"
      onSubmit={(e) => {
        e.preventDefault();
        criar.mutate({
          periodicidade,
          data_inicio: dataInicio,
          numero_periodos: periodos === "" ? null : Number(periodos),
        });
      }}
    >
      <div className="flex items-center gap-2 text-sm font-medium">
        <CalendarRange className="size-4" aria-hidden="true" />
        Esta obra ainda não tem cronograma
      </div>
      <p className="text-sm text-muted-foreground">
        A distribuição inicial é linear ao longo dos períodos; depois você ajusta na grade.
      </p>
      <div className="space-y-1">
        <label htmlFor="cron-periodicidade" className="text-sm font-medium">
          Periodicidade
        </label>
        <select
          id="cron-periodicidade"
          value={periodicidade}
          onChange={(e) => setPeriodicidade(e.target.value as Periodicidade)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
        >
          <option value="mensal">Mensal</option>
          <option value="semanal">Semanal</option>
        </select>
      </div>
      <div className="space-y-1">
        <label htmlFor="cron-inicio" className="text-sm font-medium">
          Data de início
        </label>
        <input
          id="cron-inicio"
          type="date"
          required
          value={dataInicio}
          onChange={(e) => setDataInicio(e.target.value)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="cron-periodos" className="text-sm font-medium">
          Número de períodos (opcional)
        </label>
        <input
          id="cron-periodos"
          type="number"
          min={1}
          max={520}
          value={periodos}
          onChange={(e) => setPeriodos(e.target.value)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
        />
        <p className="text-xs text-muted-foreground">Em branco, usa a previsão de fim da obra.</p>
      </div>
      <Button type="submit" disabled={criar.isPending || dataInicio === ""}>
        {criar.isPending ? "Gerando..." : "Gerar cronograma"}
      </Button>
      {erro ? (
        <div role="alert" className="space-y-2 text-sm">
          <p className="font-medium">Não foi possível gerar o cronograma: {mensagemErro(erro)}</p>
          {faltaOrcamento ? (
            <Button type="button" variant="outline" onClick={() => router.push("/orcamentos")}>
              Ir para os orçamentos
            </Button>
          ) : null}
        </div>
      ) : null}
    </form>
  );
}
