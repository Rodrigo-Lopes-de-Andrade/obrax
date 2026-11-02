"""Regressão: a sessão de testes nunca enxerga credenciais de produção do `.env`.

`config.py` faz `load_dotenv(.env, override=False)`; sem o pin do conftest, chaves
de integração vazavam do `.env` de PROD e os testes falavam com o storage real.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from app.core.config import settings

_PROD_MARKERS = ("supabase.co", "supabase.com", "pooler.supabase")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "minio", "postgres"}


def test_sessao_de_testes_nao_enxerga_producao() -> None:
    campos = {
        "storage_endpoint_url": settings.storage_endpoint_url,
        "supabase_url": settings.supabase_url,
        "uazapi_base_url": settings.uazapi_base_url,
        "app_user_database_url": settings.app_user_database_url,
        "app_admin_database_url": settings.app_admin_database_url,
    }
    for nome, valor in campos.items():
        for marcador in _PROD_MARKERS:
            assert marcador not in valor.lower(), f"{nome} aponta para produção"

    host = (urlsplit(settings.storage_endpoint_url).hostname or "").lower()
    assert host in _LOCAL_HOSTS, "storage de teste deve ser o MinIO local"
