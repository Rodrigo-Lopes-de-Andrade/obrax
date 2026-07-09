"""D5.2 — seed do catálogo SINAPI global (company_id NULL).

Insere ~10k insumos em lote via role `obrax` (bypassa RLS; global é público).
Idempotente: ON CONFLICT no código global não faz nada, então rodar de novo é
seguro.

Uso:
    cd backend && uv run python -m scripts.seed_sinapi          # 10.000
    cd backend && uv run python -m scripts.seed_sinapi 2000     # quantidade custom
"""

from __future__ import annotations

import sys

from sqlalchemy import text

from app.core.db import SessionLocal
from app.modules.orcamento.catalog_sinapi import gerar_catalogo

_INSERT = text(
    "INSERT INTO insumo (company_id, codigo, descricao, unidade, categoria, preco_unitario) "
    "VALUES (NULL, :codigo, :descricao, :unidade, :categoria, :preco_unitario) "
    "ON CONFLICT (codigo) WHERE company_id IS NULL DO NOTHING"
)


def seed(n: int = 10_000, batch: int = 1000) -> int:
    total = 0
    with SessionLocal() as session:
        lote: list[dict[str, object]] = []
        for insumo in gerar_catalogo(n):
            lote.append(insumo._asdict())
            if len(lote) >= batch:
                session.execute(_INSERT, lote)
                total += len(lote)
                lote = []
        if lote:
            session.execute(_INSERT, lote)
            total += len(lote)
        session.commit()
    return total


if __name__ == "__main__":
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    inseridos = seed(quantidade)
    print(f"seed SINAPI: {inseridos} insumos processados")
