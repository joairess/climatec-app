import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = (
        "Cria o superusuário inicial a partir de DJANGO_SUPERUSER_USERNAME, "
        "DJANGO_SUPERUSER_PASSWORD e, se existir, DJANGO_SUPERUSER_EMAIL. "
        "Não cria ninguém quando usuário ou senha estão em branco, e não altera "
        "a senha de um usuário que já existe."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()

        if not username or not password.strip():
            self.stdout.write(
                "Usuário inicial não criado: defina DJANGO_SUPERUSER_USERNAME "
                "e DJANGO_SUPERUSER_PASSWORD."
            )
            return

        User = get_user_model()
        username = User.normalize_username(username)
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Usuário {username} já existe. A senha não foi alterada.")
            return

        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
        except IntegrityError:
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    f"Usuário {username} já existe. A senha não foi alterada."
                )
                return
            raise

        self.stdout.write(self.style.SUCCESS(f"Superusuário {username} criado."))
