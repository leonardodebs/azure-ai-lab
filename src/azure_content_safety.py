"""
azure_content_safety.py — Análise de moderação com Azure AI Content Safety.

CAPACIDADE ÚNICA DA AZURE — sem equivalente direto no Amazon Bedrock. O Bedrock
oferece Guardrails (filtros configuráveis acoplados ao modelo), mas a Azure expõe
um serviço dedicado de classificação de conteúdo, com severidade graduada por
categoria, usável independentemente de qualquer LLM.

Analisa 10 textos de exemplo (mistura de conteúdo benigno de infraestrutura e
exemplos sintéticos sinalizáveis) nas 4 categorias da API:
    - Hate (ódio)        - Violence (violência)
    - Sexual             - SelfHarm (automutilação)
Cada categoria recebe severidade 0-6 (0 = seguro; 6 = severíssimo).

Uso:
    python src/azure_content_safety.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Limiar a partir do qual marcamos como "sinalizado" (ajuste conforme política).
LIMIAR = 2

# 10 textos de exemplo. Maioria é conteúdo legítimo de operações/infra; alguns
# são frases sintéticas brandas para exercitar as categorias sem material gráfico.
TEXTOS = [
    "Como reiniciar o cluster ECS após um deploy com falha?",
    "Passos para configurar o health check do ALB e evitar 502.",
    "Eu odeio quando o pipeline quebra na sexta-feira à noite.",
    "Vou destruir esse servidor legado e migrar tudo para Kubernetes.",
    "Procedimento de failover do RDS Multi-AZ com RTO de 2 minutos.",
    "Esse incidente foi violento: o tráfego triplicou e derrubou a API.",
    "Checklist de segurança para endurecer uma VPC pública.",
    "Receita de bolo de cenoura com cobertura de chocolate.",
    "Como rotacionar as chaves de acesso no Key Vault do Azure?",
    "Tutorial de boas práticas de IAM com least privilege.",
]


def _config() -> tuple[str, str]:
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except Exception:  # pragma: no cover
        pass
    endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "")
    chave = os.getenv("AZURE_CONTENT_SAFETY_API_KEY", "") or os.getenv(
        "AZURE_OPENAI_API_KEY", ""
    )
    return endpoint, chave


def _categorias_de(resposta) -> dict:
    """Extrai {categoria: severidade} de uma resposta da API (formato 1.0)."""
    return {item.category: item.severity for item in resposta.categories_analysis}


def analisar(endpoint: str, chave: str, texto: str) -> dict:
    """Chama a API de Content Safety para um texto e retorna severidades."""
    from azure.ai.contentsafety import ContentSafetyClient
    from azure.ai.contentsafety.models import AnalyzeTextOptions
    from azure.core.credentials import AzureKeyCredential

    client = ContentSafetyClient(endpoint, AzureKeyCredential(chave))
    resp = client.analyze_text(AnalyzeTextOptions(text=texto))
    return _categorias_de(resp)


def _render(linhas: list[tuple]) -> None:
    cabecalho = ["#", "Texto", "Hate", "Violence", "Sexual", "SelfHarm", "Sinalizado?"]
    try:
        from rich.console import Console
        from rich.table import Table

        t = Table(title="Azure AI Content Safety — severidade 0-6 por categoria")
        for c in cabecalho:
            t.add_column(c)
        for ln in linhas:
            t.add_row(*[str(x) for x in ln])
        Console().print(t)
    except Exception:  # pragma: no cover
        print(" | ".join(cabecalho))
        for ln in linhas:
            print(" | ".join(str(x) for x in ln))


def main() -> None:
    endpoint, chave = _config()
    if not endpoint or not chave or chave == "your_key_here":
        print(
            "[erro] Configure AZURE_CONTENT_SAFETY_ENDPOINT e a chave no .env "
            "(pode reutilizar a chave do recurso Cognitive Services).",
            file=sys.stderr,
        )
        sys.exit(1)

    linhas = []
    for i, texto in enumerate(TEXTOS, start=1):
        try:
            sev = analisar(endpoint, chave, texto)
        except Exception as exc:  # noqa: BLE001
            print(f"[erro] Falha ao analisar texto {i}: {str(exc)[:160]}", file=sys.stderr)
            sys.exit(1)
        h = sev.get("Hate", 0)
        v = sev.get("Violence", 0)
        s = sev.get("Sexual", 0)
        sh = sev.get("SelfHarm", 0)
        sinalizado = "⚠️ sim" if max(h, v, s, sh) >= LIMIAR else "ok"
        linhas.append((i, texto[:42] + "…", h, v, s, sh, sinalizado))

    _render(linhas)
    print(
        f"\nLimiar de sinalização: severidade >= {LIMIAR}. "
        "Content Safety é uma capacidade única da Azure — sem equivalente direto "
        "no Bedrock (que oferece Guardrails acoplados ao modelo, não um serviço "
        "dedicado de classificação)."
    )


if __name__ == "__main__":
    main()
