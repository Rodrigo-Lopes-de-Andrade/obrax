"""Bootstrap de um usuário admin (role `owner`) — o primeiro acesso de um tenant.

Não há signup público (usuários entram por convite), então o primeiro owner de
uma empresa precisa ser criado direto no banco. Idempotente: rodar de novo
atualiza o nome/senha do usuário e não duplica a empresa nem o vínculo.

Roda como o role de conexão padrão (superuser em prod / `obrax` local), que
bypassa RLS — necessário para um insert pré-tenant. A senha vem da env
`ADMIN_PASSWORD` (não em argv, para não vazar no histórico/-C).

Uso (na máquina Fly):
    ADMIN_PASSWORD=... python -m scripts.create_admin \\
        --email you@example.com --nome "Seu Nome" --razao "Empresa" --cnpj 00000000000000
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.security import hash_password


def create_admin(*, email: str, nome: str, razao: str, cnpj: str, password: str) -> dict[str, str]:
    password_hash = hash_password(password)
    with SessionLocal() as session:
        company_id = session.execute(
            text(
                """
                INSERT INTO companies (cnpj, razao_social)
                VALUES (:cnpj, :razao)
                ON CONFLICT (cnpj) DO UPDATE SET razao_social = EXCLUDED.razao_social
                RETURNING id
                """
            ),
            {"cnpj": cnpj, "razao": razao},
        ).scalar_one()

        user_id = session.execute(
            text(
                """
                INSERT INTO users (email, password_hash, nome)
                VALUES (:email, :password_hash, :nome)
                ON CONFLICT (email)
                DO UPDATE SET password_hash = EXCLUDED.password_hash, nome = EXCLUDED.nome
                RETURNING id
                """
            ),
            {"email": email, "password_hash": password_hash, "nome": nome},
        ).scalar_one()

        session.execute(
            text(
                """
                INSERT INTO user_company_role (company_id, user_id, role)
                VALUES (:company_id, :user_id, 'owner')
                ON CONFLICT (company_id, user_id) DO UPDATE SET role = 'owner'
                """
            ),
            {"company_id": company_id, "user_id": user_id},
        )
        session.commit()

    return {"company_id": str(company_id), "user_id": str(user_id), "email": email}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cria/atualiza um admin (owner) de um tenant.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nome", required=True)
    parser.add_argument("--razao", required=True, help="Razão social da empresa.")
    parser.add_argument(
        "--cnpj", required=True, help="CNPJ (só dígitos; placeholder editável depois)."
    )
    args = parser.parse_args(argv)

    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        print("ADMIN_PASSWORD não setada no ambiente.", file=sys.stderr)
        return 1

    result = create_admin(
        email=args.email, nome=args.nome, razao=args.razao, cnpj=args.cnpj, password=password
    )
    print(f"admin owner pronto: {result['email']} (company={result['company_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
