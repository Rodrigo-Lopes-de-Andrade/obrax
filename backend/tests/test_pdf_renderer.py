"""Renderers HTML→PDF (app/integrations/pdf.py).

Regressão: em produção não havia sidecar (PDF_RENDERER_URL vazia), então caía
no HtmlPdfRenderer e o "Gerar PDF" entregava HTML cru. Agora PDF_ENGINE=weasyprint
gera o PDF in-process.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.integrations import pdf
from app.modules.orcamento.pdf.template import render_orcamento_html
from tests.test_pdf_template import _ctx


def _weasyprint_disponivel() -> bool:
    try:
        import weasyprint  # noqa: F401
    except OSError:  # libs de sistema (Pango) ausentes nesta máquina
        return False
    return True


@pytest.mark.skipif(not _weasyprint_disponivel(), reason="Pango/WeasyPrint indisponível")
def test_weasyprint_gera_pdf_do_template_do_orcamento() -> None:
    out = pdf.WeasyPrintPdfRenderer().render(html=render_orcamento_html(_ctx()))
    assert out.body.startswith(b"%PDF-")
    assert out.content_type == "application/pdf"
    assert out.extension == "pdf"


@pytest.mark.parametrize(
    ("url", "engine", "esperado"),
    [
        ("", "html", pdf.HtmlPdfRenderer),
        ("", "weasyprint", pdf.WeasyPrintPdfRenderer),
        ("http://sidecar:3000", "weasyprint", pdf.PuppeteerPdfRenderer),
    ],
)
def test_selecao_do_renderer_por_env(
    monkeypatch: pytest.MonkeyPatch, url: str, engine: str, esperado: type
) -> None:
    fake = dataclasses.replace(pdf.settings, pdf_renderer_url=url, pdf_engine=engine)
    monkeypatch.setattr(pdf, "settings", fake)
    pdf._pdf_renderer.cache_clear()
    try:
        assert isinstance(pdf._pdf_renderer(), esperado)
    finally:
        pdf._pdf_renderer.cache_clear()
