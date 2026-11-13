from datetime import time, timedelta

from django.utils import timezone

from atendimento.models import Origem, Servico, Status, TipoCliente
from atendimento.services import registrar


def proximo_dia(weekday):
    hoje = timezone.localdate()
    dias = (weekday - hoje.weekday()) % 7
    if dias == 0:
        dias = 7
    return hoje + timedelta(days=dias)


def proxima_segunda():
    return proximo_dia(0)


def segunda_passada():
    return proxima_segunda() - timedelta(days=14)


def marcar(**kwargs):
    dados = {
        "nome": "Marina Albuquerque",
        "telefone": "83991110022",
        "tipo_cliente": TipoCliente.RESIDENCIA,
        "logradouro": "Av. Rui Carneiro, 450",
        "bairro": "Tambaú",
        "cidade": "João Pessoa",
        "servico": Servico.LIMPEZA,
        "quantidade": 2,
        "observacoes": "Apto 302",
        "data": proxima_segunda(),
        "horario": time(8, 0),
        "origem": Origem.SITE,
        "status": Status.RECEBIDO,
    }
    dados.update(kwargs)
    return registrar(**dados)


def payload(**kwargs):
    dados = {
        "acao": "agendar",
        "servico": "limpeza",
        "tipo_cliente": "residencia",
        "nome": "Marina Albuquerque",
        "telefone": "(83) 99111-0022",
        "logradouro": "Av. Rui Carneiro, 450",
        "bairro": "Tambaú",
        "cidade": "João Pessoa",
        "quantidade": "2",
        "observacoes": "Apto 302",
        "data": proxima_segunda().isoformat(),
        "horario": "08:00",
    }
    dados.update(kwargs)
    return dados
