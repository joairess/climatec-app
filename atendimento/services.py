from django.db import transaction

from atendimento.empresa import CIDADE_PADRAO
from atendimento.models import Atendimento, Cliente, Endereco, Origem, Status
from atendimento.phones import normalizar_telefone
from atendimento.slots import slot_disponivel


class HorarioIndisponivel(Exception):
    pass


class StatusBloqueado(Exception):
    pass


def _chave(texto):
    return " ".join((texto or "").split()).casefold()


def upsert_cliente(nome, telefone):
    cliente, criado = Cliente.objects.get_or_create(
        telefone=telefone,
        defaults={"nome": nome},
    )
    if not criado and cliente.nome != nome:
        cliente.nome = nome
        cliente.save(update_fields=["nome", "atualizado_em"])
    return cliente


def upsert_endereco(cliente, tipo, logradouro, bairro, cidade):
    logradouro = " ".join(logradouro.split())
    bairro = " ".join(bairro.split())
    cidade = " ".join((cidade or "").split()) or CIDADE_PADRAO
    chave_logradouro = _chave(logradouro)
    chave_bairro = _chave(bairro)
    for endereco in cliente.enderecos.all():
        if _chave(endereco.logradouro) == chave_logradouro and _chave(endereco.bairro) == chave_bairro:
            campos = []
            if endereco.tipo != tipo:
                endereco.tipo = tipo
                campos.append("tipo")
            if endereco.cidade != cidade:
                endereco.cidade = cidade
                campos.append("cidade")
            if endereco.logradouro != logradouro:
                endereco.logradouro = logradouro
                campos.append("logradouro")
            if endereco.bairro != bairro:
                endereco.bairro = bairro
                campos.append("bairro")
            if campos:
                endereco.save(update_fields=campos)
            return endereco
    return Endereco.objects.create(
        cliente=cliente,
        tipo=tipo,
        logradouro=logradouro,
        bairro=bairro,
        cidade=cidade,
    )


def registrar(
    *,
    nome,
    telefone,
    tipo_cliente,
    logradouro,
    bairro,
    cidade,
    servico,
    quantidade,
    observacoes,
    data,
    horario,
    origem=Origem.SITE,
    status=Status.RECEBIDO,
    codigo=None,
    checar_horario=True,
    permitir_passado=False,
    janela_dias=90,
    janela_passado=0,
):
    horario = horario.replace(second=0, microsecond=0)
    telefone = normalizar_telefone(telefone)
    with transaction.atomic():
        if checar_horario and not slot_disponivel(
            data,
            horario,
            permitir_passado=permitir_passado,
            janela_dias=janela_dias,
            janela_passado=janela_passado,
        ):
            raise HorarioIndisponivel
        cliente = upsert_cliente(nome, telefone)
        endereco = upsert_endereco(cliente, tipo_cliente, logradouro, bairro, cidade)
        return Atendimento.objects.create(
            codigo=codigo or "",
            cliente=cliente,
            endereco=endereco,
            servico=servico,
            quantidade_aparelhos=quantidade,
            observacoes=(observacoes or "").strip(),
            data=data,
            horario=horario,
            status=status,
            origem=origem,
        )


def remarcar(atendimento, data, horario):
    if not atendimento.pode_alterar:
        raise StatusBloqueado
    horario = horario.replace(second=0, microsecond=0)
    if not slot_disponivel(data, horario, excluir_id=atendimento.pk):
        raise HorarioIndisponivel
    atendimento.data = data
    atendimento.horario = horario
    atendimento.status = Status.REMARCADO
    atendimento.save(update_fields=["data", "horario", "status", "atualizado_em"])
    return atendimento


def alterar_status(atendimento, novo_status, motivo=""):
    if not atendimento.pode_alterar:
        raise StatusBloqueado
    if novo_status not in {
        Status.CONFIRMADO,
        Status.A_CAMINHO,
        Status.CONCLUIDO,
        Status.CANCELADO,
    }:
        raise StatusBloqueado
    atendimento.status = novo_status
    campos = ["status", "atualizado_em"]
    if novo_status == Status.CANCELADO:
        atendimento.motivo_cancelamento = (motivo or "").strip()[:200]
        campos.append("motivo_cancelamento")
    atendimento.save(update_fields=campos)
    return atendimento
