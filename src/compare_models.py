"""
compare_models.py — Comparação lado a lado de LLMs gerenciados (multicloud).

Mesmos 5 prompts de infraestrutura do gcp-vertex-ai, agora com a Azure no centro:
    - Azure : GPT-4o-mini  (Azure OpenAI / Azure AI Foundry)
    - AWS   : Claude 3 Haiku via Bedrock        (opcional, só se houver creds)
    - GCP   : Gemini 1.5 Flash via Vertex AI     (opcional, só se houver creds)

Para cada modelo medimos:
    - latência (ms)
    - contagem de tokens (entrada + saída)
    - custo estimado (US$) com base no preço público por 1M de tokens
    - qualidade da resposta (1-5), heurística simples de cobertura de palavras-chave

Saída:
    reports/azure_comparison.json  -> dados crus de cada execução
    tabela lado a lado no terminal (Rich, com fallback texto puro)

Uso:
    python src/compare_models.py
    python src/compare_models.py --only-azure   # ignora AWS e GCP

Design: se SDK/credenciais de uma nuvem não estiverem disponíveis, aquele backend
entra em modo "stub" determinístico — a estrutura do relatório é gerada mesmo sem
conta ativa (útil em CI/portfólio). O Azure é obrigatório para o modo "real".
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REPORTS = RAIZ / "reports"

# Os 5 prompts de infraestrutura — idênticos aos do gcp-vertex-ai (paridade).
PROMPTS = [
    "Explique a diferença entre NAT Gateway e Internet Gateway na AWS",
    "Quais são os 5 principais riscos de segurança em uma VPC pública?",
    "Escreva um script Python para listar instâncias EC2 paradas",
    "Compare Kubernetes e ECS para cargas de trabalho de produção",
    "Qual a diferença entre RTO e RPO em disaster recovery?",
]

# Preços públicos (US$ por 1M de tokens) — referência de custo.
# GPT-4o-mini: 0,15 / 0,60.  Claude 3 Haiku: 0,25 / 1,25.  Gemini 1.5 Flash: 0,075 / 0,30.
PRECOS = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "claude-3-haiku": {"in": 0.25, "out": 1.25},
    "gemini-1.5-flash": {"in": 0.075, "out": 0.30},
}

# Palavras-chave esperadas por prompt para a heurística de qualidade (1-5).
ESPERADO = [
    ["nat", "internet gateway", "privada", "saída", "público"],
    ["exposição", "porta", "security group", "ssh", "público", "iam"],
    ["boto3", "ec2", "stopped", "describe_instances", "filter"],
    ["kubernetes", "ecs", "fargate", "produção", "escala"],
    ["rto", "rpo", "recuperação", "tempo", "dados"],
]


def _qualidade(resposta: str, esperado: list[str]) -> int:
    """Nota 1-5 = fração de palavras-chave cobertas, normalizada para [1,5]."""
    if not resposta:
        return 1
    texto = resposta.lower()
    cobertas = sum(1 for kw in esperado if kw in texto)
    frac = cobertas / len(esperado)
    return max(1, min(5, round(1 + frac * 4)))


def _custo(modelo: str, tin: int, tout: int) -> float:
    p = PRECOS[modelo]
    return round((tin * p["in"] + tout * p["out"]) / 1_000_000, 8)


# ---------------------------------------------------------------------------
# Backend Azure OpenAI (GPT-4o-mini) — obrigatório
# ---------------------------------------------------------------------------
def chamar_azure(prompt: str) -> dict:
    """Invoca o GPT-4o-mini via Azure OpenAI. Retorna métricas + texto."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    deploy = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")

    inicio = time.perf_counter()
    resp = client.chat.completions.create(
        model=deploy,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    latencia_ms = (time.perf_counter() - inicio) * 1000
    uso = resp.usage
    return {
        "texto": resp.choices[0].message.content or "",
        "latencia_ms": round(latencia_ms, 1),
        "tokens_in": uso.prompt_tokens,
        "tokens_out": uso.completion_tokens,
    }


# ---------------------------------------------------------------------------
# Backend AWS Bedrock (Claude 3 Haiku) — opcional
# ---------------------------------------------------------------------------
def chamar_bedrock(prompt: str) -> dict:
    """Invoca o Claude 3 Haiku via Bedrock. Requer credenciais AWS."""
    import boto3

    regiao_aws = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    cliente = boto3.client("bedrock-runtime", region_name=regiao_aws)
    corpo = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    inicio = time.perf_counter()
    resp = cliente.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=json.dumps(corpo),
    )
    latencia_ms = (time.perf_counter() - inicio) * 1000
    payload = json.loads(resp["body"].read())
    uso = payload["usage"]
    return {
        "texto": payload["content"][0]["text"],
        "latencia_ms": round(latencia_ms, 1),
        "tokens_in": uso["input_tokens"],
        "tokens_out": uso["output_tokens"],
    }


# ---------------------------------------------------------------------------
# Backend GCP Vertex AI (Gemini 1.5 Flash) — opcional
# ---------------------------------------------------------------------------
def chamar_gemini(prompt: str) -> dict:
    """Invoca o Gemini 1.5 Flash via Vertex AI. Requer credenciais GCP."""
    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    modelo = GenerativeModel("gemini-1.5-flash")
    inicio = time.perf_counter()
    resp = modelo.generate_content(prompt)
    latencia_ms = (time.perf_counter() - inicio) * 1000
    uso = resp.usage_metadata
    return {
        "texto": resp.text,
        "latencia_ms": round(latencia_ms, 1),
        "tokens_in": uso.prompt_token_count,
        "tokens_out": uso.candidates_token_count,
    }


def _executar(nome_modelo: str, fn, prompt: str, esperado: list[str]) -> dict:
    """Executa uma chamada protegida por try/except e monta o registro padrão."""
    try:
        r = fn(prompt)
        return {
            "modelo": nome_modelo,
            "modo": "real",
            "latencia_ms": r["latencia_ms"],
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "tokens_total": r["tokens_in"] + r["tokens_out"],
            "custo_usd": _custo(nome_modelo, r["tokens_in"], r["tokens_out"]),
            "qualidade": _qualidade(r["texto"], esperado),
            "resposta": r["texto"],
        }
    except Exception as exc:  # noqa: BLE001 — qualquer falha vira modo stub
        return {
            "modelo": nome_modelo,
            "modo": "stub",
            "erro": str(exc)[:200],
            "latencia_ms": None,
            "tokens_in": None,
            "tokens_out": None,
            "tokens_total": None,
            "custo_usd": None,
            "qualidade": None,
            "resposta": "",
        }


def _render_tabela(resultados: list[dict]) -> None:
    """Imprime a tabela lado a lado (Rich se disponível, senão texto puro)."""
    linhas = []
    for item in resultados:
        for m in item["modelos"]:
            linhas.append(
                (
                    item["prompt"][:40] + "…",
                    m["modelo"],
                    m["modo"],
                    f'{m["latencia_ms"]}' if m["latencia_ms"] is not None else "-",
                    f'{m["tokens_total"]}' if m["tokens_total"] is not None else "-",
                    f'{m["custo_usd"]:.6f}' if m["custo_usd"] is not None else "-",
                    f'{m["qualidade"]}' if m["qualidade"] is not None else "-",
                )
            )
    cabecalho = ["Prompt", "Modelo", "Modo", "Latência(ms)", "Tokens", "Custo US$", "Qual."]
    try:
        from rich.console import Console
        from rich.table import Table

        t = Table(title="Azure GPT-4o-mini vs Bedrock Claude vs Vertex Gemini")
        for c in cabecalho:
            t.add_column(c)
        for ln in linhas:
            t.add_row(*ln)
        Console().print(t)
    except Exception:  # pragma: no cover — fallback sem Rich
        print(" | ".join(cabecalho))
        for ln in linhas:
            print(" | ".join(ln))


def main() -> None:
    ap = argparse.ArgumentParser(description="Compara Azure GPT-4o-mini, Bedrock e Vertex")
    ap.add_argument("--only-azure", action="store_true", help="não chamar AWS nem GCP")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except Exception:  # pragma: no cover
        pass

    usar_bedrock = not args.only_azure and bool(os.getenv("AWS_ACCESS_KEY_ID"))
    usar_gemini = not args.only_azure and bool(os.getenv("GOOGLE_CLOUD_PROJECT"))

    resultados = []
    for i, prompt in enumerate(PROMPTS):
        modelos = [_executar("gpt-4o-mini", chamar_azure, prompt, ESPERADO[i])]
        if usar_bedrock:
            modelos.append(_executar("claude-3-haiku", chamar_bedrock, prompt, ESPERADO[i]))
        if usar_gemini:
            modelos.append(_executar("gemini-1.5-flash", chamar_gemini, prompt, ESPERADO[i]))
        resultados.append({"prompt": prompt, "modelos": modelos})
        print(f"[{i+1}/{len(PROMPTS)}] processado: {prompt[:50]}…")

    REPORTS.mkdir(exist_ok=True)
    saida = REPORTS / "azure_comparison.json"
    saida.write_text(
        json.dumps(
            {
                "bedrock_habilitado": usar_bedrock,
                "gemini_habilitado": usar_gemini,
                "resultados": resultados,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nResultados salvos em {saida}\n")
    _render_tabela(resultados)


if __name__ == "__main__":
    main()
