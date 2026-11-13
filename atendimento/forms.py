from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from atendimento.empresa import CIDADE_PADRAO
from atendimento.models import Origem, Servico, Status, TipoCliente
from atendimento.phones import normalizar_telefone, telefone_valido
from atendimento.services import HorarioIndisponivel, StatusBloqueado, registrar, remarcar
from atendimento.slots import (
    garantir_configuracao,
    horarios_livres,
    rotulo_slot,
    slot_disponivel,
)


class EntrarForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Esta conta está inativa.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuário"
        self.fields["username"].widget.attrs.update(
            {
                "class": "field-control",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
        self.fields["password"].label = "Senha"
        self.fields["password"].widget.attrs.update(
            {
                "class": "field-control",
                "autocomplete": "current-password",
            }
        )


class AgendamentoForm(forms.Form):
    modo = "publico"
    servico = forms.ChoiceField(
        label="Serviço",
        choices=Servico.choices,
        widget=forms.RadioSelect(attrs={"class": "choice-cards cols-2"}),
    )
    tipo_cliente = forms.ChoiceField(
        label="Tipo de cliente",
        choices=TipoCliente.choices,
        widget=forms.RadioSelect(attrs={"class": "choice-cards"}),
    )
    nome = forms.CharField(label="Nome", max_length=120)
    telefone = forms.CharField(label="Telefone ou WhatsApp", max_length=20)
    logradouro = forms.CharField(label="Endereço", max_length=200)
    bairro = forms.CharField(label="Bairro", max_length=80)
    cidade = forms.CharField(label="Cidade", max_length=80, initial=CIDADE_PADRAO)
    quantidade = forms.IntegerField(
        label="Quantidade de aparelhos",
        min_value=1,
        max_value=500,
        error_messages={
            "invalid": "Informe a quantidade de aparelhos.",
            "min_value": "Informe pelo menos 1 aparelho.",
            "max_value": "O máximo nesta fase é 500 aparelhos.",
        },
    )
    observacoes = forms.CharField(
        label="Observações",
        required=False,
        max_length=2000,
        widget=forms.Textarea,
        help_text="Ponto de referência, interfone ou o que o aparelho está fazendo.",
    )
    data = forms.DateField(
        label="Data",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        error_messages={"invalid": "Informe uma data válida."},
    )
    horario = forms.ChoiceField(
        label="Horário",
        required=False,
        choices=[],
        widget=forms.RadioSelect(attrs={"class": "choice-cards"}),
        error_messages={"invalid_choice": "Esse horário não está mais disponível."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permitir_passado = self.modo == "manual"
        self.janela_dias = 180 if self.modo == "manual" else 90
        self.janela_passado = 730 if self.modo == "manual" else 0
        self.excluir_id = None
        self._preparar_widgets()
        self._carregar_horarios()

    def _preparar_widgets(self):
        textos = {
            "nome": {
                "autocomplete": "name",
                "placeholder": "Nome de quem recebe a equipe",
            },
            "telefone": {
                "autocomplete": "tel",
                "inputmode": "tel",
                "placeholder": "(83) 90000-0000",
            },
            "logradouro": {
                "autocomplete": "street-address",
                "placeholder": "Rua, número, complemento",
            },
            "bairro": {"placeholder": "Ex.: Manaíra, Tambaú, Bessa"},
            "cidade": {"autocomplete": "address-level2"},
        }
        for nome, extra in textos.items():
            self.fields[nome].widget.attrs.update({"class": "field-control", **extra})
        self.fields["quantidade"].widget.attrs.update(
            {"class": "field-control", "min": 1, "max": 500, "inputmode": "numeric"}
        )
        self.fields["observacoes"].widget.attrs.update({"class": "field-control", "rows": 4})
        hoje = timezone.localdate()
        inicio = hoje - timedelta(days=self.janela_passado)
        self.fields["data"].widget.attrs.update(
            {
                "class": "field-control",
                "min": inicio.isoformat(),
                "max": (hoje + timedelta(days=self.janela_dias)).isoformat(),
            }
        )

    @property
    def data_escolhida(self):
        bruto = self.data.get("data") if self.is_bound else self.initial.get("data")
        if hasattr(bruto, "year"):
            return bruto
        if not bruto:
            return None
        try:
            return datetime.strptime(str(bruto)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def _carregar_horarios(self):
        escolhida = self.data_escolhida
        slots = (
            horarios_livres(
                escolhida,
                permitir_passado=self.permitir_passado,
                janela_dias=self.janela_dias,
                janela_passado=self.janela_passado,
                excluir_id=self.excluir_id,
            )
            if escolhida
            else []
        )
        config = garantir_configuracao()
        escolhas = [(slot.strftime("%H:%M"), rotulo_slot(slot, config.slot_minutos)) for slot in slots]
        self.fields["horario"].choices = escolhas
        if escolhas:
            self.fields["horario"].widget.attrs["required"] = True

    def _exige_horario(self):
        if self.modo == "manual":
            return True
        return self.is_bound and self.data.get("acao") == "agendar"

    def clean_nome(self):
        nome = " ".join(self.cleaned_data["nome"].split())
        if len(nome) < 3:
            raise forms.ValidationError("Informe o nome.")
        return nome

    def clean_telefone(self):
        numero = normalizar_telefone(self.cleaned_data["telefone"])
        if not telefone_valido(numero):
            raise forms.ValidationError("Informe um telefone com DDD. Ex.: (83) 98855-2060.")
        return numero

    def clean_logradouro(self):
        logradouro = " ".join(self.cleaned_data["logradouro"].split())
        if len(logradouro) < 5:
            raise forms.ValidationError("Informe a rua e o número.")
        return logradouro

    def clean_bairro(self):
        bairro = " ".join(self.cleaned_data["bairro"].split())
        if len(bairro) < 2:
            raise forms.ValidationError("Informe o bairro.")
        return bairro

    def clean_cidade(self):
        cidade = " ".join(self.cleaned_data["cidade"].split())
        return cidade or CIDADE_PADRAO

    def clean_data(self):
        data = self.cleaned_data["data"]
        hoje = timezone.localdate()
        if not self.permitir_passado and data < hoje:
            raise forms.ValidationError("Escolha hoje ou uma data futura.")
        if not self.permitir_passado and data > hoje + timedelta(days=self.janela_dias):
            raise forms.ValidationError("Só agendamos até 90 dias à frente.")
        if self.permitir_passado and data < hoje - timedelta(days=self.janela_passado):
            raise forms.ValidationError("Essa data está antiga demais para registrar.")
        if self.permitir_passado and data > hoje + timedelta(days=self.janela_dias):
            raise forms.ValidationError("Escolha uma data mais próxima.")
        return data

    def clean_horario(self):
        bruto = self.cleaned_data.get("horario")
        if not bruto:
            return None
        try:
            return datetime.strptime(bruto, "%H:%M").time()
        except ValueError as exc:
            raise forms.ValidationError("Horário inválido.") from exc

    def clean(self):
        cleaned = super().clean()
        if not self._exige_horario():
            return cleaned
        data = cleaned.get("data")
        horario = cleaned.get("horario")
        if not horario:
            self.add_error("horario", "Escolha um horário livre.")
        elif data and not slot_disponivel(
            data,
            horario,
            permitir_passado=self.permitir_passado,
            janela_dias=self.janela_dias,
            janela_passado=self.janela_passado,
            excluir_id=self.excluir_id,
        ):
            self.add_error("horario", "Esse horário não está disponível.")
        return cleaned

    def save(self):
        dados = self.cleaned_data
        try:
            return registrar(
                nome=dados["nome"],
                telefone=dados["telefone"],
                tipo_cliente=dados["tipo_cliente"],
                logradouro=dados["logradouro"],
                bairro=dados["bairro"],
                cidade=dados["cidade"],
                servico=dados["servico"],
                quantidade=dados["quantidade"],
                observacoes=dados.get("observacoes", ""),
                data=dados["data"],
                horario=dados["horario"],
                origem=dados.get("origem", Origem.SITE),
                status=dados.get("status", Status.RECEBIDO),
                permitir_passado=self.permitir_passado,
                janela_dias=self.janela_dias,
                janela_passado=self.janela_passado,
            )
        except HorarioIndisponivel as exc:
            raise forms.ValidationError(
                "Esse horário acabou de ser preenchido. Escolha outro."
            ) from exc


class AgendamentoManualForm(AgendamentoForm):
    modo = "manual"
    origem = forms.ChoiceField(
        label="Como chegou",
        choices=[
            (Origem.TELEFONE, Origem.TELEFONE.label),
            (Origem.WHATSAPP, Origem.WHATSAPP.label),
        ],
        widget=forms.RadioSelect(attrs={"class": "choice-cards"}),
    )
    status = forms.ChoiceField(
        label="Situação inicial",
        choices=[
            (Status.RECEBIDO, Status.RECEBIDO.label),
            (Status.CONFIRMADO, Status.CONFIRMADO.label),
            (Status.A_CAMINHO, Status.A_CAMINHO.label),
            (Status.CONCLUIDO, Status.CONCLUIDO.label),
        ],
        initial=Status.RECEBIDO,
        widget=forms.RadioSelect(attrs={"class": "choice-cards cols-2"}),
    )


class RemarcarForm(forms.Form):
    data = forms.DateField(
        label="Nova data",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "field-control"}),
        error_messages={"invalid": "Informe uma data válida."},
    )
    horario = forms.ChoiceField(
        label="Novo horário",
        required=False,
        choices=[],
        widget=forms.RadioSelect(attrs={"class": "choice-cards"}),
        error_messages={"invalid_choice": "Esse horário não está disponível."},
    )

    def __init__(self, *args, atendimento, **kwargs):
        self.atendimento = atendimento
        super().__init__(*args, **kwargs)
        hoje = timezone.localdate()
        self.fields["data"].widget.attrs.update(
            {
                "min": hoje.isoformat(),
                "max": (hoje + timedelta(days=90)).isoformat(),
            }
        )
        escolhida = self._data_escolhida()
        slots = horarios_livres(escolhida, excluir_id=atendimento.pk) if escolhida else []
        config = garantir_configuracao()
        escolhas = [(slot.strftime("%H:%M"), rotulo_slot(slot, config.slot_minutos)) for slot in slots]
        self.fields["horario"].choices = escolhas
        if escolhas:
            self.fields["horario"].widget.attrs["required"] = True

    def _data_escolhida(self):
        bruto = self.data.get("data") if self.is_bound else self.initial.get("data")
        if hasattr(bruto, "year"):
            return bruto
        if not bruto:
            return None
        try:
            return datetime.strptime(str(bruto)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def clean_horario(self):
        bruto = self.cleaned_data.get("horario")
        if not bruto:
            return None
        return datetime.strptime(bruto, "%H:%M").time()

    def clean(self):
        cleaned = super().clean()
        data = cleaned.get("data")
        horario = cleaned.get("horario")
        if not horario:
            self.add_error("horario", "Escolha um horário livre.")
            return cleaned
        atual = self.atendimento.horario.replace(second=0, microsecond=0)
        if data == self.atendimento.data and horario == atual:
            self.add_error("horario", "Esse já é o horário marcado.")
        elif data and not slot_disponivel(data, horario, excluir_id=self.atendimento.pk):
            self.add_error("horario", "Esse horário não está disponível.")
        return cleaned

    def save(self):
        try:
            return remarcar(
                self.atendimento,
                self.cleaned_data["data"],
                self.cleaned_data["horario"],
            )
        except HorarioIndisponivel as exc:
            raise forms.ValidationError(
                "Esse horário acabou de ser preenchido. Escolha outro."
            ) from exc
        except StatusBloqueado as exc:
            raise forms.ValidationError("Esse atendimento não pode mais ser alterado.") from exc


def anotar_acessibilidade(form):
    if form is None or not hasattr(form, "fields"):
        return form
    for nome, campo in form.fields.items():
        descritos = []
        if campo.help_text:
            descritos.append(f"ajuda-{nome}")
        if form.is_bound and form.errors.get(nome):
            campo.widget.attrs["aria-invalid"] = "true"
            descritos.append(f"erro-{nome}")
        if descritos:
            campo.widget.attrs["aria-describedby"] = " ".join(descritos)
    return form
