from django.contrib.auth import views as auth_views
from django.urls import path

from atendimento import views_painel, views_public
from atendimento.forms import EntrarForm

urlpatterns = [
    path("", views_public.home, name="home"),
    path("agendar/horarios/", views_public.horarios, name="horarios"),
    path("acompanhar/", views_public.acompanhar_busca, name="acompanhar_busca"),
    path("acompanhar/<slug:codigo>/", views_public.acompanhar, name="acompanhar"),
    path("privacidade/", views_public.privacidade, name="privacidade"),
    path("saude/", views_public.saude, name="saude"),
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="painel/login.html",
            authentication_form=EntrarForm,
            redirect_authenticated_user=True,
        ),
        name="entrar",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="sair"),
    path("painel/", views_painel.agenda, name="painel"),
    path("painel/semana/", views_painel.semana, name="painel_semana"),
    path("painel/pedido/novo/", views_painel.pedido_novo, name="pedido_novo"),
    path("painel/pedido/<int:pk>/", views_painel.pedido_detalhe, name="pedido_detalhe"),
    path("painel/clientes/", views_painel.clientes, name="clientes"),
    path("painel/clientes/<int:pk>/", views_painel.cliente_detalhe, name="cliente_detalhe"),
    path("painel/horarios/", views_painel.configuracao, name="configuracao"),
]
