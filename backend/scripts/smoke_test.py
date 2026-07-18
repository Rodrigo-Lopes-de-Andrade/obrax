"""S12.6 — smoke test de deploy (read-only), o gate do blue-green.

Roda contra a URL de um ambiente recém-deployado (o "green") ANTES de repontar
o tráfego. Se qualquer checagem-gate falhar, sai com código != 0 e a virada NÃO
deve prosseguir. Só faz GETs idempotentes — seguro rodar contra produção.

Checagens (gate = bloqueia a virada; info = só reporta):
    [gate] /health              → 200 e status "ok" (com --require-storage,
                                  exige storage "ok" também).
    [gate] /openapi.json        → 200; confirma que a API certa está servindo
                                  (imprime title/version — útil p/ conferir o build).
    [gate] rota protegida sem token → 401; prova que o router /api/v1 está
                                  montado e o auth/tenant middleware está ativo.
    [info] /  (--frontend-url)  → 200 e contém "Obrax"; landing servindo.

Uso:
    cd backend && uv run python -m scripts.smoke_test --api-url https://api.obrax.com.br
    cd backend && uv run python -m scripts.smoke_test \\
        --api-url http://localhost:8000 --frontend-url http://localhost:3000 \\
        --require-storage
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import httpx

# Rota protegida estável usada para provar que o auth está sendo aplicado.
_PROTECTED_PATH = "/api/v1/dashboard/summary"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    gate: bool  # True = falha bloqueia a virada; False = informativo
    detail: str


def _get(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        return client.get(url)
    except httpx.HTTPError as exc:
        _get.error = str(exc)  # type: ignore[attr-defined]
        return None


def check_health(client: httpx.Client, api_url: str, require_storage: bool) -> CheckResult:
    resp = _get(client, f"{api_url}/health")
    if resp is None:
        return CheckResult("health", False, True, f"sem resposta ({_get.error})")  # type: ignore[attr-defined]
    if resp.status_code != 200:
        return CheckResult("health", False, True, f"HTTP {resp.status_code}")
    body = resp.json()
    if body.get("status") != "ok":
        return CheckResult("health", False, True, f"status={body.get('status')!r}")
    storage = body.get("storage")
    if require_storage and storage != "ok":
        return CheckResult("health", False, True, f"storage={storage!r} (exigido ok)")
    return CheckResult(
        "health", True, True, f"status=ok, storage={storage}, realtime={body.get('realtime')}"
    )


def check_openapi(client: httpx.Client, api_url: str) -> CheckResult:
    resp = _get(client, f"{api_url}/openapi.json")
    if resp is None:
        return CheckResult("openapi", False, True, f"sem resposta ({_get.error})")  # type: ignore[attr-defined]
    if resp.status_code != 200:
        return CheckResult("openapi", False, True, f"HTTP {resp.status_code}")
    info = resp.json().get("info", {})
    return CheckResult("openapi", True, True, f"{info.get('title')} v{info.get('version')}")


def check_auth_enforced(client: httpx.Client, api_url: str) -> CheckResult:
    resp = _get(client, f"{api_url}{_PROTECTED_PATH}")
    if resp is None:
        return CheckResult("auth", False, True, f"sem resposta ({_get.error})")  # type: ignore[attr-defined]
    if resp.status_code in (401, 403):
        return CheckResult(
            "auth", True, True, f"rota protegida rejeita sem token (HTTP {resp.status_code})"
        )
    if resp.status_code == 404:
        return CheckResult("auth", False, True, f"{_PROTECTED_PATH} não existe (build errado?)")
    return CheckResult(
        "auth",
        False,
        True,
        f"rota protegida respondeu HTTP {resp.status_code} sem token (auth não aplicado!)",
    )


def check_frontend(client: httpx.Client, frontend_url: str) -> CheckResult:
    resp = _get(client, frontend_url)
    if resp is None:
        return CheckResult("frontend", False, False, f"sem resposta ({_get.error})")  # type: ignore[attr-defined]
    if resp.status_code != 200:
        return CheckResult("frontend", False, False, f"HTTP {resp.status_code}")
    if "Obrax" not in resp.text:
        return CheckResult("frontend", False, False, "200 mas sem 'Obrax' no HTML")
    return CheckResult("frontend", True, False, "landing servindo (200, contém 'Obrax')")


def run(api_url: str, frontend_url: str | None, require_storage: bool, timeout: float) -> int:
    api_url = api_url.rstrip("/")
    print(f"smoke test → {api_url}\n")

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        results = [
            check_health(client, api_url, require_storage),
            check_openapi(client, api_url),
            check_auth_enforced(client, api_url),
        ]
        if frontend_url:
            results.append(check_frontend(client, frontend_url.rstrip("/")))

    gate_failures = 0
    for r in results:
        mark = "✓" if r.ok else "✗"
        tag = "" if r.gate else " (info)"
        print(f"  {mark} {r.name}{tag}: {r.detail}")
        if not r.ok and r.gate:
            gate_failures += 1

    if gate_failures:
        print(f"\n✗ SMOKE FALHOU — {gate_failures} gate(s). NÃO repontar tráfego.")
        return 1
    print("\n✓ smoke 100% nos gates — seguro repontar tráfego.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test read-only de um ambiente (S12.6).")
    parser.add_argument(
        "--api-url", required=True, help="Base da API (ex.: https://api.obrax.com.br)."
    )
    parser.add_argument("--frontend-url", help="Base do frontend (opcional; check informativo).")
    parser.add_argument(
        "--require-storage", action="store_true", help="Falha o gate se o storage não estiver 'ok'."
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="Timeout por request em segundos."
    )
    args = parser.parse_args(argv)
    return run(args.api_url, args.frontend_url, args.require_storage, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
