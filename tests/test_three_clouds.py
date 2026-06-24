"""Testes da lógica determinística de three_clouds_rag_comparison."""
import three_clouds_rag_comparison as tc


def test_cinco_perguntas():
    assert len(tc.PERGUNTAS) == 5


def test_resumo_trunca_texto_longo():
    texto = "palavra " * 100
    r = tc._resumo(texto, limite=50)
    assert len(r) <= 51 and r.endswith("…")


def test_resumo_de_vazio():
    assert tc._resumo("") == "—"


def test_markdown_contem_secoes_e_matriz():
    linhas = [
        {
            "pergunta": p,
            "aws": {"modo": "stub", "latencia_ms": None, "resposta": "(stub)"},
            "gcp": {"modo": "stub", "latencia_ms": None, "resposta": "(stub)"},
            "azure": {"modo": "real", "latencia_ms": 120.0, "resposta": "resposta azure"},
        }
        for p in tc.PERGUNTAS
    ]
    md = tc.gerar_markdown(linhas)
    assert "Matriz de recomendação" in md
    assert "AWS" in md and "GCP" in md and "Azure" in md
    assert "| # | Pergunta |" in md
