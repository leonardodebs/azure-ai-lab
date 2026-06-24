"""Testes da lógica determinística de setup_check (sem chamar a Azure CLI real)."""
import setup_check as sc


def test_lista_de_providers_exigidos():
    assert "Microsoft.CognitiveServices" in sc.PROVIDERS
    assert "Microsoft.MachineLearningServices" in sc.PROVIDERS


def test_run_comando_inexistente_retorna_127():
    rc, _ = sc._run(["comando-que-nao-existe-xyz"])
    assert rc == 127


def test_checar_openai_sem_credenciais(monkeypatch, capsys):
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    assert sc.checar_openai() is False
    assert "❌" in capsys.readouterr().out
