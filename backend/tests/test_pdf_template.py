"""B6.4 — template HTML do PDF do orçamento: estrutura, formatação pt-BR e
escaping. Puro (sem banco/headless), só verifica o HTML gerado.
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.orcamento.pdf.template import (
    OrcamentoPdfContext,
    PdfAbcClasse,
    PdfEmpresa,
    PdfFaseResumo,
    PdfLinhaEap,
    render_orcamento_html,
)


def _ctx(**over: object) -> OrcamentoPdfContext:
    base: dict[str, object] = dict(
        empresa=PdfEmpresa(nome="Construtora Alfa"),
        cliente_nome="Cliente Beta LTDA",
        cliente_documento="11.222.333/0001-81",
        obra_codigo="OBR-1",
        obra_nome="Residencial Jardim",
        titulo="Orçamento base",
        revisao=2,
        status="aguardando_aprovacao",
        emitido_em="09/07/2026",
        custo_direto=Decimal("1650.00"),
        markup_global=Decimal("0.2000"),
        taxa_adm=Decimal("0.0500"),
        preco_venda=Decimal("2115.75"),
        margem=Decimal("0.2201"),
        linhas=[
            PdfLinhaEap(
                "F", 0, None, "Fundações", None, Decimal("0"), Decimal("0"), Decimal("1575.00")
            ),
            PdfLinhaEap(
                "S", 1, None, "Sapatas", None, Decimal("0"), Decimal("0"), Decimal("1575.00")
            ),
            PdfLinhaEap(
                "I",
                2,
                "SINAPI-01",
                "Concreto usinado",
                "m³",
                Decimal("10"),
                Decimal("100.00"),
                Decimal("1200.00"),
            ),
        ],
        fases=[
            PdfFaseResumo(
                "Fundações",
                Decimal("1250.00"),
                Decimal("0.2000"),
                Decimal("1575.00"),
                Decimal("0.74"),
            )
        ],
        abc=[
            PdfAbcClasse("A", 1, Decimal("1200.00"), Decimal("0.8000")),
            PdfAbcClasse("B", 1, Decimal("250.00"), Decimal("0.1500")),
            PdfAbcClasse("C", 1, Decimal("200.00"), Decimal("0.0500")),
        ],
    )
    base.update(over)
    return OrcamentoPdfContext(**base)  # type: ignore[arg-type]


def test_documento_html_completo() -> None:
    html_out = render_orcamento_html(_ctx())
    assert html_out.startswith("<!DOCTYPE html>")
    assert "@page" in html_out and "size: A4" in html_out
    # Cabeçalho / partes
    assert "Construtora Alfa" in html_out
    assert "Cliente Beta LTDA" in html_out
    assert "Residencial Jardim" in html_out
    assert "Rev. 2" in html_out
    assert "Aguardando aprovação" in html_out
    # EAP
    assert "Concreto usinado" in html_out
    assert "SINAPI-01" in html_out


def test_formatacao_ptbr() -> None:
    html_out = render_orcamento_html(_ctx())
    assert "R$ 2.115,75" in html_out  # preço de venda com milhar
    assert "R$ 1.650,00" in html_out  # custo direto
    assert "20,00%" in html_out  # markup global
    assert "22,01%" in html_out  # margem


def test_logo_placeholder_iniciais() -> None:
    html_out = render_orcamento_html(_ctx(empresa=PdfEmpresa(nome="Alfa Beta")))
    assert "logo-ph" in html_out
    assert ">AB<" in html_out  # iniciais das duas primeiras palavras


def test_escaping_previne_injecao() -> None:
    html_out = render_orcamento_html(_ctx(cliente_nome="<script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;" in html_out


def test_curva_abc_vazia_nao_quebra() -> None:
    html_out = render_orcamento_html(_ctx(abc=[], fases=[]))
    assert "Sem itens classificados." in html_out
    assert "Resumo por fase" not in html_out  # seção some quando não há fases
