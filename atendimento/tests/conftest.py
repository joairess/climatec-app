import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def owner(db):
    return get_user_model().objects.create_user(
        username="atendimento",
        password="climatec-demo",
        is_staff=True,
        is_superuser=True,
    )
