"""B6.4 — Template HTML/CSS do orçamento (PDF timbrado, US-17).

`render_orcamento_html` recebe um contexto tipado (montado a partir do banco em
B6.3) e devolve um documento HTML completo, pronto para o Puppeteer sidecar
converter em PDF (docs/CLAUDE.md › PDF). O template é puro (sem I/O): assim ele
é testável sem banco nem headless browser.

Layout A4, impressão-first (fundo claro, texto escuro), com cabeçalho da
construtora (logo customizável — S1 prep), dados de cliente/obra, a tabela da
EAP (Fase › Serviço › Insumo), resumo de precificação, curva ABC e área de
assinatura. **Valores em Decimal formatados em pt-BR — nunca float.**
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class PdfEmpresa:
    nome: str
    # Data URI (ex.: "data:image/png;base64,...") do logo, ou None → placeholder
    # com as iniciais. O logo por construtora é customizável (S1 prep).
    logo_data_uri: str | None = None


@dataclass(frozen=True)
class PdfLinhaEap:
    tipo: str  # F / S / I
    depth: int
    codigo: str | None
    descricao: str
    unidade: str | None
    quantidade: Decimal
    preco_unitario: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class PdfFaseResumo:
    descricao: str
    custo: Decimal
    markup: Decimal
    subtotal: Decimal
    pct: Decimal  # participação no preço de venda


@dataclass(frozen=True)
class PdfAbcClasse:
    classe: str  # A / B / C
    count: int
    custo: Decimal
    pct: Decimal


@dataclass(frozen=True)
class OrcamentoPdfContext:
    empresa: PdfEmpresa
    cliente_nome: str
    cliente_documento: str | None
    obra_codigo: str
    obra_nome: str
    titulo: str
    revisao: int
    status: str
    emitido_em: str  # já formatado (dd/mm/aaaa) pelo chamador
    custo_direto: Decimal
    markup_global: Decimal
    taxa_adm: Decimal
    preco_venda: Decimal
    margem: Decimal
    linhas: list[PdfLinhaEap] = field(default_factory=list)
    fases: list[PdfFaseResumo] = field(default_factory=list)
    abc: list[PdfAbcClasse] = field(default_factory=list)


_STATUS_LABEL = {
    "rascunho": "Rascunho",
    "em_revisao": "Em revisão",
    "aguardando_aprovacao": "Aguardando aprovação",
    "aprovado": "Aprovado",
    "rejeitado": "Rejeitado",
}

_CLASSE_COR = {"A": "#dc2626", "B": "#d97706", "C": "#059669"}


# --------------------------------------------------------------------------- #
# Formatação pt-BR (Decimal → string; proibido float)
# --------------------------------------------------------------------------- #
def _brl(valor: Decimal) -> str:
    q = valor.quantize(_CENT, ROUND_HALF_UP)
    inteiro, _, dec = f"{q:.2f}".partition(".")
    negativo = inteiro.startswith("-")
    inteiro = inteiro.lstrip("-")
    grupos: list[str] = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return f"{'-' if negativo else ''}R$ {'.'.join(grupos)},{dec}"


def _pct(valor: Decimal) -> str:
    p = (valor * 100).quantize(_CENT, ROUND_HALF_UP)
    return f"{p:.2f}".replace(".", ",") + "%"


def _qtd(valor: Decimal) -> str:
    s = f"{valor.normalize():f}"
    return s.replace(".", ",")


def _e(texto: str | None) -> str:
    return html.escape(texto) if texto else ""


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def render_orcamento_html(ctx: OrcamentoPdfContext) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<title>{_e(ctx.titulo)} — {_e(ctx.obra_codigo)}</title>
<style>{_CSS}</style>
</head>
<body>
  <header class="doc-head">
    <div class="brand">
      {_logo(ctx.empresa)}
      <div class="brand-name">{_e(ctx.empresa.nome)}</div>
    </div>
    <div class="doc-meta">
      <div class="doc-title">Orçamento</div>
      <div class="doc-sub">{_e(ctx.titulo)}</div>
      <div class="doc-tags">
        <span class="tag">Rev. {ctx.revisao}</span>
        <span class="tag">{_e(_STATUS_LABEL.get(ctx.status, ctx.status))}</span>
      </div>
      <div class="doc-date">Emitido em {_e(ctx.emitido_em)}</div>
    </div>
  </header>

  <section class="parties">
    <div class="party">
      <div class="party-label">Cliente</div>
      <div class="party-name">{_e(ctx.cliente_nome)}</div>
      {f'<div class="party-doc">{_e(ctx.cliente_documento)}</div>' if ctx.cliente_documento else ""}
    </div>
    <div class="party">
      <div class="party-label">Obra</div>
      <div class="party-name">{_e(ctx.obra_nome)}</div>
      <div class="party-doc">{_e(ctx.obra_codigo)}</div>
    </div>
  </section>

  <section>
    <h2 class="sec-title">Estrutura Analítica do Projeto</h2>
    <table class="eap">
      <thead>
        <tr>
          <th class="c-desc">Descrição</th>
          <th class="c-un">Un.</th>
          <th class="c-num">Qtd.</th>
          <th class="c-num">Preço unit.</th>
          <th class="c-num">Subtotal</th>
        </tr>
      </thead>
      <tbody>
        {_linhas(ctx.linhas) if ctx.linhas else '<tr><td colspan="5" class="empty">Sem itens.</td></tr>'}
      </tbody>
    </table>
  </section>

  <section class="grid-2">
    <div class="box">
      <h2 class="sec-title">Resumo</h2>
      <table class="kv">
        <tr><td>Custo direto</td><td class="c-num">{_brl(ctx.custo_direto)}</td></tr>
        <tr><td>Markup global</td><td class="c-num">{_pct(ctx.markup_global)}</td></tr>
        <tr><td>Taxa de administração</td><td class="c-num">{_pct(ctx.taxa_adm)}</td></tr>
        <tr><td>Margem</td><td class="c-num">{_pct(ctx.margem)}</td></tr>
        <tr class="total"><td>Preço de venda</td><td class="c-num">{_brl(ctx.preco_venda)}</td></tr>
      </table>
    </div>
    <div class="box">
      <h2 class="sec-title">Curva ABC</h2>
      {_abc(ctx.abc)}
    </div>
  </section>

  {_fases_section(ctx.fases)}

  <section class="signature">
    <div class="sig-line">
      <span>{_e(ctx.empresa.nome)}</span>
    </div>
    <div class="sig-line">
      <span>{_e(ctx.cliente_nome)}</span>
    </div>
  </section>

  <footer class="doc-foot">
    Documento gerado por Obrax · {_e(ctx.obra_codigo)} · Rev. {ctx.revisao}
  </footer>
</body>
</html>"""


def _logo(empresa: PdfEmpresa) -> str:
    if empresa.logo_data_uri:
        return f'<img class="logo" src="{html.escape(empresa.logo_data_uri, quote=True)}" alt="logo" />'
    iniciais = "".join(p[0] for p in empresa.nome.split()[:2]).upper() or "?"
    return f'<div class="logo logo-ph">{_e(iniciais)}</div>'


def _linhas(linhas: list[PdfLinhaEap]) -> str:
    out: list[str] = []
    for ln in linhas:
        cls = {"F": "row-f", "S": "row-s", "I": "row-i"}.get(ln.tipo, "row-i")
        indent = ln.depth * 16
        codigo = f'<span class="cod">{_e(ln.codigo)}</span> ' if ln.codigo else ""
        folha = ln.tipo == "I"
        out.append(
            f'<tr class="{cls}">'
            f'<td class="c-desc" style="padding-left:{8 + indent}px">{codigo}{_e(ln.descricao)}</td>'
            f'<td class="c-un">{_e(ln.unidade) if folha else ""}</td>'
            f'<td class="c-num">{_qtd(ln.quantidade) if folha else ""}</td>'
            f'<td class="c-num">{_brl(ln.preco_unitario) if folha else ""}</td>'
            f'<td class="c-num">{_brl(ln.subtotal)}</td>'
            f"</tr>"
        )
    return "\n".join(out)


def _abc(classes: list[PdfAbcClasse]) -> str:
    if not classes or all(c.count == 0 for c in classes):
        return '<p class="empty">Sem itens classificados.</p>'
    linhas = "\n".join(
        f'<tr><td><span class="dot" style="background:{_CLASSE_COR.get(c.classe, "#666")}"></span>'
        f"Classe {_e(c.classe)}</td>"
        f'<td class="c-num">{c.count}</td>'
        f'<td class="c-num">{_brl(c.custo)}</td>'
        f'<td class="c-num">{_pct(c.pct)}</td></tr>'
        for c in classes
    )
    return (
        '<table class="kv abc"><thead><tr><th>Classe</th><th class="c-num">Itens</th>'
        '<th class="c-num">Custo</th><th class="c-num">% do custo</th></tr></thead>'
        f"<tbody>{linhas}</tbody></table>"
    )


def _fases_section(fases: list[PdfFaseResumo]) -> str:
    if not fases:
        return ""
    linhas = "\n".join(
        f"<tr><td>{_e(f.descricao)}</td>"
        f'<td class="c-num">{_brl(f.custo)}</td>'
        f'<td class="c-num">{_pct(f.markup)}</td>'
        f'<td class="c-num">{_brl(f.subtotal)}</td>'
        f'<td class="c-num">{_pct(f.pct)}</td></tr>'
        for f in fases
    )
    return (
        '<section><h2 class="sec-title">Resumo por fase</h2>'
        '<table class="eap"><thead><tr><th class="c-desc">Fase</th>'
        '<th class="c-num">Custo</th><th class="c-num">Markup</th>'
        '<th class="c-num">Subtotal</th><th class="c-num">% do total</th></tr></thead>'
        f"<tbody>{linhas}</tbody></table></section>"
    )


_CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1e293b; font-size: 11px; line-height: 1.45; margin: 0; }
.doc-head { display: flex; justify-content: space-between; align-items: flex-start;
  border-bottom: 2px solid #4f46e5; padding-bottom: 12px; margin-bottom: 16px; }
.brand { display: flex; align-items: center; gap: 12px; }
.logo { width: 52px; height: 52px; border-radius: 8px; object-fit: contain; }
.logo-ph { background: #4f46e5; color: #fff; display: flex; align-items: center;
  justify-content: center; font-weight: 700; font-size: 18px; }
.brand-name { font-size: 15px; font-weight: 700; }
.doc-meta { text-align: right; }
.doc-title { font-size: 20px; font-weight: 700; color: #4f46e5; letter-spacing: .5px; }
.doc-sub { font-weight: 600; }
.doc-tags { margin: 4px 0; }
.tag { display: inline-block; background: #eef2ff; color: #4338ca; border-radius: 4px;
  padding: 1px 6px; font-size: 10px; font-weight: 600; margin-left: 4px; }
.doc-date { color: #64748b; font-size: 10px; }
.parties { display: flex; gap: 16px; margin-bottom: 18px; }
.party { flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; }
.party-label { text-transform: uppercase; font-size: 9px; letter-spacing: .6px; color: #64748b; }
.party-name { font-weight: 600; font-size: 12px; }
.party-doc { color: #64748b; }
.sec-title { font-size: 12px; font-weight: 700; color: #334155; margin: 0 0 8px;
  text-transform: uppercase; letter-spacing: .4px; }
table { width: 100%; border-collapse: collapse; }
.eap th { text-align: left; background: #f1f5f9; color: #475569; font-size: 9px;
  text-transform: uppercase; letter-spacing: .4px; padding: 6px 8px; border-bottom: 1px solid #cbd5e1; }
.eap td { padding: 5px 8px; border-bottom: 1px solid #eef2f7; }
.c-num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.c-un { text-align: center; color: #64748b; }
.row-f td { background: #eef2ff; font-weight: 700; }
.row-s td { background: #f8fafc; font-weight: 600; }
.cod { display: inline-block; background: #e2e8f0; color: #475569; border-radius: 3px;
  padding: 0 4px; font-size: 9px; margin-right: 4px; }
.empty { color: #94a3b8; text-align: center; padding: 12px; }
.grid-2 { display: flex; gap: 16px; margin: 18px 0; }
.grid-2 .box { flex: 1; }
.kv td { padding: 4px 2px; border-bottom: 1px solid #eef2f7; }
.kv .total td { border-top: 2px solid #4f46e5; border-bottom: none; font-weight: 700;
  font-size: 13px; color: #4f46e5; padding-top: 6px; }
.abc th { font-size: 9px; text-transform: uppercase; color: #64748b; text-align: left;
  padding: 4px 2px; border-bottom: 1px solid #cbd5e1; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.signature { display: flex; gap: 48px; margin-top: 48px; }
.sig-line { flex: 1; border-top: 1px solid #334155; padding-top: 6px; text-align: center;
  color: #475569; font-weight: 600; }
.doc-foot { margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 8px;
  color: #94a3b8; font-size: 9px; text-align: center; }
"""
