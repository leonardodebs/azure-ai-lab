"""Testes da lógica determinística de azure_content_safety."""
import azure_content_safety as cs


class _Item:
    def __init__(self, category, severity):
        self.category = category
        self.severity = severity


class _Resp:
    def __init__(self, pares):
        self.categories_analysis = [_Item(c, s) for c, s in pares]


def test_dez_textos_de_exemplo():
    assert len(cs.TEXTOS) == 10


def test_extrai_categorias_da_resposta():
    resp = _Resp([("Hate", 0), ("Violence", 2), ("Sexual", 0), ("SelfHarm", 0)])
    sev = cs._categorias_de(resp)
    assert sev == {"Hate": 0, "Violence": 2, "Sexual": 0, "SelfHarm": 0}


def test_limiar_e_inteiro_no_intervalo_valido():
    assert isinstance(cs.LIMIAR, int)
    assert 0 <= cs.LIMIAR <= 6
