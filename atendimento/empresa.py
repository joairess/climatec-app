from urllib.parse import quote

TELEFONE_EXIBICAO = "(83) 3221-0628"
TELEFONE_URI = "tel:+558332210628"
WHATSAPP_EXIBICAO = "(83) 98855-2060"
WHATSAPP_NUMERO = "5583988552060"
CIDADE_PADRAO = "João Pessoa"

SERVICOS = [
    {
        "titulo": "Instalação",
        "texto": "Instalamos o aparelho que você já comprou, em casa ou na empresa.",
    },
    {
        "titulo": "Limpeza/Higienização",
        "texto": "Limpeza interna para o ar circular melhor e com menos cheiro.",
    },
    {
        "titulo": "Manutenção/Conserto",
        "texto": "Quando o aparelho não gela, vaza ou faz barulho.",
    },
    {
        "titulo": "Contrato de manutenção (PMOC)",
        "texto": "Visitas periódicas para empresas e condomínios.",
    },
]

MENSAGENS_STATUS = {
    "recebido": "Recebemos seu pedido. A equipe vai confirmar o horário.",
    "confirmado": "Horário confirmado. A equipe vai no dia combinado.",
    "remarcado": "O horário foi remarcado. Confira a nova data abaixo.",
    "a_caminho": "A equipe está a caminho.",
    "concluido": "Atendimento concluído. Obrigado por escolher a Climatec.",
    "cancelado": "Este atendimento foi cancelado.",
}


def link_whatsapp(texto=""):
    base = f"https://wa.me/{WHATSAPP_NUMERO}"
    if texto:
        return f"{base}?text={quote(texto)}"
    return base
