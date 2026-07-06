"""Seed de demonstração: 2 empresas + 1 usuário cada, para exercitar o
isolamento multi-tenant (RLS) manualmente via psql ou pela suite de testes.

Roda como o usuário de conexão padrão (`obrax`, superuser local — bypassa
RLS), então sempre enxerga as duas empresas independente de `app.company_id`.

Uso:
    cd backend && uv run python -m scripts.seed_demo
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.db import SessionLocal

_SEED = [
    {
        "cnpj": "11111111000191",
        "razao_social": "Construtora Alfa Ltda",
        "email": "admin@alfa.example.com",
        "nome": "Admin Alfa",
    },
    {
        "cnpj": "22222222000191",
        "razao_social": "Construtora Beta Ltda",
        "email": "admin@beta.example.com",
        "nome": "Admin Beta",
    },
]


def seed() -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    with SessionLocal() as session:
        for entry in _SEED:
            company_id = session.execute(
                text(
                    """
                    INSERT INTO companies (cnpj, razao_social)
                    VALUES (:cnpj, :razao_social)
                    ON CONFLICT (cnpj) DO UPDATE SET razao_social = EXCLUDED.razao_social
                    RETURNING id
                    """
                ),
                {"cnpj": entry["cnpj"], "razao_social": entry["razao_social"]},
            ).scalar_one()

            user_id = session.execute(
                text(
                    """
                    INSERT INTO users (email, password_hash, nome)
                    VALUES (:email, 'seed-not-a-real-hash', :nome)
                    ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome
                    RETURNING id
                    """
                ),
                {"email": entry["email"], "nome": entry["nome"]},
            ).scalar_one()

            session.execute(
                text(
                    """
                    INSERT INTO user_company_role (company_id, user_id, role)
                    VALUES (:company_id, :user_id, 'owner')
                    ON CONFLICT (company_id, user_id) DO NOTHING
                    """
                ),
                {"company_id": company_id, "user_id": user_id},
            )

            result.append(
                {
                    "company_id": str(company_id),
                    "user_id": str(user_id),
                    "razao_social": entry["razao_social"],
                    "email": entry["email"],
                }
            )
        session.commit()
    return result


if __name__ == "__main__":
    for row in seed():
        print(row)
