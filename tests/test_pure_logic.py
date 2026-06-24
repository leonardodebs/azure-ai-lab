"""Testes de caminhos puros (sem nuvem): stubs, render e helpers.

Exercita as ramificações que NÃO chamam Azure/AWS/GCP — modo stub, fallback de
tabela, impressão de fontes e validações de credenciais — para garantir que a
lógica de orquestração e resiliência está coberta.
"""
import compare_models as cm
import three_clouds_rag_comparison as tc
import azure_rag
import azure_content_safety as cs
import setup_check as sc


# ---------------------------------------------------------------------------
# compare_models — _executar (real vs stub) e _render_tabela
# ---------------------------------------------------------------------------
def test_executar_caminho_real_monta_registro():
    def fake(_prompt):
        return {"texto": "nat internet gateway privada saída público",
                "latencia_ms": 12.3, "tokens_in": 10, "tokens_out": 20}
    reg = cm._executar("gpt-4o-mini", fake, "p", cm.ESPERADO[0])
    assert reg["modo"] == "real"
    assert reg["tokens_total"] == 30
    assert reg["custo_usd"] == cm._custo("gpt-4o-mini", 10, 20)
    assert reg["qualidade"] == 5


def test_executar_caminho_stub_quando_funcao_falha():
    def quebra(_prompt):
        raise RuntimeError("sem credencial")
    reg = cm._executar("gpt-4o-mini", quebra, "p", cm.ESPERADO[0])
    assert reg["modo"] == "stub"
    assert reg["custo_usd"] is None
    assert "sem credencial" in reg["erro"]


def test_render_tabela_nao_quebra(capsys):
    resultados = [{
        "prompt": "Explique NAT vs IGW",
        "modelos": [
            {"modelo": "gpt-4o-mini", "modo": "real", "latencia_ms": 10.0,
             "tokens_total": 30, "custo_usd": 0.0001, "qualidade": 5},
            {"modelo": "claude-3-haiku", "modo": "stub", "latencia_ms": None,
             "tokens_total": None, "custo_usd": None, "qualidade": None},
        ],
    }]
    cm._render_tabela(resultados)
    assert "gpt-4o-mini" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# three_clouds — backends sem credencial e _exec → stub
# ---------------------------------------------------------------------------
def test_rodar_aws_sem_credencial(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    import pytest
    with pytest.raises(Exception):
        tc.rodar_aws("q")


def test_rodar_gcp_sem_projeto(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    import pytest
    with pytest.raises(Exception):
        tc.rodar_gcp("q")


def test_exec_envolve_excecao_em_stub():
    def quebra(_p):
        raise RuntimeError("boom")
    r = tc._exec(quebra, "q")
    assert r["modo"] == "stub"
    assert r["latencia_ms"] is None
    assert "boom" in r["resposta"]


# ---------------------------------------------------------------------------
# azure_rag — impressão de fontes
# ---------------------------------------------------------------------------
def test_imprimir_mostra_resposta_e_fontes(capsys):
    saida = {
        "resposta": "Reinicie o target e cheque o health check.",
        "fontes": [{"file": "alb-502-errors.md", "score": 0.91}],
    }
    azure_rag._imprimir(saida)
    out = capsys.readouterr().out
    assert "health check" in out and "alb-502-errors.md" in out


# ---------------------------------------------------------------------------
# content_safety — render do fallback de tabela
# ---------------------------------------------------------------------------
def test_render_content_safety(capsys):
    linhas = [(1, "texto exemplo…", 0, 2, 0, 0, "⚠️ sim")]
    cs._render(linhas)
    assert "exemplo" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# setup_check — _run sucesso, _ok/_falha
# ---------------------------------------------------------------------------
def test_run_comando_de_sucesso():
    rc, out = sc._run(["python3", "-c", "print('ok')"])
    assert rc == 0 and "ok" in out


def test_ok_e_falha_imprimem(capsys):
    sc._ok("tudo certo")
    sc._falha("algo errado", "rode X")
    out = capsys.readouterr().out
    assert "✅" in out and "❌" in out and "rode X" in out


# ---------------------------------------------------------------------------
# semantic_kernel_demo — constantes e plugins (skip se a lib não instalada)
# ---------------------------------------------------------------------------
def test_sk_constantes():
    import semantic_kernel_demo as skd

    assert "ecs" in skd.SERVICOS and "aks" in skd.SERVICOS
    assert skd.PERGUNTA_PADRAO


def test_sk_plugins_explain_e_compare():
    import pytest

    skd = pytest.importorskip("semantic_kernel_demo")
    pytest.importorskip("semantic_kernel")  # plugins dependem do decorator
    infra, runbook = skd._build_plugins()
    assert "ECS" in infra.explain_service("ecs")
    assert "desconhecido" not in infra.compare_services("ecs", "aks")
    # retriever indisponível (sem .env) deve degradar com mensagem, não quebrar
    assert isinstance(runbook.search_runbook("rollback"), str)
