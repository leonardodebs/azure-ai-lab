"""Testes da lógica determinística de azure_rag (chunking e config).

Não há chamadas a Azure: os clients são importados dentro das funções, então
exercitamos apenas o chunking dos runbooks e a montagem de configuração.
"""
import azure_rag


def test_carregar_chunks_le_os_cinco_runbooks():
    chunks = azure_rag.carregar_chunks()
    arquivos = {c["file"] for c in chunks}
    assert len(arquivos) == 5
    assert "alb-502-errors.md" in arquivos


def test_chunks_tem_id_unico_file_e_texto():
    chunks = azure_rag.carregar_chunks()
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))  # ids únicos
    for c in chunks:
        assert c["text"] and c["file"] and c["id"]


def test_chunks_respeitam_tamanho_minimo():
    for c in azure_rag.carregar_chunks():
        assert len(c["text"]) >= 40


def test_dims_do_embedding_ada002():
    assert azure_rag.EMBED_DIMS == 1536


def test_config_usa_defaults(monkeypatch):
    for var in [
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "AZURE_OPENAI_EMBED_DEPLOYMENT",
        "AZURE_SEARCH_INDEX",
    ]:
        monkeypatch.delenv(var, raising=False)
    cfg = azure_rag._config()
    assert cfg["chat_deploy"] == "gpt-4o-mini"
    assert cfg["embed_deploy"] == "text-embedding-ada-002"
    assert cfg["search_index"] == "runbooks-index"
