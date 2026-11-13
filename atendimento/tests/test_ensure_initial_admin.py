from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

pytestmark = pytest.mark.django_db

USERNAME = "equipe"
PASSWORD = "senha-inicial-segura"
EMAIL = "equipe@climatec.example"


def _definir_ambiente(monkeypatch, username=USERNAME, password=PASSWORD, email=EMAIL):
    for chave, valor in (
        ("DJANGO_SUPERUSER_USERNAME", username),
        ("DJANGO_SUPERUSER_PASSWORD", password),
        ("DJANGO_SUPERUSER_EMAIL", email),
    ):
        if valor is None:
            monkeypatch.delenv(chave, raising=False)
        else:
            monkeypatch.setenv(chave, valor)


def _executar():
    saida = StringIO()
    call_command("ensure_initial_admin", stdout=saida)
    return saida.getvalue()


@pytest.mark.parametrize(
    ("username", "password"),
    [
        (None, None),
        ("", PASSWORD),
        (USERNAME, ""),
        ("   ", PASSWORD),
        (USERNAME, "   "),
        (None, PASSWORD),
        (USERNAME, None),
    ],
)
def test_variaveis_ausentes_ou_em_branco_nao_criam_usuario(monkeypatch, username, password):
    _definir_ambiente(monkeypatch, username=username, password=password, email=None)

    saida = _executar()

    assert get_user_model().objects.count() == 0
    assert PASSWORD not in saida


def test_variaveis_validas_criam_superusuario(monkeypatch):
    _definir_ambiente(monkeypatch)

    saida = _executar()

    usuario = get_user_model().objects.get(username=USERNAME)
    assert usuario.is_staff is True
    assert usuario.is_superuser is True
    assert usuario.email == EMAIL
    assert usuario.check_password(PASSWORD)
    assert PASSWORD not in saida
    assert "criado" in saida


def test_email_opcional(monkeypatch):
    _definir_ambiente(monkeypatch, email=None)

    _executar()

    usuario = get_user_model().objects.get(username=USERNAME)
    assert usuario.email == ""
    assert usuario.is_staff is True
    assert usuario.is_superuser is True


def test_segunda_execucao_nao_falha_nem_redefine_senha(monkeypatch):
    _definir_ambiente(monkeypatch)
    _executar()
    usuario = get_user_model().objects.get(username=USERNAME)
    usuario.set_password("senha-trocada-depois")
    usuario.save(update_fields=["password"])

    saida = _executar()

    usuario.refresh_from_db()
    assert get_user_model().objects.count() == 1
    assert usuario.check_password("senha-trocada-depois")
    assert not usuario.check_password(PASSWORD)
    assert PASSWORD not in saida
    assert "senha-trocada-depois" not in saida
