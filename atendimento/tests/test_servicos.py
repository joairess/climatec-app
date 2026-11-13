from datetime import time

import pytest

from atendimento.models import Atendimento, Cliente, Endereco, Status
from atendimento.services import (
    HorarioIndisponivel,
    StatusBloqueado,
    alterar_status,
    registrar,
    remarcar,
)
from atendimento.tests.helpers import marcar, proxima_segunda

pytestmark = pytest.mark.django_db


def test_telefone_reune_cliente_e_endereco():
    segunda = proxima_segunda()
    primeiro = marcar(
        data=segunda,
        horario=time(8, 0),
        telefone="83991110022",
        nome="Marina Albuquerque",
        logradouro="Av. Rui Carneiro, 450",
        bairro="Tambaú",
    )
    segundo = registrar(
        nome="Marina A. Albuquerque",
        telefone="(83) 99111-0022",
        tipo_cliente="residencia",
        logradouro="av. rui carneiro, 450",
        bairro=" tambaú ",
        cidade="João Pessoa",
        servico="manutencao",
        quantidade=1,
        observacoes="",
        data=segunda,
        horario=time(10, 0),
    )
    terceiro = registrar(
        nome="Marina Albuquerque",
        telefone="83991110022",
        tipo_cliente="residencia",
        logradouro="Rua das Flores, 10",
        bairro="Bessa",
        cidade="João Pessoa",
        servico="limpeza",
        quantidade=1,
        observacoes="Casa da mãe",
        data=segunda,
        horario=time(14, 0),
    )
    assert Cliente.objects.count() == 1
    cliente = Cliente.objects.get()
    assert cliente.nome == "Marina Albuquerque"
    assert cliente.pk == primeiro.cliente_id == segundo.cliente_id == terceiro.cliente_id
    assert Endereco.objects.filter(cliente=cliente).count() == 2
    assert segundo.endereco_id == primeiro.endereco_id
    assert terceiro.endereco_id != primeiro.endereco_id


def test_codigo_unico_e_primeiro_nome():
    item = marcar()
    assert item.codigo.startswith("CLM-")
    assert item.cliente.primeiro_nome == "Marina"
    assert Atendimento.objects.filter(codigo=item.codigo).count() == 1


def test_remarcar_e_bloquear_concluido():
    segunda = proxima_segunda()
    item = marcar(data=segunda, horario=time(8, 0))
    remarcar(item, segunda, time(10, 0))
    item.refresh_from_db()
    assert item.status == Status.REMARCADO
    assert item.horario == time(10, 0)
    assert time(8, 0) in horarios(segunda)

    alterar_status(item, Status.CONCLUIDO)
    item.refresh_from_db()
    assert not item.pode_alterar
    with pytest.raises(StatusBloqueado):
        remarcar(item, segunda, time(14, 0))


def test_slot_cheio_recusa_registro():
    segunda = proxima_segunda()
    marcar(data=segunda, horario=time(8, 0))
    with pytest.raises(HorarioIndisponivel):
        marcar(data=segunda, horario=time(8, 0), telefone="83990001122", nome="Outra Pessoa")


def horarios(data):
    from atendimento.slots import horarios_livres

    return horarios_livres(data)
