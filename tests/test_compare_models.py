"""Testes da lógica determinística de compare_models (qualidade e custo)."""
import compare_models as cm


# ----- Heurística de qualidade (1-5) -----

def test_qualidade_resposta_vazia():
    assert cm._qualidade("", ["nat", "internet gateway"]) == 1


def test_qualidade_cobertura_total():
    esperado = ["nat", "internet gateway", "privada"]
    resposta = "O NAT permite saída de subrede privada; o Internet Gateway é público."
    assert cm._qualidade(resposta, esperado) == 5


def test_qualidade_case_insensitive():
    nota = cm._qualidade("RTO e RPO definem recuperação", ["rto", "rpo", "recuperação"])
    assert nota == 5


def test_qualidade_dentro_do_intervalo():
    esperado = ["a", "b", "c", "d"]
    for resposta in ["", "a", "a b", "a b c", "a b c d", "nada disso"]:
        assert 1 <= cm._qualidade(resposta, esperado) <= 5


# ----- Cálculo de custo -----

def test_custo_gpt4o_mini_por_milhao():
    """1M in + 1M out do GPT-4o-mini = 0,15 + 0,60."""
    custo = cm._custo("gpt-4o-mini", 1_000_000, 1_000_000)
    assert round(custo, 4) == round(0.15 + 0.60, 4)


def test_custo_haiku_mais_caro_que_gpt4o_mini():
    gpt = cm._custo("gpt-4o-mini", 500, 500)
    haiku = cm._custo("claude-3-haiku", 500, 500)
    assert haiku > gpt


def test_custo_gemini_mais_barato_na_entrada():
    gpt = cm._custo("gpt-4o-mini", 1_000_000, 0)
    gemini = cm._custo("gemini-1.5-flash", 1_000_000, 0)
    assert gemini < gpt


def test_custo_zero_tokens():
    assert cm._custo("gpt-4o-mini", 0, 0) == 0.0


# ----- Estrutura de constantes -----

def test_cinco_prompts_alinhados():
    assert len(cm.PROMPTS) == 5
    assert len(cm.ESPERADO) == len(cm.PROMPTS)


def test_precos_tem_tres_modelos():
    assert set(cm.PRECOS) == {"gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash"}
