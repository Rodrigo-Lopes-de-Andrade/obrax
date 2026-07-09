"""Gerador do catálogo SINAPI (stand-in determinístico).

Premissa declarada: o dataset SINAPI real (~10k composições, publicado pela
Caixa/IBGE) não está disponível neste ambiente. Este gerador produz um catálogo
sintético porém realista (categorias, unidades e descrições de construção civil
brasileira, com preços plausíveis) para exercitar busca/autocomplete e o
importador. Em staging o seed real substitui esta fonte — o schema de `insumo` e
a API de busca não mudam. Ver docs/SPRINTS.md D5.2 / B5.6.

`gerar_catalogo(n)` é puro e determinístico (mesmo n → mesmas linhas), para que
o seed seja idempotente e os testes reproduzíveis.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from decimal import Decimal
from typing import NamedTuple


class InsumoSeed(NamedTuple):
    codigo: str
    descricao: str
    unidade: str
    categoria: str
    preco_unitario: Decimal


# (categoria, base, unidade, faixa de preço base R$)
_BASES: list[tuple[str, str, str, tuple[float, float]]] = [
    ("Movimentação de Terra", "Escavação manual em solo", "m³", (35, 90)),
    ("Movimentação de Terra", "Escavação mecânica", "m³", (12, 40)),
    ("Movimentação de Terra", "Aterro compactado", "m³", (25, 70)),
    ("Fundações", "Estaca escavada", "m", (60, 180)),
    ("Fundações", "Sapata de concreto armado", "m³", (700, 1400)),
    ("Fundações", "Viga baldrame", "m", (90, 220)),
    ("Concreto e Formas", "Concreto usinado fck 25MPa", "m³", (380, 620)),
    ("Concreto e Formas", "Fôrma de madeira", "m²", (45, 110)),
    ("Concreto e Formas", "Armadura de aço CA-50", "kg", (8, 16)),
    ("Concreto e Formas", "Laje pré-moldada", "m²", (70, 160)),
    ("Alvenaria", "Alvenaria de bloco cerâmico", "m²", (55, 120)),
    ("Alvenaria", "Alvenaria de bloco de concreto", "m²", (60, 130)),
    ("Alvenaria", "Verga e contraverga", "m", (25, 60)),
    ("Revestimentos", "Chapisco", "m²", (8, 20)),
    ("Revestimentos", "Emboço", "m²", (25, 55)),
    ("Revestimentos", "Revestimento cerâmico", "m²", (45, 130)),
    ("Revestimentos", "Porcelanato retificado", "m²", (80, 220)),
    ("Cobertura", "Telha cerâmica", "m²", (45, 110)),
    ("Cobertura", "Telha de fibrocimento", "m²", (35, 80)),
    ("Cobertura", "Estrutura de madeira para telhado", "m²", (60, 150)),
    ("Instalações Elétricas", "Ponto de tomada", "un", (55, 140)),
    ("Instalações Elétricas", "Ponto de iluminação", "un", (60, 150)),
    ("Instalações Elétricas", "Cabo flexível 2,5mm²", "m", (2, 6)),
    ("Instalações Elétricas", "Quadro de distribuição", "un", (180, 700)),
    ("Instalações Elétricas", "Eletroduto corrugado", "m", (3, 9)),
    ("Instalações Hidráulicas", "Ponto de água fria", "un", (90, 220)),
    ("Instalações Hidráulicas", "Ponto de esgoto", "un", (110, 260)),
    ("Instalações Hidráulicas", "Tubo PVC soldável", "m", (8, 28)),
    ("Instalações Hidráulicas", "Registro de gaveta", "un", (45, 130)),
    ("Instalações Hidráulicas", "Reservatório de água", "un", (400, 1600)),
    ("Esquadrias", "Porta de madeira", "un", (280, 900)),
    ("Esquadrias", "Janela de alumínio", "m²", (350, 900)),
    ("Esquadrias", "Porta de vidro temperado", "m²", (500, 1200)),
    ("Pintura", "Massa corrida PVA", "m²", (10, 28)),
    ("Pintura", "Pintura látex acrílica", "m²", (18, 45)),
    ("Pintura", "Pintura esmalte sintético", "m²", (22, 55)),
    ("Impermeabilização", "Manta asfáltica", "m²", (55, 130)),
    ("Impermeabilização", "Cimento polimérico", "m²", (30, 75)),
    ("Louças e Metais", "Bacia sanitária com caixa acoplada", "un", (350, 1100)),
    ("Louças e Metais", "Lavatório de louça", "un", (180, 600)),
    ("Louças e Metais", "Torneira de mesa", "un", (80, 400)),
    ("Louças e Metais", "Chuveiro elétrico", "un", (120, 500)),
]

_VARIANTES = [
    "fornecimento e instalação",
    "somente material",
    "somente mão de obra",
    "padrão popular",
    "padrão médio",
    "padrão alto",
    "com preparo de superfície",
    "reforçado",
    "acabamento fino",
    "execução conforme projeto",
]
_MARCAS = [
    "Tigre",
    "Amanco",
    "Deca",
    "Tramontina",
    "Votorantim",
    "Gerdau",
    "Eliane",
    "Portobello",
    "Suvinil",
    "genérico",
    "importado",
]
_DIMENSOES = [
    "",
    '1/2"',
    '3/4"',
    '1"',
    "DN50",
    "DN100",
    "6mm",
    "8mm",
    "10mm",
    "e=15cm",
]


def gerar_catalogo(n: int = 10_000) -> Iterator[InsumoSeed]:
    """Gera até `n` insumos únicos (código sequencial SINAPI-000001…). Preços
    determinísticos por semente fixa."""
    rng = random.Random(20260709)
    contador = 0
    for size in _DIMENSOES:
        for marca in _MARCAS:
            for variante in _VARIANTES:
                for categoria, base, unidade, (lo, hi) in _BASES:
                    if contador >= n:
                        return
                    contador += 1
                    sufixo_dim = f" {size}" if size else ""
                    descricao = f"{base}{sufixo_dim} - {variante} ({marca})"
                    preco = Decimal(str(round(rng.uniform(lo, hi), 4)))
                    yield InsumoSeed(
                        codigo=f"SINAPI-{contador:06d}",
                        descricao=descricao,
                        unidade=unidade,
                        categoria=categoria,
                        preco_unitario=preco,
                    )
