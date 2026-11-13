from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Climatec"
admin.site.site_title = "Climatec"
admin.site.index_title = "Atendimento"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("atendimento.urls")),
]

handler404 = "atendimento.views_public.pagina_nao_encontrada"
handler500 = "atendimento.views_public.pagina_erro"
