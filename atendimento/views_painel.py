from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from atendimento.forms import (
    AgendamentoManualForm,
    RemarcarForm,
    anotar_acessibilidade,
)
from atendimento.models import Atendimento, Cliente, Folga, Status
from atendimento.phones import somente_digitos
from atendimento.services import StatusBloqueado, alterar_status
from atendimento.slots import (
    NOMES_DIAS,
    adicionar_minutos,
    dia_esta_aberto,
    garantir_configuracao,
    situacao_dia,
)


def _ler_data(request):
    bruto = request.GET.get("data")
    if not bruto:
        return timezone.localdate()
    try:
        return datetime.strptime(bruto, "%Y-%m-%d").date()
    except ValueError:
        return timezone.localdate()


def _ler_status(request):
    status = request.GET.get("status", "")
    if status not in Status.values:
        return ""
    return status


def _query(data, status):
    params = {"data": data.isoformat()}
    if status:
        params["status"] = status
    return urlencode(params)


def _anexar_fim(itens, minutos):
    for item in itens:
        item.fim = adicionar_minutos(item.horario, minutos)
    return itens


@login_required
def agenda(request):
    dia = _ler_data(request)
    status = _ler_status(request)
    qs = Atendimento.objects.select_related("cliente", "endereco").filter(data=dia)
    if status:
        qs = qs.filter(status=status)
    config = garantir_configuracao()
    itens = _anexar_fim(list(qs.order_by("horario", "id")), config.slot_minutos)
    hoje = timezone.localdate()
    return render(
        request,
        "painel/agenda.html",
        {
            "dia": dia,
            "status": status,
            "itens": itens,
            "hoje": hoje,
            "aberto": dia_esta_aberto(dia),
            "anterior": f"?{_query(dia - timedelta(days=1), status)}",
            "proximo": f"?{_query(dia + timedelta(days=1), status)}",
            "link_hoje": f"?{_query(hoje, status)}",
            "filtros": [("", "Todos"), *Status.choices],
            "vista": "dia",
        },
    )


@login_required
def semana(request):
    dia = _ler_data(request)
    status = _ler_status(request)
    inicio = dia - timedelta(days=dia.weekday())
    fim = inicio + timedelta(days=6)
    qs = Atendimento.objects.select_related("cliente", "endereco").filter(
        data__range=(inicio, fim)
    )
    if status:
        qs = qs.filter(status=status)
    config = garantir_configuracao()
    por_dia = {(inicio + timedelta(days=i)): [] for i in range(7)}
    for item in qs.order_by("data", "horario", "id"):
        item.fim = adicionar_minutos(item.horario, config.slot_minutos)
        por_dia[item.data].append(item)
    grupos = [
        {
            "data": inicio + timedelta(days=i),
            "itens": por_dia[inicio + timedelta(days=i)],
            "aberto": dia_esta_aberto(inicio + timedelta(days=i)),
        }
        for i in range(7)
    ]
    hoje = timezone.localdate()
    return render(
        request,
        "painel/semana.html",
        {
            "dia": dia,
            "inicio": inicio,
            "fim": fim,
            "status": status,
            "grupos": grupos,
            "hoje": hoje,
            "anterior": f"?{_query(dia - timedelta(days=7), status)}",
            "proximo": f"?{_query(dia + timedelta(days=7), status)}",
            "link_hoje": f"?{_query(hoje, status)}",
            "filtros": [("", "Todos"), *Status.choices],
            "vista": "semana",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def pedido_detalhe(request, pk):
    atendimento = get_object_or_404(
        Atendimento.objects.select_related("cliente", "endereco"),
        pk=pk,
    )
    remarcar_form = RemarcarForm(
        initial={"data": atendimento.data},
        atendimento=atendimento,
    )
    if request.method == "POST":
        if not atendimento.pode_alterar:
            messages.error(request, "Esse atendimento não pode mais ser alterado.")
            return redirect("pedido_detalhe", pk=pk)
        acao = request.POST.get("acao")
        if acao == "remarcar":
            remarcar_form = RemarcarForm(request.POST, atendimento=atendimento)
            if remarcar_form.is_valid():
                try:
                    remarcar_form.save()
                except Exception as exc:
                    from django.core.exceptions import ValidationError

                    if not isinstance(exc, ValidationError):
                        raise
                    remarcar_form.add_error(None, exc)
                else:
                    messages.success(request, "Atendimento remarcado.")
                    return redirect("pedido_detalhe", pk=pk)
        elif acao in {"confirmar", "a_caminho", "concluir", "cancelar"}:
            mapa = {
                "confirmar": Status.CONFIRMADO,
                "a_caminho": Status.A_CAMINHO,
                "concluir": Status.CONCLUIDO,
                "cancelar": Status.CANCELADO,
            }
            try:
                alterar_status(atendimento, mapa[acao], request.POST.get("motivo", ""))
            except StatusBloqueado:
                messages.error(request, "Esse atendimento não pode mais ser alterado.")
            else:
                rotulos = {
                    "confirmar": "Atendimento confirmado.",
                    "a_caminho": "Marcado como a caminho.",
                    "concluir": "Atendimento concluído.",
                    "cancelar": "Atendimento cancelado.",
                }
                messages.success(request, rotulos[acao])
            return redirect("pedido_detalhe", pk=pk)
        else:
            messages.error(request, "Não reconheci essa ação.")
            return redirect("pedido_detalhe", pk=pk)

    config = garantir_configuracao()
    atendimento.fim = adicionar_minutos(atendimento.horario, config.slot_minutos)
    anotar_acessibilidade(remarcar_form)
    mensagem = ""
    if remarcar_form.data and remarcar_form.is_bound:
        escolhida = remarcar_form._data_escolhida()
    else:
        escolhida = atendimento.data
    if escolhida:
        mensagem = situacao_dia(escolhida, excluir_id=atendimento.pk)["mensagem"]
    else:
        mensagem = "Escolha uma data para ver os horários livres."
    return render(
        request,
        "painel/pedido_detalhe.html",
        {
            "atendimento": atendimento,
            "remarcar_form": remarcar_form,
            "mensagem_horarios": mensagem,
        },
    )


@login_required
def pedido_novo(request):
    if request.method == "POST":
        form = AgendamentoManualForm(request.POST)
        if request.POST.get("acao") == "agendar" and form.is_valid():
            try:
                atendimento = form.save()
            except Exception as exc:
                from django.core.exceptions import ValidationError

                if not isinstance(exc, ValidationError):
                    raise
                form.add_error(None, exc)
            else:
                messages.success(request, "Atendimento registrado na agenda.")
                return redirect("pedido_detalhe", pk=atendimento.pk)
    else:
        initial = {}
        if request.GET.get("data"):
            initial["data"] = request.GET.get("data")
        form = AgendamentoManualForm(initial=initial)
    anotar_acessibilidade(form)
    if form.data_escolhida:
        situacao = situacao_dia(
            form.data_escolhida,
            permitir_passado=True,
            janela_dias=form.janela_dias,
            janela_passado=form.janela_passado,
        )
    else:
        situacao = {
            "mensagem": "Escolha uma data para ver os horários livres.",
            "slots": [],
        }
    return render(
        request,
        "painel/pedido_novo.html",
        {"form": form, "mensagem_horarios": situacao["mensagem"]},
    )


@login_required
def clientes(request):
    termo = request.GET.get("q", "").strip()
    qs = Cliente.objects.annotate(
        total=Count("atendimentos"),
        ultimo=Max("atendimentos__data"),
    )
    if termo:
        filtro = Q(nome__icontains=termo)
        digitos = somente_digitos(termo)
        if digitos:
            filtro |= Q(telefone__contains=digitos)
        qs = qs.filter(filtro)
    pagina = Paginator(qs.order_by("nome"), 20).get_page(request.GET.get("pagina"))
    return render(request, "painel/clientes.html", {"pagina": pagina, "q": termo})


@login_required
def cliente_detalhe(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    enderecos = cliente.enderecos.prefetch_related(
        Prefetch(
            "atendimentos",
            queryset=Atendimento.objects.order_by("-data", "-horario"),
        )
    )
    config = garantir_configuracao()
    for endereco in enderecos:
        for item in endereco.atendimentos.all():
            item.fim = adicionar_minutos(item.horario, config.slot_minutos)
    return render(
        request,
        "painel/cliente_detalhe.html",
        {"cliente": cliente, "enderecos": enderecos},
    )


def _analisar_hora(valor):
    if not valor:
        return None
    try:
        hora, minuto = valor.split(":")[:2]
        return datetime.strptime(f"{int(hora):02d}:{int(minuto):02d}", "%H:%M").time()
    except (TypeError, ValueError):
        return None


@login_required
def configuracao(request):
    config = garantir_configuracao()
    dias = list(config.dias.order_by("dia_semana"))
    erros = []
    if request.method == "POST":
        if "remover_folga" in request.POST:
            Folga.objects.filter(pk=request.POST.get("remover_folga")).delete()
            messages.success(request, "Folga removida.")
            return redirect("configuracao")
        if "adicionar_folga" in request.POST:
            bruto = request.POST.get("data_folga")
            motivo = (request.POST.get("motivo_folga") or "").strip()[:120]
            try:
                data = datetime.strptime(bruto or "", "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Informe a data da folga.")
                return redirect("configuracao")
            Folga.objects.get_or_create(data=data, defaults={"motivo": motivo})
            messages.success(request, "Folga registrada. Esse dia sai da agenda pública.")
            return redirect("configuracao")

        try:
            slot = int(request.POST.get("slot_minutos", ""))
            capacidade = int(request.POST.get("capacidade", ""))
        except ValueError:
            erros.append("Informe a duração e a capacidade com números.")
            slot = config.slot_minutos
            capacidade = config.capacidade
        else:
            if slot not in {30, 60, 90, 120, 180}:
                erros.append("A duração do horário deve ser 30, 60, 90, 120 ou 180 minutos.")
            if not 1 <= capacidade <= 10:
                erros.append("A capacidade deve ficar entre 1 e 10.")

        novos = []
        for dia in dias:
            aberto = request.POST.get(f"aberto_{dia.dia_semana}") == "on"
            inicio = _analisar_hora(request.POST.get(f"inicio_{dia.dia_semana}"))
            fim = _analisar_hora(request.POST.get(f"fim_{dia.dia_semana}"))
            nome = NOMES_DIAS[dia.dia_semana]
            if inicio is None or fim is None:
                erros.append(f"Horário inválido em {nome}.")
                continue
            if aberto and inicio >= fim:
                erros.append(f"{nome}: o início precisa ser antes do fim.")
            elif aberto and datetime.combine(dia_dummy(inicio), inicio) + timedelta(minutes=slot) > datetime.combine(
                dia_dummy(inicio), fim
            ):
                erros.append(f"{nome}: a grade não cabe um horário de {slot} minutos.")
            novos.append((dia, aberto, inicio, fim))

        if not erros and len(novos) == len(dias):
            config.slot_minutos = slot
            config.capacidade = capacidade
            config.save(update_fields=["slot_minutos", "capacidade"])
            for dia, aberto, inicio, fim in novos:
                dia.aberto = aberto
                dia.inicio = inicio
                dia.fim = fim
                dia.save(update_fields=["aberto", "inicio", "fim"])
            messages.success(request, "Horários atualizados.")
            return redirect("configuracao")

    folgas = Folga.objects.filter(
        data__gte=timezone.localdate() - timedelta(days=30)
    ).order_by("data")
    for dia in dias:
        dia.nome = NOMES_DIAS[dia.dia_semana]
    return render(
        request,
        "painel/configuracao.html",
        {
            "config": config,
            "dias": dias,
            "nomes_dias": NOMES_DIAS,
            "erros": erros,
            "folgas": folgas,
            "vista": "configuracao",
        },
    )


def dia_dummy(horario):
    return datetime.today().date()
