from atendimento.empresa import (
    TELEFONE_EXIBICAO,
    TELEFONE_URI,
    WHATSAPP_EXIBICAO,
    link_whatsapp,
)


def empresa(request):
    return {
        "empresa_telefone": TELEFONE_EXIBICAO,
        "empresa_telefone_uri": TELEFONE_URI,
        "empresa_whatsapp": WHATSAPP_EXIBICAO,
        "empresa_whatsapp_url": link_whatsapp(),
    }
