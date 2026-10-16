"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Building2, Loader2, Search, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { listClientes } from "@/lib/api/clientes";
import { useObras } from "@/lib/hooks/use-obras";
import { useOnClickOutside } from "@/lib/hooks/use-on-click-outside";
import { formatDocumento } from "@/components/modules/cliente/documento";
import { cn } from "@/lib/utils";

interface Resultado {
  key: string;
  href: string;
  titulo: string;
  detalhe: string;
  tipo: "obra" | "cliente";
}

const MAX_POR_TIPO = 5;

/** Busca da Topbar: clientes pelo `?search=` do backend; obras filtradas no
 * client (o GET /obras não tem busca textual) sobre as 100 mais recentes. */
export function GlobalSearch() {
  const router = useRouter();
  const [input, setInput] = React.useState("");
  const [termo, setTermo] = React.useState("");
  const [aberto, setAberto] = React.useState(false);
  const [ativo, setAtivo] = React.useState(0);
  const ref = React.useRef<HTMLDivElement>(null);
  useOnClickOutside(ref, () => setAberto(false));

  React.useEffect(() => {
    const t = setTimeout(() => setTermo(input.trim()), 250);
    return () => clearTimeout(t);
  }, [input]);

  const buscando = termo.length >= 2;
  const clientesQ = useQuery({
    queryKey: ["clientes", "list", { search: termo, limit: MAX_POR_TIPO }],
    queryFn: () => listClientes({ search: termo, limit: MAX_POR_TIPO }),
    enabled: buscando,
  });
  // Só carrega a lista de obras depois que o usuário interage com a busca.
  const obrasQ = useObras({ limit: 100 }, { enabled: aberto || buscando });

  const resultados = React.useMemo<Resultado[]>(() => {
    if (!buscando) return [];
    const t = termo.toLowerCase();
    const obras = (obrasQ.data?.items ?? [])
      .filter((o) => o.nome.toLowerCase().includes(t) || o.codigo.toLowerCase().includes(t))
      .slice(0, MAX_POR_TIPO)
      .map<Resultado>((o) => ({
        key: `obra-${o.id}`,
        href: `/obras/${o.id}/documentos`,
        titulo: o.nome,
        detalhe: o.codigo,
        tipo: "obra",
      }));
    const clientes = (clientesQ.data?.items ?? []).map<Resultado>((c) => ({
      key: `cliente-${c.id}`,
      href: `/clientes?q=${encodeURIComponent(c.nome)}`,
      titulo: c.nome,
      detalhe: formatDocumento(c.documento),
      tipo: "cliente",
    }));
    return [...obras, ...clientes];
  }, [buscando, termo, obrasQ.data, clientesQ.data]);

  React.useEffect(() => setAtivo(0), [termo]);

  const carregando = buscando && (clientesQ.isFetching || obrasQ.isFetching);

  function ir(r: Resultado) {
    setAberto(false);
    setInput("");
    router.push(r.href);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      setAberto(false);
      return;
    }
    if (!resultados.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setAtivo((i) => (i + 1) % resultados.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setAtivo((i) => (i - 1 + resultados.length) % resultados.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      ir(resultados[ativo]);
    }
  }

  return (
    <div className="relative max-w-110 flex-1" ref={ref}>
      <Search className="absolute top-1/2 left-3.5 h-4.5 w-4.5 -translate-y-1/2 text-muted-foreground/70" />
      <input
        type="search"
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          setAberto(true);
        }}
        onFocus={() => setAberto(true)}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-expanded={aberto && buscando}
        aria-controls="busca-global-resultados"
        aria-label="Buscar obras e clientes"
        placeholder="Buscar obras e clientes…"
        className="w-full rounded-lg border border-white/6 bg-muted py-2.5 pr-9 pl-10 text-[13.5px] outline-none placeholder:text-muted-foreground/70 focus:border-white/15"
      />
      {carregando && (
        <Loader2 className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
      )}

      {aberto && buscando && (
        <div
          id="busca-global-resultados"
          role="listbox"
          className="absolute top-12 right-0 left-0 z-40 overflow-hidden rounded-[10px] border border-white/8 bg-popover py-1.5 shadow-[0_20px_60px_rgba(0,0,0,0.6)]"
        >
          {resultados.length === 0 ? (
            <p className="px-4 py-3 text-sm text-muted-foreground">
              {carregando ? "Buscando…" : `Nada encontrado para “${termo}”.`}
            </p>
          ) : (
            resultados.map((r, i) => {
              const Icon = r.tipo === "obra" ? Building2 : Users;
              return (
                <Link
                  key={r.key}
                  href={r.href}
                  role="option"
                  aria-selected={i === ativo}
                  onMouseEnter={() => setAtivo(i)}
                  onClick={(e) => {
                    e.preventDefault();
                    ir(r);
                  }}
                  className={cn(
                    "flex items-center gap-3 px-4 py-2 text-sm",
                    i === ativo ? "bg-white/6" : "hover:bg-white/4",
                  )}
                >
                  <Icon className="size-4 flex-shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1 truncate font-medium">{r.titulo}</span>
                  <span className="flex-shrink-0 text-xs text-muted-foreground tabular-nums">
                    {r.tipo === "obra" ? "Obra" : "Cliente"} · {r.detalhe}
                  </span>
                </Link>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
