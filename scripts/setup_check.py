#!/usr/bin/env python3
"""
setup_check.py — Verificação de ambiente do Azure AI Lab.

Equivalente AWS: checar `aws sts get-caller-identity` + acesso ao Bedrock.
Aqui validamos, em ordem, que o ambiente está pronto para falar com o
Azure AI Foundry (Azure OpenAI):

    1. az --version              -> Azure CLI instalada
    2. az account show           -> sessão autenticada (az login feito)
    3. providers registrados     -> Microsoft.CognitiveServices e
                                    Microsoft.MachineLearningServices
    4. AzureOpenAI client        -> conexão real ao endpoint (lista deployments)

Para cada etapa imprime ✅/❌ e, em caso de falha, o comando de correção.
No final imprime "Azure AI Foundry: OK" se tudo passou, ou sai com código 1.

Uso:
    python scripts/setup_check.py
    make check
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Providers exigidos pelo laboratório (Azure AI Foundry usa ambos).
PROVIDERS = ["Microsoft.CognitiveServices", "Microsoft.MachineLearningServices"]


def _carregar_env() -> None:  # pragma: no cover
    """Carrega o .env (se existir) para popular AZURE_OPENAI_* no os.environ."""
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except Exception:  # pragma: no cover — dotenv é opcional
        pass


def _ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def _falha(msg: str, correcao: str) -> None:
    print(f"  ❌ {msg}")
    print(f"     ↳ correção: {correcao}")


def _run(args: list[str]) -> tuple[int, str]:
    """Executa um comando e retorna (returncode, stdout+stderr)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "comando não encontrado"
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def checar_cli() -> bool:  # pragma: no cover
    """1. az --version — a Azure CLI precisa estar instalada e no PATH."""
    print("[1/4] Azure CLI (az --version)")
    if shutil.which("az") is None:
        _falha(
            "Azure CLI não encontrada no PATH",
            "instale: https://learn.microsoft.com/cli/azure/install-azure-cli",
        )
        return False
    rc, out = _run(["az", "version", "-o", "json"])
    if rc != 0:
        _falha("az version falhou", "reinstale a Azure CLI")
        return False
    try:
        versao = json.loads(out).get("azure-cli", "?")
    except json.JSONDecodeError:
        versao = "?"
    _ok(f"Azure CLI instalada (versão {versao})")
    return True


def checar_conta() -> tuple[bool, str]:  # pragma: no cover
    """2. az account show — precisa de uma sessão autenticada (az login)."""
    print("[2/4] Sessão autenticada (az account show)")
    rc, out = _run(["az", "account", "show", "-o", "json"])
    if rc != 0:
        _falha(
            "nenhuma assinatura ativa / não autenticado",
            'az login && az account set --subscription "YOUR_SUBSCRIPTION_ID"',
        )
        return False, ""
    try:
        conta = json.loads(out)
        sub_id = conta.get("id", "")
        _ok(f"autenticado em '{conta.get('name', '?')}' (sub {sub_id[:8]}…)")
        return True, sub_id
    except json.JSONDecodeError:
        _falha("resposta inesperada de az account show", "az login novamente")
        return False, ""


def checar_providers(sub_id: str) -> bool:  # pragma: no cover
    """3. Providers Microsoft.CognitiveServices e MachineLearningServices."""
    print("[3/4] Resource Providers registrados")
    todos_ok = True
    for prov in PROVIDERS:
        rc, out = _run(
            ["az", "provider", "show", "--namespace", prov,
             "--query", "registrationState", "-o", "tsv"]
        )
        estado = out.strip()
        if rc == 0 and estado == "Registered":
            _ok(f"{prov}: Registered")
        else:
            _falha(
                f"{prov}: {estado or 'não registrado'}",
                f"az provider register --namespace {prov}",
            )
            todos_ok = False
    return todos_ok


def checar_openai() -> bool:  # pragma: no cover
    """4. AzureOpenAI client — conexão real ao endpoint (lista os deployments)."""
    print("[4/4] Conexão AzureOpenAI client")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    deploy = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")

    if not endpoint or not api_key or api_key == "your_key_here":
        _falha(
            "AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY ausentes",
            "copie .env.example para .env e preencha com os outputs do Terraform",
        )
        return False
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=endpoint, api_key=api_key, api_version=api_version
        )
        # Chamada mínima e barata: um chat de 1 token confirma o deployment.
        resp = client.chat.completions.create(
            model=deploy,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        _ok(f"endpoint respondeu (deployment '{deploy}', id {resp.id[:12]}…)")
        return True
    except Exception as exc:  # noqa: BLE001
        _falha(
            f"falha ao conectar no Azure OpenAI: {str(exc)[:160]}",
            "confira endpoint/chave e se o deployment '%s' existe (terraform apply)"
            % deploy,
        )
        return False


def main() -> int:  # pragma: no cover
    _carregar_env()
    print("=" * 64)
    print("Azure AI Lab — verificação de ambiente (setup_check)")
    print("=" * 64)

    ok_cli = checar_cli()
    ok_conta, sub_id = checar_conta() if ok_cli else (False, "")
    ok_prov = checar_providers(sub_id) if ok_conta else False
    ok_oai = checar_openai()

    print("-" * 64)
    if ok_cli and ok_conta and ok_prov and ok_oai:
        print("Azure AI Foundry: OK")
        return 0
    print("Azure AI Foundry: ERRO — resolva os itens ❌ acima e rode novamente.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
