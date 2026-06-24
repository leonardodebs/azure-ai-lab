"""
semantic_kernel_demo.py — Microsoft Semantic Kernel (framework de agentes da Azure).

Equivalente AWS: Bedrock Agents (orquestração de ferramentas + LLM). O Semantic
Kernel é o framework NATIVO de agentes da Azure e aparece com frequência em vagas
("JDs") de engenharia de IA corporativa.

Demonstra um kernel com dois plugins de função:

    InfraPlugin
        - explain_service(name)        -> explica um serviço de infraestrutura
        - compare_services(a, b)        -> compara dois serviços (ex: ECS vs AKS)

    RunbookPlugin
        - search_runbook(topic)         -> chama o retriever do azure_rag (RAG real)

Fluxo: o modelo (GPT-4o-mini) decide automaticamente quais funções chamar
(function calling = "planner" moderno do SK) para responder:

    "Como faço rollback de ECS e diferença para AKS?"

→ search_runbook("rollback ECS") + compare_services("ECS", "AKS")
→ resposta sintetizada com as fontes.

Uso:
    pip install semantic-kernel
    python src/semantic_kernel_demo.py
    python src/semantic_kernel_demo.py "sua pergunta"
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"
for caminho in (str(RAIZ), str(SRC)):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

PERGUNTA_PADRAO = "Como faço rollback de ECS e diferença para AKS?"

# Mini base de conhecimento para o InfraPlugin (determinística, sem nuvem).
SERVICOS = {
    "ecs": "Amazon ECS — orquestrador de contêineres da AWS; usa Task Definitions "
    "e roda em Fargate (serverless) ou EC2. Rollback = apontar para a revisão "
    "anterior da Task Definition.",
    "aks": "Azure Kubernetes Service — Kubernetes gerenciado da Azure. Rollback = "
    "'kubectl rollout undo deployment/X', revertendo para o ReplicaSet anterior.",
    "eks": "Amazon EKS — Kubernetes gerenciado da AWS, equivalente direto do AKS.",
    "lambda": "AWS Lambda — funções serverless orientadas a eventos.",
    "alb": "Application Load Balancer — balanceador L7 da AWS; emite 502/503 quando "
    "targets estão unhealthy ou respondem de forma inválida.",
}


# ---------------------------------------------------------------------------
# Plugins do Semantic Kernel
# ---------------------------------------------------------------------------
def _build_plugins():  # pragma: no cover
    """Cria as classes de plugin. Importa semantic_kernel só aqui (lazy)."""
    from semantic_kernel.functions import kernel_function

    class InfraPlugin:
        """Conhecimento sobre serviços de infraestrutura."""

        @kernel_function(description="Explica um serviço de infraestrutura pelo nome.")
        def explain_service(self, name: str) -> str:
            return SERVICOS.get(
                name.strip().lower(), f"Serviço '{name}' não está na base local."
            )

        @kernel_function(description="Compara dois serviços de infraestrutura.")
        def compare_services(self, a: str, b: str) -> str:
            da = SERVICOS.get(a.strip().lower(), f"({a} desconhecido)")
            db = SERVICOS.get(b.strip().lower(), f"({b} desconhecido)")
            return f"Comparação {a} vs {b}:\n- {a}: {da}\n- {b}: {db}"

    class RunbookPlugin:
        """Busca nos runbooks via o retriever real do azure_rag (RAG)."""

        @kernel_function(description="Busca nos runbooks de operação por um tópico.")
        def search_runbook(self, topic: str) -> str:
            try:
                import azure_rag

                cfg = azure_rag._config()
                fontes = azure_rag.buscar(cfg, topic, top_k=3)
                if not fontes:
                    return "Nenhum trecho de runbook encontrado."
                return "\n\n".join(f"[{f['file']}]\n{f['text']}" for f in fontes)
            except Exception as exc:  # noqa: BLE001 — fallback sem Azure ativo
                return (
                    f"(retriever indisponível: {str(exc)[:120]}) — configure o .env "
                    "e rode 'python src/azure_rag.py --index' para busca real."
                )

    return InfraPlugin(), RunbookPlugin()


async def _executar(pergunta: str) -> str:  # pragma: no cover
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.function_choice_behavior import (
        FunctionChoiceBehavior,
    )
    from semantic_kernel.connectors.ai.open_ai import (
        AzureChatCompletion,
        AzureChatPromptExecutionSettings,
    )
    from semantic_kernel.contents import ChatHistory

    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            service_id="azure-gpt4o-mini",
            deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"),
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
    )
    infra, runbook = _build_plugins()
    kernel.add_plugin(infra, plugin_name="InfraPlugin")
    kernel.add_plugin(runbook, plugin_name="RunbookPlugin")

    # function calling automático = o "planner" moderno: o modelo escolhe as funções.
    settings = AzureChatPromptExecutionSettings()
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    service = kernel.get_service("azure-gpt4o-mini")
    historico = ChatHistory()
    historico.add_system_message(
        "Você é um assistente de SRE. Use as funções InfraPlugin e RunbookPlugin "
        "para fundamentar a resposta e cite as fontes dos runbooks."
    )
    historico.add_user_message(pergunta)

    resposta = await service.get_chat_message_content(
        chat_history=historico, settings=settings, kernel=kernel
    )
    return str(resposta)


def main() -> None:  # pragma: no cover
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except Exception:  # pragma: no cover
        pass

    pergunta = sys.argv[1] if len(sys.argv) > 1 else PERGUNTA_PADRAO
    print(f"Pergunta: {pergunta}\n")
    print("SK planner → seleciona search_runbook + compare_services …\n")
    try:
        resposta = asyncio.run(_executar(pergunta))
    except Exception as exc:  # noqa: BLE001
        print(
            "[erro] Semantic Kernel não pôde rodar "
            f"({str(exc)[:160]}).\n"
            "Confira o .env (Azure OpenAI) e 'pip install semantic-kernel'.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("=" * 70)
    print(resposta)
    print("=" * 70)


if __name__ == "__main__":
    main()
