"""Seed de dados de demonstração (D11.1) — uma construtora fictícia com dados
realistas para demo/onboarding de beta: clientes, obras, orçamentos, documentos
e chamados.

Diferente de `seed_demo.py` (2 empresas mínimas para exercitar RLS), este popula
UMA empresa com volume realista:
  - 1 empresa + 1 usuário owner que **consegue logar** (hash Argon2id real);
  - 7 clientes (PF/PJ, CPF/CNPJ válidos);
  - 10 obras (status variados);
  - 5 orçamentos (com versão + itens EAP);
  - 50 documentos (tipos variados, parte visível ao cliente);
  - chamados com mensagens.

Roda via `SessionLocal` (conexão `postgres`/`obrax` — BYPASSRLS), então insere
para qualquer `company_id`. É **idempotente**: se a empresa demo já tem obras,
não faz nada.

Uso:
    cd backend && uv run python -m scripts.seed_demo_data
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.security import hash_password

# --- Empresa e usuário demo ----------------------------------------------------
DEMO_CNPJ = "19131243000197"  # CNPJ válido (dígitos verificadores corretos)
DEMO_COMPANY = "Construtora Obrax Demo Ltda"
DEMO_USER_EMAIL = "demo@obrax.com.br"
DEMO_USER_NOME = "Marina Alves"
DEMO_USER_SENHA = "obraxdemo123"  # senha do usuário demo (login real)


# --- Geração de CPF/CNPJ válidos (mod-11) --------------------------------------
def _dv(nums: str) -> str:
    """Dígito verificador mod-11 de CPF (pesos len+1..2)."""
    w = len(nums) + 1
    s = sum(int(d) * (w - i) for i, d in enumerate(nums))
    r = s % 11
    return "0" if r < 2 else str(11 - r)


def cpf(base9: str) -> str:
    d1 = _dv(base9)
    return base9 + d1 + _dv(base9 + d1)


def _cnpj_dv(nums: str, weights: list[int]) -> str:
    s = sum(int(d) * w for d, w in zip(nums, weights, strict=False))
    r = s % 11
    return "0" if r < 2 else str(11 - r)


def cnpj(base12: str) -> str:
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _cnpj_dv(base12, w1)
    return base12 + d1 + _cnpj_dv(base12 + d1, w2)


# --- Dados fixos ---------------------------------------------------------------
# tipo_pessoa é 'PF'/'PJ' (bpchar) — bate com ck_clientes_tipo_pessoa e com
# fn_validate_documento no Postgres (que roteia CPF vs CNPJ por esse valor).
CLIENTES = [
    ("PF", cpf("111444777"), "João Pereira", "(11) 98888-1010", "joao.pereira@example.com"),
    ("PF", cpf("222555888"), "Ana Souza", "(11) 97777-2020", "ana.souza@example.com"),
    ("PF", cpf("333666999"), "Carlos Menezes", "(21) 96666-3030", "carlos.menezes@example.com"),
    ("PF", cpf("529982247"), "Beatriz Lima", "(31) 95555-4040", "beatriz.lima@example.com"),
    ("PJ", cnpj("112223330001"), "Incorporadora Aurora S.A.", "(11) 3030-5050", "contato@aurora.example.com"),
    ("PJ", cnpj("445556660001"), "Shopping Vale Empreendimentos", "(11) 3040-6060", "obras@vale.example.com"),
    ("PJ", cnpj("778889990001"), "Condomínio Parque Verde", "(41) 3050-7070", "sindico@parqueverde.example.com"),
]

OBRA_STATUS = ["execucao", "execucao", "execucao", "planejamento", "pausada",
               "concluida", "execucao", "planejamento", "concluida", "execucao"]
OBRA_NOMES = [
    "Residencial Vila Aurora", "Reforma Comercial Centro", "Edifício Solar das Águas",
    "Casa Alto Padrão Alphaville", "Galpão Logístico Km 32", "Retrofit Edifício Beta",
    "Condomínio Parque Verde — Bloco A", "Escola Municipal Jardim", "Clínica Vida — Ampliação",
    "Praça Central — Requalificação",
]
DOC_TIPOS = ["projeto", "contrato", "nota_fiscal", "foto", "outro"]
DOC_NOMES = {
    "projeto": ["Projeto Arquitetônico.pdf", "Projeto Estrutural.pdf", "Projeto Hidráulico.pdf"],
    "contrato": ["Contrato de Empreitada.pdf", "Aditivo Contratual.pdf"],
    "nota_fiscal": ["NF Cimento.pdf", "NF Aço CA-50.pdf", "NF Mão de Obra.pdf"],
    "foto": ["Fundação.jpg", "Alvenaria 1º Pav.jpg", "Cobertura.jpg"],
    "outro": ["ART.pdf", "Diário de Obra.pdf"],
}


def seed() -> dict[str, object]:
    with SessionLocal() as s:
        company_id = s.execute(
            text(
                "INSERT INTO companies (cnpj, razao_social) VALUES (:c, :r) "
                "ON CONFLICT (cnpj) DO UPDATE SET razao_social = EXCLUDED.razao_social RETURNING id"
            ),
            {"c": DEMO_CNPJ, "r": DEMO_COMPANY},
        ).scalar_one()

        user_id = s.execute(
            text(
                "INSERT INTO users (email, password_hash, nome) VALUES (:e, :p, :n) "
                "ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash "
                "RETURNING id"
            ),
            {"e": DEMO_USER_EMAIL, "p": hash_password(DEMO_USER_SENHA), "n": DEMO_USER_NOME},
        ).scalar_one()

        s.execute(
            text(
                "INSERT INTO user_company_role (company_id, user_id, role) "
                "VALUES (:c, :u, 'owner') ON CONFLICT (company_id, user_id) DO NOTHING"
            ),
            {"c": company_id, "u": user_id},
        )

        # Idempotência: se já há obras nesta empresa, não re-semeia os filhos.
        n_obras = s.execute(
            text("SELECT count(*) FROM obras WHERE company_id = :c"), {"c": company_id}
        ).scalar_one()
        if n_obras:
            s.commit()
            return {"company_id": str(company_id), "user_id": str(user_id),
                    "status": f"já semeado ({n_obras} obras) — sem alteração"}

        # Clientes
        cliente_ids: list[str] = []
        for tipo_pessoa, doc, nome, tel, email in CLIENTES:
            cid = s.execute(
                text(
                    "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome, telefone, email) "
                    "VALUES (:c, :tp, :doc, :nome, :tel, :email) RETURNING id"
                ),
                {"c": company_id, "tp": tipo_pessoa, "doc": doc, "nome": nome, "tel": tel, "email": email},
            ).scalar_one()
            cliente_ids.append(cid)

        # Obras (10)
        obra_ids: list[str] = []
        for i in range(10):
            cliente_id = cliente_ids[i % len(cliente_ids)]
            status = OBRA_STATUS[i]
            valor = 250000 + i * 175000
            oid = s.execute(
                text(
                    "INSERT INTO obras (company_id, cliente_id, status, codigo, nome, "
                    "data_inicio, data_prevista_fim, valor_contrato) VALUES "
                    "(:c, :cli, CAST(:st AS obra_status), :cod, :nome, "
                    ":ini, :fim, :valor) RETURNING id"
                ),
                {
                    "c": company_id, "cli": cliente_id, "st": status,
                    "cod": f"OBR-D{i + 1:03d}", "nome": OBRA_NOMES[i],
                    "ini": f"2025-{(i % 12) + 1:02d}-05",
                    "fim": f"2026-{(i % 12) + 1:02d}-20",
                    "valor": str(valor),
                },
            ).scalar_one()
            obra_ids.append(oid)
            # owner como membro responsável nas primeiras obras
            if i < 5:
                s.execute(
                    text(
                        "INSERT INTO obra_membro (company_id, obra_id, user_id, papel) "
                        "VALUES (:c, :o, :u, 'responsavel')"
                    ),
                    {"c": company_id, "o": oid, "u": user_id},
                )

        # Documentos (50: 5 por obra)
        n_docs = 0
        for i, oid in enumerate(obra_ids):
            for j in range(5):
                tipo = DOC_TIPOS[(i + j) % len(DOC_TIPOS)]
                nomes = DOC_NOMES[tipo]
                nome = nomes[j % len(nomes)]
                s.execute(
                    text(
                        "INSERT INTO documento (company_id, obra_id, nome, tipo, storage_path, "
                        "size_bytes, categoria, visivel_cliente, uploaded_by) VALUES "
                        "(:c, :o, :nome, CAST(:tipo AS documento_tipo), :path, :size, :cat, :vis, :u)"
                    ),
                    {
                        "c": company_id, "o": oid, "nome": nome, "tipo": tipo,
                        "path": f"documents/{company_id}/{oid}/{j}-{nome}",
                        "size": 120000 + j * 45000, "cat": tipo,
                        "vis": tipo in ("contrato", "foto"), "u": user_id,
                    },
                )
                n_docs += 1

        # Orçamentos (5, nas 5 primeiras obras) + versão + itens EAP
        orc_status = ["aprovado", "aguardando_aprovacao", "em_revisao", "rascunho", "rejeitado"]
        for i in range(5):
            oid = obra_ids[i]
            orc_id = s.execute(
                text(
                    "INSERT INTO orcamento (company_id, obra_id, titulo, status, created_by) "
                    "VALUES (:c, :o, :t, CAST(:st AS orcamento_status), :u) RETURNING id"
                ),
                {"c": company_id, "o": oid, "t": f"Orçamento — {OBRA_NOMES[i]}",
                 "st": orc_status[i], "u": user_id},
            ).scalar_one()
            custo = 200000 + i * 90000
            preco = int(custo * 1.28)
            # markup_global/taxa_adm/margem são NUMERIC(5,4) — frações/multiplicador
            # (< 10). markup 1.28 (28%), taxa adm 0.05, margem 0.18.
            ver_id = s.execute(
                text(
                    "INSERT INTO orcamento_versao (company_id, orcamento_id, numero, custo_direto, "
                    "markup_global, taxa_adm, preco_venda, margem) VALUES "
                    "(:c, :orc, 1, :cd, 1.28, 0.05, :pv, 0.18) RETURNING id"
                ),
                {"c": company_id, "orc": orc_id, "cd": str(custo), "pv": str(preco)},
            ).scalar_one()
            # 2 fases (F) com 1 insumo (I) cada
            for f in range(2):
                fase_id = s.execute(
                    text(
                        "INSERT INTO orcamento_item (company_id, versao_id, tipo, codigo, descricao, "
                        "sort_order) VALUES (:c, :v, 'F', :cod, :desc, :so) RETURNING id"
                    ),
                    {"c": company_id, "v": ver_id, "cod": f"{f + 1}",
                     "desc": ["Serviços Preliminares", "Estrutura"][f], "so": f * 10},
                ).scalar_one()
                s.execute(
                    text(
                        "INSERT INTO orcamento_item (company_id, versao_id, parent_id, tipo, codigo, "
                        "descricao, unidade, quantidade, preco_unitario, subtotal, sort_order) VALUES "
                        "(:c, :v, :p, 'I', :cod, :desc, :un, :qt, :pu, :sub, :so)"
                    ),
                    {"c": company_id, "v": ver_id, "p": fase_id,
                     "cod": ["87490", "92715"][f], "desc": ["Concreto usinado fck 25", "Aço CA-50"][f],
                     "un": ["m³", "kg"][f], "qt": ["45.5", "1200"][f],
                     "pu": ["480.00", "9.80"][f], "sub": ["21840.00", "11760.00"][f], "so": f * 10 + 1},
                )

        # Chamados (tickets) + mensagens
        ticket_status = ["aberto", "andamento", "resolvido"]
        for i in range(3):
            oid = obra_ids[i]
            tid = s.execute(
                text(
                    "INSERT INTO ticket (company_id, obra_id, titulo, descricao, status, created_by) "
                    "VALUES (:c, :o, :t, :d, CAST(:st AS ticket_status), :u) RETURNING id"
                ),
                {"c": company_id, "o": oid,
                 "t": ["Infiltração no 2º pavimento", "Ajuste no cronograma", "Dúvida sobre acabamento"][i],
                 "d": "Registrado pelo cliente via portal.", "st": ticket_status[i], "u": user_id},
            ).scalar_one()
            s.execute(
                text(
                    "INSERT INTO ticket_mensagem (company_id, ticket_id, author_id, content) "
                    "VALUES (:c, :t, :u, :msg)"
                ),
                {"c": company_id, "t": tid, "u": user_id, "msg": "Recebido, vamos verificar e retornar."},
            )
            # mensagem do cliente (author_id nulo = cliente pelo portal)
            s.execute(
                text(
                    "INSERT INTO ticket_mensagem (company_id, ticket_id, author_id, content) "
                    "VALUES (:c, :t, NULL, :msg)"
                ),
                {"c": company_id, "t": tid, "msg": "Obrigado! Aguardo o retorno."},
            )

        s.commit()
        return {
            "company_id": str(company_id),
            "user_id": str(user_id),
            "login": f"{DEMO_USER_EMAIL} / {DEMO_USER_SENHA}",
            "clientes": len(cliente_ids),
            "obras": len(obra_ids),
            "documentos": n_docs,
            "orcamentos": 5,
            "tickets": 3,
        }


if __name__ == "__main__":
    for k, v in seed().items():
        print(f"{k}: {v}")
