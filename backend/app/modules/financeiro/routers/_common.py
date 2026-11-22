"""Papéis (ESPEC §9) e helpers comuns dos routers do financeiro.

`campo`, `viewer` e `ai` nunca têm acesso. A dependência de papel roda antes do
corpo e da validação do body: quem não tem o papel recebe 403, não 422/501.
"""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import Depends, HTTPException, status

from app.core.deps import require_roles

# Escrita/pagamento/planejamento: tudo exceto aprovar medição.
ROLES_GERENCIA = ("owner", "admin", "financeiro")
# Aprovar medição é ato comercial com o cliente.
ROLES_APROVAR = ("owner", "admin")
# Leitura de tudo + gestor cria/edita despesa (não paga).
ROLES_LEITURA = ("owner", "admin", "financeiro", "gestor")
ROLES_DESPESA_ESCRITA = ("owner", "admin", "financeiro", "gestor")
# Orçado x realizado e Curva S também abrem para orçamentista.
ROLES_ANALISE = ("owner", "admin", "financeiro", "gestor", "orcamentista")

GERENCIA = Depends(require_roles(*ROLES_GERENCIA))
APROVAR = Depends(require_roles(*ROLES_APROVAR))
LEITURA = Depends(require_roles(*ROLES_LEITURA))
DESPESA_ESCRITA = Depends(require_roles(*ROLES_DESPESA_ESCRITA))
ANALISE = Depends(require_roles(*ROLES_ANALISE))

RESP_501: dict[int | str, dict[str, Any]] = {
    501: {"description": "Não implementado (stub de contrato da S-F2); corpo RFC 7807."}
}


def nao_implementado() -> NoReturn:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "não implementado")
