from datetime import datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone

from atendimento.models import (
    Atendimento,
    ConfiguracaoAgenda,
    Folga,
    HorarioSemana,
    Status,
)

NOMES_DIAS = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]

DIAS_PADRAO = {
    0: (True, time(8, 0), time(18, 0)),
    1: (True, time(8, 0), time(18, 0)),
    2: (True, time(8, 0), time(18, 0)),
    3: (True, time(8, 0), time(18, 0)),
    4: (True, time(8, 0), time(18, 0)),
    5: (True, time(8, 0), time(12, 0)),
    6: (False, time(8, 0), time(12, 0)),
}

JANELA_PUBLICA_DIAS = 90


def garantir_configuracao():
    config, _ = ConfiguracaoAgenda.objects.get_or_create(
        pk=1,
        defaults={"slot_minutos": 120, "capacidade": 1},
    )
    for dia, (aberto, inicio, fim) in DIAS_PADRAO.items():
        HorarioSemana.objects.get_or_create(
            configuracao=config,
            dia_semana=dia,
            defaults={"aberto": aberto, "inicio": inicio, "fim": fim},
        )
    return config


def adicionar_minutos(horario, minutos):
    base = datetime.combine(datetime.today().date(), horario) + timedelta(minutes=int(minutos))
    return base.time().replace(second=0, microsecond=0)


def rotulo_slot(inicio, minutos):
    fim = adicionar_minutos(inicio, minutos)
    return f"{inicio.strftime('%H:%M')}–{fim.strftime('%H:%M')}"


def _agora_local(agora):
    if agora is None:
        return timezone.localtime()
    if timezone.is_aware(agora):
        return timezone.localtime(agora)
    return agora


def dia_esta_aberto(data):
    garantir_configuracao()
    if Folga.objects.filter(data=data).exists():
        return False
    return HorarioSemana.objects.filter(dia_semana=data.weekday(), aberto=True).exists()


def situacao_dia(
    data,
    *,
    agora=None,
    excluir_id=None,
    permitir_passado=False,
    janela_dias=JANELA_PUBLICA_DIAS,
    janela_passado=0,
):
    if data is None:
        return _vazio("invalida", "Informe uma data válida.")

    agora = _agora_local(agora)
    hoje = agora.date()

    if not permitir_passado and data < hoje:
        return _vazio("passado", "Escolha hoje ou uma data futura.")
    if permitir_passado and data < hoje - timedelta(days=janela_passado):
        return _vazio("fora", "Essa data está fora da janela da agenda.")
    if data > hoje + timedelta(days=janela_dias):
        return _vazio("fora", "Só mostramos horários dentro da janela de agendamento.")

    config = garantir_configuracao()
    if Folga.objects.filter(data=data).exists():
        return _vazio("folga", "Essa data está fechada na agenda.")

    grade = config.dias.filter(dia_semana=data.weekday()).first()
    if grade is None or not grade.aberto:
        return _vazio("fechado", "Não atendemos nesse dia da semana.")

    slots = _slots_livres(
        data,
        grade,
        config,
        agora=agora,
        excluir_id=excluir_id,
        permitir_passado=permitir_passado,
    )
    if not slots:
        return _vazio("lotado", "Não há horários livres nessa data.")
    return {"slots": slots, "motivo": "ok", "mensagem": ""}


def horarios_livres(data, **kwargs):
    return situacao_dia(data, **kwargs)["slots"]


def slot_disponivel(data, horario, **kwargs):
    if horario is None or data is None:
        return False
    horario = horario.replace(second=0, microsecond=0)
    return any(slot.replace(second=0, microsecond=0) == horario for slot in horarios_livres(data, **kwargs))


def _vazio(motivo, mensagem):
    return {"slots": [], "motivo": motivo, "mensagem": mensagem}


def _slots_livres(data, grade, config, *, agora, excluir_id, permitir_passado):
    consulta = Atendimento.objects.filter(data=data).exclude(status=Status.CANCELADO)
    if excluir_id:
        consulta = consulta.exclude(pk=excluir_id)
    ocupacao = {
        linha["horario"].replace(second=0, microsecond=0): linha["total"]
        for linha in consulta.values("horario").annotate(total=Count("id"))
    }

    passo = timedelta(minutes=config.slot_minutos)
    cursor = datetime.combine(data, grade.inicio)
    limite = datetime.combine(data, grade.fim)
    livres = []
    while cursor + passo <= limite:
        horario = cursor.time().replace(second=0, microsecond=0)
        passou = (
            not permitir_passado
            and data == agora.date()
            and horario <= agora.time().replace(second=0, microsecond=0)
        )
        if not passou and ocupacao.get(horario, 0) < config.capacidade:
            livres.append(horario)
        cursor += passo
    return livres
