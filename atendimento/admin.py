from django.contrib import admin

from atendimento.models import (
    Atendimento,
    Cliente,
    ConfiguracaoAgenda,
    Endereco,
    Folga,
    HorarioSemana,
)


class EnderecoInline(admin.TabularInline):
    model = Endereco
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "criado_em")
    search_fields = ("nome", "telefone")
    inlines = [EnderecoInline]


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "data", "horario", "status", "servico", "cliente", "origem")
    list_filter = ("status", "servico", "origem", "data")
    search_fields = ("codigo", "cliente__nome", "cliente__telefone", "endereco__bairro")
    readonly_fields = ("codigo", "criado_em", "atualizado_em")


class HorarioSemanaInline(admin.TabularInline):
    model = HorarioSemana
    extra = 0


@admin.register(ConfiguracaoAgenda)
class ConfiguracaoAgendaAdmin(admin.ModelAdmin):
    inlines = [HorarioSemanaInline]


@admin.register(Folga)
class FolgaAdmin(admin.ModelAdmin):
    list_display = ("data", "motivo")
