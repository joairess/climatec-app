from datetime import datetime

from django.contrib import messages
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from atendimento.codigos import normalizar_codigo
from atendimento.empresa import MENSAGENS_STATUS, SERVICOS, link_whatsapp
from atendimento.forms import AgendamentoForm, anotar_acessibilidade
from atendimento.models import Atendimento
from atendimento.slots import adicionar_minutos, garantir_configuracao, situacao_dia


def home(request):
    if request.method == "POST":
        form = AgendamentoForm(request.POST)
        if request.POST.get("acao") == "agendar" and form.is_valid():
            try:
                atendimento = form.save()
            except Exception as exc:
                from django.core.exceptions import ValidationError

                if isinstance(exc, ValidationError):
                    form.add_error(None, exc)
                else:
                    raise
            else:
                messages.success(
                    request,
                    "Pedido recebido. Guarde o código para acompanhar o atendimento.",
                )
                return redirect("acompanhar", codigo=atendimento.codigo)
    else:
        initial = {}
        if request.GET.get("data"):
            initial["data"] = request.GET.get("data")
        form = AgendamentoForm(initial=initial)

    anotar_acessibilidade(form)
    if form.data_escolhida:
        situacao = situacao_dia(form.data_escolhida)
    else:
        situacao = {
            "mensagem": "Escolha uma data para ver os horários livres.",
            "slots": [],
            "motivo": "sem_data",
        }
    return render(
        request,
        "public/home.html",
        {
            "form": form,
            "servicos": SERVICOS,
            "mensagem_horarios": situacao["mensagem"],
        },
    )


@require_GET
def horarios(request):
    bruto = request.GET.get("data") or ""
    try:
        data = datetime.strptime(bruto, "%Y-%m-%d").date()
    except ValueError:
        resposta = JsonResponse(
            {"slots": [], "mensagem": "Informe uma data válida.", "motivo": "invalida"},
            status=400,
        )
        resposta["Cache-Control"] = "no-store"
        return resposta

    kwargs = {}
    if request.user.is_authenticated and request.GET.get("painel") == "1":
        kwargs = {
            "permitir_passado": True,
            "janela_dias": 180,
            "janela_passado": 730,
        }
        excluir = request.GET.get("excluir")
        if excluir and excluir.isdigit():
            kwargs["excluir_id"] = int(excluir)

    info = situacao_dia(data, **kwargs)
    config = garantir_configuracao()
    from atendimento.slots import rotulo_slot

    resposta = JsonResponse(
        {
            "motivo": info["motivo"],
            "mensagem": info["mensagem"],
            "slots": [
                {
                    "value": slot.strftime("%H:%M"),
                    "label": rotulo_slot(slot, config.slot_minutos),
                }
                for slot in info["slots"]
            ],
        }
    )
    resposta["Cache-Control"] = "no-store"
    return resposta


def acompanhar_busca(request):
    bruto = (request.GET.get("codigo") or "").strip()
    erro = ""
    if bruto:
        codigo = normalizar_codigo(bruto)
        if not codigo:
            erro = "Use o código no formato CLM-XXXXXX."
        else:
            return redirect("acompanhar", codigo=codigo)
    return render(request, "public/busca.html", {"erro": erro, "codigo": bruto})


def acompanhar(request, codigo):
    normalizado = normalizar_codigo(codigo)
    if not normalizado:
        return render(
            request,
            "public/nao_encontrado.html",
            {"codigo": codigo},
            status=404,
        )
    try:
        atendimento = Atendimento.objects.select_related("cliente").get(codigo=normalizado)
    except Atendimento.DoesNotExist:
        return render(
            request,
            "public/nao_encontrado.html",
            {"codigo": normalizado},
            status=404,
        )
    config = garantir_configuracao()
    return render(
        request,
        "public/status.html",
        {
            "atendimento": atendimento,
            "fim": adicionar_minutos(atendimento.horario, config.slot_minutos),
            "mensagem_status": MENSAGENS_STATUS.get(atendimento.status, ""),
            "whatsapp_pedido": link_whatsapp(
                f"Olá, quero falar sobre o atendimento {atendimento.codigo}."
            ),
        },
    )


def privacidade(request):
    return render(request, "public/privacidade.html")


def saude(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "erro"}, status=503)
    return JsonResponse({"status": "ok"})


def csrf_falhou(request, reason=""):
    return render(request, "public/csrf.html", status=403)


def pagina_nao_encontrada(request, exception):
    return render(request, "404.html", status=404)


def pagina_erro(request):
    return render(request, "500.html", status=500)
