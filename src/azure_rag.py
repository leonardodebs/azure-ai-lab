"""
azure_rag.py — RAG com Azure AI Search + GPT-4o-mini.

Equivalente AWS: Amazon Bedrock Knowledge Bases (ingestão + vetor + retrieve).
Aqui montamos o pipeline explicitamente para evidenciar cada etapa:

    Indexação (--index, roda uma vez):
        1. Carrega os 5 runbooks de data/runbooks.
        2. Quebra em chunks por parágrafo.
        3. Gera embeddings com text-embedding-ada-002 (1536 dims).
        4. Cria/atualiza o índice no Azure AI Search com campo vetorial (HNSW).
        5. Faz upload dos documentos (chunk + vetor).

    Consulta (texto da pergunta):
        1. Embeda a pergunta (ada-002).
        2. Vector search top 3 no Azure AI Search.
        3. GPT-4o-mini gera a resposta ancorada, citando as fontes.

Comparação com Bedrock Knowledge Bases: lá a ingestão e o vetor (OpenSearch
Serverless) são gerenciados de ponta a ponta; aqui controlamos chunking, schema
do índice e a query — mais código, porém total transparência e portabilidade.

Uso:
    python src/azure_rag.py --index                       # cria o índice (uma vez)
    python src/azure_rag.py "Como resolver erro 502 no ALB?"
    python src/azure_rag.py --interactive
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUNBOOKS = RAIZ / "data" / "runbooks"

EMBED_DIMS = 1536  # text-embedding-ada-002 sempre retorna 1536 dimensões.
TOP_K = 3


def _config() -> dict:
    """Lê configuração do .env / ambiente. Carrega .env se python-dotenv existir."""
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except Exception:  # pragma: no cover
        pass
    return {
        "oai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "oai_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "oai_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        "chat_deploy": os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"),
        "embed_deploy": os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-ada-002"),
        "search_endpoint": os.getenv("AZURE_SEARCH_ENDPOINT", ""),
        "search_key": os.getenv("AZURE_SEARCH_API_KEY", ""),
        "search_index": os.getenv("AZURE_SEARCH_INDEX", "runbooks-index"),
    }


# ---------------------------------------------------------------------------
# Chunking — lógica pura, testável sem nuvem
# ---------------------------------------------------------------------------
def carregar_chunks() -> list[dict]:
    """Lê os runbooks .md e os divide em chunks por parágrafo (>= 40 chars)."""
    chunks = []
    for arquivo in sorted(RUNBOOKS.glob("*.md")):
        texto = arquivo.read_text(encoding="utf-8")
        for i, bloco in enumerate(re.split(r"\n\s*\n", texto)):
            bloco = bloco.strip()
            if len(bloco) >= 40:
                chunks.append(
                    {"id": f"{arquivo.stem}-{i}", "file": arquivo.name, "text": bloco}
                )
    return chunks


# ---------------------------------------------------------------------------
# Embeddings (Azure OpenAI ada-002)
# ---------------------------------------------------------------------------
def _client_openai(cfg: dict):
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=cfg["oai_endpoint"],
        api_key=cfg["oai_key"],
        api_version=cfg["oai_version"],
    )


def embeddings(cfg: dict, textos: list[str]) -> list[list[float]]:
    """Gera embeddings em lote (ada-002, 1536 dims)."""
    client = _client_openai(cfg)
    vetores: list[list[float]] = []
    # A API aceita lotes; quebramos de 16 em 16 para respeitar limites de payload.
    for i in range(0, len(textos), 16):
        lote = textos[i : i + 16]
        resp = client.embeddings.create(model=cfg["embed_deploy"], input=lote)
        vetores.extend([d.embedding for d in resp.data])
    return vetores


# ---------------------------------------------------------------------------
# Azure AI Search — criação do índice e upload (campo vetorial HNSW)
# ---------------------------------------------------------------------------
def _index_client(cfg: dict):
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient

    return SearchIndexClient(cfg["search_endpoint"], AzureKeyCredential(cfg["search_key"]))


def _search_client(cfg: dict):
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    return SearchClient(
        cfg["search_endpoint"], cfg["search_index"], AzureKeyCredential(cfg["search_key"])
    )


def criar_indice(cfg: dict) -> None:
    """Cria (ou recria) o índice com campo vetorial e perfil HNSW."""
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchableField,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )

    campos = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="file", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SearchField(
            name="vetor",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBED_DIMS,
            vector_search_profile_name="perfil-hnsw",
        ),
    ]
    vetor = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="config-hnsw")],
        profiles=[
            VectorSearchProfile(name="perfil-hnsw", algorithm_configuration_name="config-hnsw")
        ],
    )
    indice = SearchIndex(name=cfg["search_index"], fields=campos, vector_search=vetor)
    client = _index_client(cfg)
    client.create_or_update_index(indice)


def indexar(cfg: dict) -> int:
    """Pipeline completo de indexação. Retorna o nº de documentos enviados."""
    chunks = carregar_chunks()
    print(f"Runbooks: {len(set(c['file'] for c in chunks))} arquivos, {len(chunks)} chunks.")
    criar_indice(cfg)
    print(f"Índice '{cfg['search_index']}' criado/atualizado (HNSW, {EMBED_DIMS} dims).")
    vetores = embeddings(cfg, [c["text"] for c in chunks])
    docs = [
        {"id": c["id"], "file": c["file"], "text": c["text"], "vetor": v}
        for c, v in zip(chunks, vetores)
    ]
    _search_client(cfg).upload_documents(documents=docs)
    print(f"Upload concluído: {len(docs)} documentos no Azure AI Search.")
    return len(docs)


# ---------------------------------------------------------------------------
# Consulta — vector search + geração
# ---------------------------------------------------------------------------
def buscar(cfg: dict, pergunta: str, top_k: int = TOP_K) -> list[dict]:
    """Embeda a pergunta e faz vector search top_k no Azure AI Search."""
    from azure.search.documents.models import VectorizedQuery

    q_vec = embeddings(cfg, [pergunta])[0]
    vq = VectorizedQuery(vector=q_vec, k_nearest_neighbors=top_k, fields="vetor")
    resultados = _search_client(cfg).search(
        search_text=None, vector_queries=[vq], select=["file", "text"], top=top_k
    )
    return [
        {"file": r["file"], "text": r["text"], "score": r.get("@search.score", 0.0)}
        for r in resultados
    ]


def gerar_resposta(cfg: dict, pergunta: str, contextos: list[dict]) -> str:
    """Gera a resposta final com GPT-4o-mini, ancorada nos contextos recuperados."""
    client = _client_openai(cfg)
    blocos = "\n\n".join(f"[{c['file']}]\n{c['text']}" for c in contextos)
    sistema = (
        "Você é um assistente de SRE. Responda usando APENAS o contexto dos runbooks. "
        "Cite os arquivos usados entre colchetes. Se a resposta não estiver no "
        "contexto, diga isso claramente."
    )
    usuario = f"=== CONTEXTO ===\n{blocos}\n\n=== PERGUNTA ===\n{pergunta}"
    resp = client.chat.completions.create(
        model=cfg["chat_deploy"],
        messages=[
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        max_tokens=800,
    )
    return resp.choices[0].message.content or ""


def responder(cfg: dict, pergunta: str, top_k: int = TOP_K) -> dict:
    """Orquestra busca + geração. Reutilizado pelo Semantic Kernel (RunbookPlugin)."""
    fontes = buscar(cfg, pergunta, top_k)
    resposta = gerar_resposta(cfg, pergunta, fontes)
    return {"pergunta": pergunta, "resposta": resposta, "fontes": fontes}


def _imprimir(saida: dict) -> None:
    print("=" * 70)
    print(saida["resposta"])
    print("=" * 70)
    print("\nFontes consultadas:")
    for f in saida["fontes"]:
        print(f"  - {f['file']:<24} relevância={f['score']:.4f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG com Azure AI Search + GPT-4o-mini")
    ap.add_argument("pergunta", nargs="?", help="pergunta em linguagem natural")
    ap.add_argument("--index", action="store_true", help="cria o índice e indexa os runbooks")
    ap.add_argument("--interactive", action="store_true", help="modo interativo (loop)")
    ap.add_argument("--top-k", type=int, default=TOP_K, help="nº de chunks a recuperar")
    args = ap.parse_args()

    cfg = _config()

    try:
        if args.index:
            indexar(cfg)
            return
        if args.interactive:
            print("Modo interativo. Digite 'sair' para encerrar.\n")
            while True:
                try:
                    pergunta = input("pergunta> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if pergunta.lower() in {"sair", "exit", "quit", ""}:
                    break
                _imprimir(responder(cfg, pergunta, args.top_k))
                print()
            return
        if not args.pergunta:
            ap.error("informe uma pergunta, ou use --index / --interactive")
        _imprimir(responder(cfg, args.pergunta, args.top_k))
    except Exception as exc:  # noqa: BLE001
        print(
            "\n[erro] Falha ao falar com Azure OpenAI / AI Search "
            f"({str(exc)[:160]}).\n"
            "Verifique o .env (endpoints/chaves) e rode 'python src/azure_rag.py --index' "
            "antes de consultar.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
