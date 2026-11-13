from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from atendimento.models import ConfiguracaoAgenda, Folga, HorarioSemana, Status
from atendimento.slots import horarios_livres, situacao_dia
from atendimento.tests.helpers import marcar, proxima_segunda, proximo_dia, segunda_passada

pytestmark = pytest.mark.django_db


def test_segunda_tem_grade_e_domingo_nao():
    segunda = proxima_segunda()
    domingo = proximo_dia(6)
    assert time(8, 0) in horarios_livres(segunda)
    assert time(16, 0) in horarios_livres(segunda)
    assert horarios_livres(domingo) == []
    assert situacao_dia(domingo)["motivo"] == "fechado"


def test_sabado_so_de_manha():
    sabado = proximo_dia(5)
    slots = horarios_livres(sabado)
    assert time(8, 0) in slots
    assert time(10, 0) in slots
    assert time(14, 0) not in slots


def test_capacidade_e_cancelamento_liberam_vaga():
    segunda = proxima_segunda()
    ocupado = marcar(data=segunda, horario=time(8, 0))
    assert time(8, 0) not in horarios_livres(segunda)
    assert time(10, 0) in horarios_livres(segunda)

    config = ConfiguracaoAgenda.objects.get(pk=1)
    config.capacidade = 2
    config.save()
    assert time(8, 0) in horarios_livres(segunda)

    config.capacidade = 1
    config.save()
    ocupado.status = Status.CANCELADO
    ocupado.save(update_fields=["status"])
    assert time(8, 0) in horarios_livres(segunda)


def test_remarcar_nao_conta_o_proprio_horario():
    segunda = proxima_segunda()
    item = marcar(data=segunda, horario=time(8, 0))
    assert time(8, 0) not in horarios_livres(segunda)
    assert time(8, 0) in horarios_livres(segunda, excluir_id=item.pk)


def test_horarios_passados_somem_para_o_publico():
    segunda = proxima_segunda()
    agora = timezone.make_aware(datetime.combine(segunda, time(11, 0)))
    slots = horarios_livres(segunda, agora=agora)
    assert time(8, 0) not in slots
    assert time(10, 0) not in slots
    assert time(12, 0) in slots
    assert time(8, 0) in horarios_livres(segunda, agora=agora, permitir_passado=True)


def test_folga_fecha_o_dia():
    segunda = proxima_segunda()
    Folga.objects.create(data=segunda, motivo="Feriado")
    assert horarios_livres(segunda) == []
    assert situacao_dia(segunda)["motivo"] == "folga"


def test_janela_publica_nao_passa_de_90_dias():
    alvo = proxima_segunda() + timedelta(days=98)
    assert horarios_livres(alvo) == []
    assert time(8, 0) in horarios_livres(
        alvo, permitir_passado=True, janela_dias=180, janela_passado=1
    )


def test_data_passada_fica_oculta_no_publico():
    assert horarios_livres(segunda_passada()) == []
    assert time(8, 0) in horarios_livres(
        segunda_passada(), permitir_passado=True, janela_passado=30
    )


def test_grade_curta_nao_gera_horario():
    sexta = proximo_dia(4)
    HorarioSemana.objects.filter(dia_semana=4).update(inicio=time(8, 0), fim=time(9, 0))
    assert horarios_livres(sexta) == []
