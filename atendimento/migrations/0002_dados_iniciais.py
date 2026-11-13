from datetime import time

from django.db import migrations


DIAS = {
    0: (True, time(8, 0), time(18, 0)),
    1: (True, time(8, 0), time(18, 0)),
    2: (True, time(8, 0), time(18, 0)),
    3: (True, time(8, 0), time(18, 0)),
    4: (True, time(8, 0), time(18, 0)),
    5: (True, time(8, 0), time(12, 0)),
    6: (False, time(8, 0), time(12, 0)),
}


def criar_grade(apps, schema_editor):
    Configuracao = apps.get_model("atendimento", "ConfiguracaoAgenda")
    Horario = apps.get_model("atendimento", "HorarioSemana")
    config, _ = Configuracao.objects.get_or_create(
        pk=1,
        defaults={"slot_minutos": 120, "capacidade": 1},
    )
    for dia, (aberto, inicio, fim) in DIAS.items():
        Horario.objects.get_or_create(
            configuracao_id=config.pk,
            dia_semana=dia,
            defaults={"aberto": aberto, "inicio": inicio, "fim": fim},
        )


def remover_grade(apps, schema_editor):
    Configuracao = apps.get_model("atendimento", "ConfiguracaoAgenda")
    Configuracao.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("atendimento", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(criar_grade, remover_grade),
    ]
