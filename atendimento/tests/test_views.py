from datetime import time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from atendimento.models import Atendimento, Cliente, ConfiguracaoAgenda, Folga, Status
from atendimento.tests.helpers import marcar, payload, proxima_segunda, segunda_passada

pytestmark = pytest.mark.django_db


def test_saude(client):
    resposta = client.get(reverse("saude"))
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_home_mostra_contato_e_lgpd(client):
    resposta = client.get(reverse("home"))
    html = resposta.content.decode()
    assert resposta.status_code == 200
    assert "(83) 3221-0628" in html
    assert "https://wa.me/5583988552060" in html
    assert "LGPD" in html
    assert "Instalação" in html


def test_agendar_cria_pedido_e_esconde_dados_pessoais(client):
    resposta = client.post(reverse("home"), payload(), follow=True)
    assert resposta.status_code == 200
    item = Atendimento.objects.get()
    html = resposta.content.decode()
    assert item.codigo in html
    assert "Marina" in html
    assert "Albuquerque" not in html
    assert "Rui Carneiro" not in html
    assert "99111-0022" not in html
    assert "83991110022" not in html
    assert "Apto 302" not in html
    assert item.cliente.telefone == "83991110022"
    assert item.status == Status.RECEBIDO


def test_nao_deixa_ocupar_horario_cheio(client):
    client.post(reverse("home"), payload())
    resposta = client.post(
        reverse("home"),
        payload(nome="Paulo Lima", telefone="(83) 99000-1122"),
    )
    assert resposta.status_code == 200
    assert resposta.context["form"].errors
    assert Atendimento.objects.count() == 1


def test_status_desconhecido(client):
    resposta = client.get(reverse("acompanhar", args=["CLM-ZZZZZZ"]))
    assert resposta.status_code == 404
    assert "Não encontramos" in resposta.content.decode()


def test_busca_redireciona(client):
    item = marcar()
    resposta = client.get(reverse("acompanhar_busca"), {"codigo": item.codigo.lower()})
    assert resposta.status_code == 302
    assert item.codigo in resposta["Location"]


def test_horarios_json(client, owner):
    segunda = proxima_segunda()
    resposta = client.get(reverse("horarios"), {"data": segunda.isoformat()})
    assert "08:00" in [slot["value"] for slot in resposta.json()["slots"]]

    domingo = segunda + timedelta(days=6)
    fechado = client.get(reverse("horarios"), {"data": domingo.isoformat()})
    assert fechado.json()["slots"] == []
    assert fechado.json()["motivo"] == "fechado"

    invalida = client.get(reverse("horarios"), {"data": "amanha"})
    assert invalida.status_code == 400

    passado = client.get(
        reverse("horarios"),
        {"data": segunda_passada().isoformat(), "painel": "1"},
    )
    assert passado.json()["slots"] == []

    client.force_login(owner)
    liberado = client.get(
        reverse("horarios"),
        {"data": segunda_passada().isoformat(), "painel": "1"},
    )
    assert "08:00" in [slot["value"] for slot in liberado.json()["slots"]]


def test_painel_exige_login(client):
    resposta = client.get(reverse("painel"))
    assert resposta.status_code == 302
    assert "/entrar/" in resposta["Location"]
    item = marcar()
    bloqueado = client.post(reverse("pedido_detalhe", args=[item.pk]), {"acao": "confirmar"})
    assert bloqueado.status_code == 302
    item.refresh_from_db()
    assert item.status == Status.RECEBIDO


def test_login_e_agenda(client, owner):
    resposta = client.post(
        reverse("entrar"),
        {"username": "atendimento", "password": "climatec-demo"},
    )
    assert resposta.status_code == 302
    assert resposta["Location"].endswith("/painel/")
    segunda = proxima_segunda()
    marcar(data=segunda, horario=time(8, 0), nome="Marina Albuquerque")
    marcar(
        data=segunda,
        horario=time(10, 0),
        nome="Paulo Lima",
        telefone="83990001122",
        status=Status.CONFIRMADO,
    )
    dia = client.get(reverse("painel"), {"data": segunda.isoformat()})
    assert "Marina Albuquerque" in dia.content.decode()
    filtrado = client.get(
        reverse("painel"),
        {"data": segunda.isoformat(), "status": Status.RECEBIDO},
    )
    html = filtrado.content.decode()
    assert "Marina Albuquerque" in html
    assert "Paulo Lima" not in html
    semana = client.get(reverse("painel_semana"), {"data": segunda.isoformat()})
    assert semana.status_code == 200
    assert "Marina Albuquerque" in semana.content.decode()


def test_confirmar_cancelar_e_concluir(client, owner):
    client.force_login(owner)
    item = marcar(observacoes="<script>alert(1)</script>")
    detalhe = client.get(reverse("pedido_detalhe", args=[item.pk]))
    assert b"<script>alert" not in detalhe.content
    assert b"&lt;script&gt;" in detalhe.content
    assert "83991110022" in detalhe.content.decode() or "(83) 99111-0022" in detalhe.content.decode()

    client.post(reverse("pedido_detalhe", args=[item.pk]), {"acao": "confirmar"})
    item.refresh_from_db()
    assert item.status == Status.CONFIRMADO

    client.post(reverse("pedido_detalhe", args=[item.pk]), {"acao": "a_caminho"})
    item.refresh_from_db()
    assert item.status == Status.A_CAMINHO

    client.post(
        reverse("pedido_detalhe", args=[item.pk]),
        {"acao": "cancelar", "motivo": "Cliente desistiu"},
    )
    item.refresh_from_db()
    assert item.status == Status.CANCELADO
    assert item.motivo_cancelamento == "Cliente desistiu"
    publico = client.get(reverse("acompanhar", args=[item.codigo]))
    assert "Cancelado" in publico.content.decode()
    assert "Cliente desistiu" not in publico.content.decode()
    assert "Rui Carneiro" not in publico.content.decode()


def test_remarcar_pela_agenda(client, owner):
    client.force_login(owner)
    segunda = proxima_segunda()
    item = marcar(data=segunda, horario=time(8, 0))
    resposta = client.post(
        reverse("pedido_detalhe", args=[item.pk]),
        {"acao": "remarcar", "data": segunda.isoformat(), "horario": "14:00"},
    )
    assert resposta.status_code == 302
    item.refresh_from_db()
    assert item.status == Status.REMARCADO
    assert item.horario == time(14, 0)


def test_registro_manual(client, owner):
    client.force_login(owner)
    dados = payload(
        origem="telefone",
        status="confirmado",
        nome="Padaria São José",
        telefone="8332210099",
        tipo_cliente="empresa",
        horario="16:00",
    )
    resposta = client.post(reverse("pedido_novo"), dados)
    assert resposta.status_code == 302
    item = Atendimento.objects.get()
    assert item.origem == "telefone"
    assert item.status == Status.CONFIRMADO
    assert item.cliente.nome == "Padaria São José"


def test_historico_do_cliente(client, owner):
    client.force_login(owner)
    segunda = proxima_segunda()
    marcar(data=segunda, horario=time(8, 0), observacoes="Portaria secreta")
    registrar_outro = payload(
        horario="10:00",
        logradouro="Rua das Flores, 10",
        bairro="Bessa",
        observacoes="Casa da mãe",
    )
    client.post(reverse("home"), registrar_outro)
    assert Cliente.objects.count() == 1
    cliente = Cliente.objects.get()
    pagina = client.get(reverse("cliente_detalhe", args=[cliente.pk]))
    html = pagina.content.decode()
    assert "(83) 99111-0022" in html
    assert "Tambaú" in html
    assert "Bessa" in html
    assert "Portaria secreta" in html
    assert "Casa da mãe" in html


def test_configuracao_e_folga(client, owner):
    client.force_login(owner)
    config = ConfiguracaoAgenda.objects.get(pk=1)
    dados = {"slot_minutos": "60", "capacidade": "3"}
    for dia in config.dias.all():
        if dia.aberto:
            dados[f"aberto_{dia.dia_semana}"] = "on"
        dados[f"inicio_{dia.dia_semana}"] = dia.inicio.strftime("%H:%M")
        dados[f"fim_{dia.dia_semana}"] = dia.fim.strftime("%H:%M")
    resposta = client.post(reverse("configuracao"), dados)
    assert resposta.status_code == 302
    config.refresh_from_db()
    assert config.capacidade == 3
    assert config.slot_minutos == 60

    segunda = proxima_segunda()
    client.post(
        reverse("configuracao"),
        {"adicionar_folga": "1", "data_folga": segunda.isoformat(), "motivo_folga": "Feriado"},
    )
    assert Folga.objects.filter(data=segunda).exists()
    from atendimento.slots import horarios_livres

    assert horarios_livres(segunda) == []


def test_logout(client, owner):
    client.force_login(owner)
    resposta = client.post(reverse("sair"))
    assert resposta.status_code == 302
    assert client.get(reverse("painel")).status_code == 302


def test_privacidade(client):
    resposta = client.get(reverse("privacidade"))
    assert resposta.status_code == 200
    assert "LGPD" in resposta.content.decode()


def test_seed_demo(client):
    from django.core.management import call_command

    call_command("seed_demo")
    assert Atendimento.objects.filter(codigo="CLM-DEMO01").exists()
    assert Cliente.objects.filter(telefone="83991230044").get().enderecos.count() == 2
    total = Atendimento.objects.count()
    call_command("seed_demo")
    assert Atendimento.objects.count() == total
    assert client.login(username="atendimento", password="climatec-demo")
