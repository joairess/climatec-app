import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from atendimento.models import Atendimento, Origem, Servico, Status, TipoCliente
from atendimento.services import HorarioIndisponivel, registrar
from atendimento.slots import garantir_configuracao, situacao_dia

SENHA_DEMO = "climatec-demo"
USUARIO_DEMO = "atendimento"


class Command(BaseCommand):
    help = "Carrega um usuário e atendimentos fictícios para demonstração."

    def handle(self, *args, **options):
        if os.environ.get("RENDER") and os.environ.get("ALLOW_DEMO_SEED") != "1":
            raise CommandError(
                "Seed de demonstração desativado em produção. "
                "Crie o acesso com createsuperuser. "
                "ALLOW_DEMO_SEED=1 força a carga e não é recomendado."
            )

        garantir_configuracao()
        self._garantir_usuario()
        if Atendimento.objects.filter(codigo="CLM-DEMO01").exists():
            self.stdout.write("Demonstração já estava carregada.")
            self._imprimir()
            return

        with transaction.atomic():
            self._criar_atendimentos()
        self.stdout.write(self.style.SUCCESS("Demonstração pronta."))
        self._imprimir()

    def _garantir_usuario(self):
        User = get_user_model()
        usuario, criado = User.objects.get_or_create(
            username=USUARIO_DEMO,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Climatec",
            },
        )
        if criado:
            usuario.set_password(SENHA_DEMO)
            usuario.save()

    def _criar_atendimentos(self):
        hoje = timezone.localdate()
        vitrine, slots = self._dia(hoje, 3, 1)
        self._marcar(
            codigo="CLM-DEMO01",
            nome="Eduardo Nascimento",
            telefone="83988770011",
            tipo=TipoCliente.RESIDENCIA,
            logradouro="Rua Infante Dom Henrique, 210",
            bairro="Manaíra",
            servico=Servico.MANUTENCAO,
            quantidade=1,
            observacoes="Não gela o suficiente desde a semana passada.",
            data=vitrine,
            horario=slots[0],
            status=Status.A_CAMINHO,
            origem=Origem.TELEFONE,
        )
        self._marcar(
            codigo="CLM-DEMO02",
            nome="Marina Albuquerque",
            telefone="83991110022",
            tipo=TipoCliente.RESIDENCIA,
            logradouro="Av. Rui Carneiro, 450, apto 302",
            bairro="Tambaú",
            servico=Servico.LIMPEZA,
            quantidade=2,
            observacoes="Portaria 24h. Apto 302.",
            data=vitrine,
            horario=slots[1],
            status=Status.REMARCADO,
            origem=Origem.SITE,
        )
        self._marcar(
            codigo="CLM-DEMO03",
            nome="Padaria São José",
            telefone="8332210099",
            tipo=TipoCliente.EMPRESA,
            logradouro="Rua Duque de Caxias, 880",
            bairro="Centro",
            servico=Servico.INSTALACAO,
            quantidade=3,
            observacoes="Os aparelhos já estão na loja.",
            data=vitrine,
            horario=slots[2],
            status=Status.RECEBIDO,
            origem=Origem.WHATSAPP,
        )

        seguinte, slots_seguinte = self._dia(vitrine + timedelta(days=1), 2, 1)
        self._marcar(
            codigo="CLM-DEMO04",
            nome="Escola Pequeno Príncipe",
            telefone="8332147700",
            tipo=TipoCliente.EMPRESA,
            logradouro="Av. Epitácio Pessoa, 1200",
            bairro="Miramar",
            servico=Servico.LIMPEZA,
            quantidade=6,
            observacoes="Atender no intervalo da manhã.",
            data=seguinte,
            horario=slots_seguinte[0],
            status=Status.CONFIRMADO,
            origem=Origem.TELEFONE,
        )
        self._marcar(
            codigo="CLM-DEMO09",
            nome="Lúcia Ferreira",
            telefone="83991230044",
            tipo=TipoCliente.RESIDENCIA,
            logradouro="Rua Projetada, 12",
            bairro="Jardim Oceania",
            servico=Servico.LIMPEZA,
            quantidade=1,
            observacoes="Casa da mãe. Interfone 12.",
            data=seguinte,
            horario=slots_seguinte[1],
            status=Status.RECEBIDO,
            origem=Origem.WHATSAPP,
        )

        dia_pmoc, slots_pmoc = self._dia(seguinte + timedelta(days=1), 1, 1)
        self._marcar(
            codigo="CLM-DEMO05",
            nome="Condomínio Parque Cabo Branco",
            telefone="83999880033",
            tipo=TipoCliente.CONDOMINIO,
            logradouro="Av. Cabo Branco, 2500",
            bairro="Cabo Branco",
            servico=Servico.PMOC,
            quantidade=18,
            observacoes="Procurar a administração na portaria.",
            data=dia_pmoc,
            horario=slots_pmoc[0],
            status=Status.CONFIRMADO,
            origem=Origem.WHATSAPP,
        )

        passado, slots_passados = self._dia(hoje - timedelta(days=7), 1, -1)
        self._marcar(
            codigo="CLM-DEMO06",
            nome="Lúcia Ferreira",
            telefone="83991230044",
            tipo=TipoCliente.RESIDENCIA,
            logradouro="Rua José Serrano Navarro, 75",
            bairro="Bessa",
            servico=Servico.LIMPEZA,
            quantidade=2,
            observacoes="Dois splits na sala e no quarto.",
            data=passado,
            horario=slots_passados[0],
            status=Status.CONCLUIDO,
            origem=Origem.TELEFONE,
        )
        antes, slots_antes = self._dia(passado - timedelta(days=1), 1, -1)
        self._marcar(
            codigo="CLM-DEMO07",
            nome="Rafael Monteiro",
            telefone="83997650055",
            tipo=TipoCliente.RESIDENCIA,
            logradouro="Rua das Acácias, 40",
            bairro="Altiplano",
            servico=Servico.MANUTENCAO,
            quantidade=1,
            observacoes="Cliente pediu para cancelar.",
            data=antes,
            horario=slots_antes[0],
            status=Status.CANCELADO,
            origem=Origem.WHATSAPP,
        )
        mais_antigo, slots_antigos = self._dia(antes - timedelta(days=1), 1, -1)
        self._marcar(
            codigo="CLM-DEMO08",
            nome="Lúcia Ferreira",
            telefone="83991230044",
            tipo=TipoCliente.RESIDENCIA,
            logradouro="Rua José Serrano Navarro, 75",
            bairro="Bessa",
            servico=Servico.LIMPEZA,
            quantidade=2,
            observacoes="Primeira higienização do ano.",
            data=mais_antigo,
            horario=slots_antigos[0],
            status=Status.CONCLUIDO,
            origem=Origem.TELEFONE,
        )

    def _dia(self, inicio, minimo, passo):
        data = inicio
        for _ in range(60):
            info = situacao_dia(
                data,
                permitir_passado=True,
                janela_dias=120,
                janela_passado=800,
            )
            if len(info["slots"]) >= minimo:
                return data, info["slots"]
            data += timedelta(days=passo)
        raise CommandError("Não encontrei um dia com horários livres na grade.")

    def _marcar(self, **dados):
        try:
            registrar(
                nome=dados["nome"],
                telefone=dados["telefone"],
                tipo_cliente=dados["tipo"],
                logradouro=dados["logradouro"],
                bairro=dados["bairro"],
                cidade="João Pessoa",
                servico=dados["servico"],
                quantidade=dados["quantidade"],
                observacoes=dados["observacoes"],
                data=dados["data"],
                horario=dados["horario"],
                origem=dados["origem"],
                status=dados["status"],
                codigo=dados["codigo"],
                permitir_passado=True,
                janela_dias=120,
                janela_passado=800,
            )
        except HorarioIndisponivel as exc:
            raise CommandError(f"Horário ocupado ao criar {dados['codigo']}.") from exc

    def _imprimir(self):
        self.stdout.write(f"Usuário: {USUARIO_DEMO}")
        self.stdout.write(f"Senha: {SENHA_DEMO}")
        self.stdout.write("Acompanhar: /acompanhar/CLM-DEMO01/")
        self.stdout.write("Área da equipe: /painel/")
