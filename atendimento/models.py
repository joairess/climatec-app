from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from atendimento.codigos import gerar_codigo
from atendimento.phones import formatar_telefone, link_whatsapp_cliente


class TipoCliente(models.TextChoices):
    RESIDENCIA = "residencia", "Residência"
    EMPRESA = "empresa", "Empresa"
    CONDOMINIO = "condominio", "Condomínio"


class Servico(models.TextChoices):
    INSTALACAO = "instalacao", "Instalação"
    LIMPEZA = "limpeza", "Limpeza/Higienização"
    MANUTENCAO = "manutencao", "Manutenção/Conserto"
    PMOC = "pmoc", "Contrato de manutenção (PMOC)"


class Status(models.TextChoices):
    RECEBIDO = "recebido", "Recebido"
    CONFIRMADO = "confirmado", "Confirmado"
    REMARCADO = "remarcado", "Remarcado"
    A_CAMINHO = "a_caminho", "A caminho"
    CONCLUIDO = "concluido", "Concluído"
    CANCELADO = "cancelado", "Cancelado"


class Origem(models.TextChoices):
    SITE = "site", "Site"
    TELEFONE = "telefone", "Telefone"
    WHATSAPP = "whatsapp", "WhatsApp"


STATUS_ALTERAVEIS = {
    Status.RECEBIDO,
    Status.CONFIRMADO,
    Status.REMARCADO,
    Status.A_CAMINHO,
}


class ConfiguracaoAgenda(models.Model):
    slot_minutos = models.PositiveSmallIntegerField(
        default=120,
        validators=[MinValueValidator(30), MaxValueValidator(180)],
    )
    capacidade = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )

    class Meta:
        verbose_name = "Configuração da agenda"
        verbose_name_plural = "Configuração da agenda"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Agenda da Climatec"


class HorarioSemana(models.Model):
    configuracao = models.ForeignKey(
        ConfiguracaoAgenda,
        related_name="dias",
        on_delete=models.CASCADE,
    )
    dia_semana = models.PositiveSmallIntegerField()
    aberto = models.BooleanField(default=True)
    inicio = models.TimeField()
    fim = models.TimeField()

    class Meta:
        verbose_name = "Horário da semana"
        verbose_name_plural = "Horários da semana"
        constraints = [
            models.UniqueConstraint(
                fields=["configuracao", "dia_semana"],
                name="horario_unico_por_dia",
            )
        ]
        ordering = ["dia_semana"]

    def __str__(self):
        return f"Dia {self.dia_semana}"


class Folga(models.Model):
    data = models.DateField(unique=True)
    motivo = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "Folga"
        verbose_name_plural = "Folgas"
        ordering = ["data"]

    def __str__(self):
        return self.data.strftime("%d/%m/%Y")


class Cliente(models.Model):
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=11, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.telefone_formatado})"

    @property
    def telefone_formatado(self):
        return formatar_telefone(self.telefone)

    @property
    def primeiro_nome(self):
        partes = self.nome.split()
        return partes[0] if partes else ""


class Endereco(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        related_name="enderecos",
        on_delete=models.PROTECT,
    )
    tipo = models.CharField(max_length=20, choices=TipoCliente.choices)
    logradouro = models.CharField(max_length=200)
    bairro = models.CharField(max_length=80)
    cidade = models.CharField(max_length=80, default="João Pessoa")
    uf = models.CharField(max_length=2, default="PB")

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        ordering = ["bairro", "logradouro"]

    def __str__(self):
        return f"{self.logradouro} — {self.bairro}"


class Atendimento(models.Model):
    codigo = models.CharField(max_length=12, unique=True, blank=True, editable=False)
    cliente = models.ForeignKey(
        Cliente,
        related_name="atendimentos",
        on_delete=models.PROTECT,
    )
    endereco = models.ForeignKey(
        Endereco,
        related_name="atendimentos",
        on_delete=models.PROTECT,
    )
    servico = models.CharField(max_length=20, choices=Servico.choices)
    quantidade_aparelhos = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(500)]
    )
    observacoes = models.TextField(blank=True)
    data = models.DateField()
    horario = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEBIDO,
    )
    origem = models.CharField(
        max_length=20,
        choices=Origem.choices,
        default=Origem.SITE,
    )
    motivo_cancelamento = models.CharField(max_length=200, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Atendimento"
        verbose_name_plural = "Atendimentos"
        ordering = ["data", "horario"]
        indexes = [
            models.Index(fields=["data", "horario"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.codigo} {self.get_servico_display()}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            for _ in range(8):
                candidato = gerar_codigo()
                if not Atendimento.objects.filter(codigo=candidato).exists():
                    self.codigo = candidato
                    break
            else:
                raise RuntimeError("Não foi possível gerar um código de acompanhamento.")
        super().save(*args, **kwargs)

    @property
    def pode_alterar(self):
        return self.status in STATUS_ALTERAVEIS

    def whatsapp_cliente_url(self):
        texto = f"Olá, aqui é da Climatec. Falo sobre o atendimento {self.codigo}."
        return link_whatsapp_cliente(self.cliente.telefone, texto)
