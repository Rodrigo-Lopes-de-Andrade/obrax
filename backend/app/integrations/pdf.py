"""Renderização de HTML → PDF do orçamento (B6.3, US-17).

Ponto de extensão na mesma linha de app/integrations/notifications.py: o
serviço monta o HTML timbrado (app/modules/orcamento/pdf/template.py) e pede ao
renderer os bytes do artefato; *como* o HTML vira PDF é decidido aqui, por
ambiente.

- Dev / testes / CI: `HtmlPdfRenderer` — devolve o próprio HTML como bytes
  (content-type text/html). Não depende de headless/Chromium, então roda em
  qualquer máquina e no CI; o artefato ainda é visualizável no browser.
- Staging / prod: `PuppeteerPdfRenderer` — faz POST do HTML pro sidecar
  Puppeteer/Chromium (PDF_RENDERER_URL), que devolve o PDF binário. Seleção por
  env, sem tocar no chamador.

Seam de fila: hoje a geração é **síncrona** (o POST /pdf renderiza e sobe na
mesma request). Quando houver fila (arq) o `pdf_job` vira um job enfileirado e o
POST só o agenda — o renderer aqui não muda. Mesmo padrão sync-com-TODO de
notifications.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import settings

# Timeout do sidecar: geração de PDF com Chromium pode levar alguns segundos
# num orçamento grande; folga sobre o default (5s) do httpx sem travar a request.
_RENDER_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class RenderedPdf:
    """Artefato renderizado. `extension`/`content_type` variam por renderer
    (html em dev, pdf em prod) — o chamador usa ambos ao montar a chave do
    storage e ao assinar o download."""

    body: bytes
    content_type: str
    extension: str


class PdfRenderer(Protocol):
    """Contrato mínimo: HTML timbrado entra, bytes do artefato saem."""

    def render(self, *, html: str) -> RenderedPdf: ...


class HtmlPdfRenderer:
    """Dev/testes: não converte — devolve o HTML como bytes. O artefato abre no
    browser e casa com os testes do template (B6.4) sem exigir headless."""

    def render(self, *, html: str) -> RenderedPdf:
        return RenderedPdf(
            body=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            extension="html",
        )


class PuppeteerPdfRenderer:
    """Prod: delega a conversão HTML→PDF a um sidecar Puppeteer/Chromium via
    HTTP (mesma ideia do storage: infra pesada fora do processo da API)."""

    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def render(self, *, html: str) -> RenderedPdf:
        resp = httpx.post(
            f"{self._base_url}/render",
            content=html.encode("utf-8"),
            headers={"Content-Type": "text/html; charset=utf-8"},
            timeout=_RENDER_TIMEOUT_S,
        )
        resp.raise_for_status()
        return RenderedPdf(
            body=resp.content,
            content_type="application/pdf",
            extension="pdf",
        )


@lru_cache
def _pdf_renderer() -> PdfRenderer:
    if settings.pdf_renderer_url:
        return PuppeteerPdfRenderer(base_url=settings.pdf_renderer_url)
    return HtmlPdfRenderer()


def get_pdf_renderer() -> PdfRenderer:
    """Dependency FastAPI: renderer singleton conforme ambiente.
    Sobrescreva com `app.dependency_overrides` nos testes."""
    return _pdf_renderer()
