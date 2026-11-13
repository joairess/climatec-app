import pytest

from atendimento.codigos import gerar_codigo, normalizar_codigo
from atendimento.phones import formatar_telefone, normalizar_telefone, telefone_valido


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("(83) 98855-2060", "83988552060"),
        ("+55 83 98855-2060", "83988552060"),
        ("083988552060", "83988552060"),
        ("558332210628", "8332210628"),
        ("83988552060", "83988552060"),
    ],
)
def test_normaliza_telefone(bruto, esperado):
    assert normalizar_telefone(bruto) == esperado


def test_rejeita_telefone_curto():
    assert not telefone_valido(normalizar_telefone("98855-2060"))
    assert telefone_valido("83988552060")
    assert telefone_valido("8332210628")


def test_formata_telefone():
    assert formatar_telefone("83988552060") == "(83) 98855-2060"
    assert formatar_telefone("8332210628") == "(83) 3221-0628"


def test_codigo_tem_prefixo_e_normaliza():
    codigo = gerar_codigo()
    assert codigo.startswith("CLM-")
    assert normalizar_codigo(codigo.lower()) == codigo
    assert normalizar_codigo("abc") == ""
