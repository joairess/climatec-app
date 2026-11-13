import re
from urllib.parse import quote

_NAO_DIGITOS = re.compile(r"\D")


def somente_digitos(valor):
    return _NAO_DIGITOS.sub("", valor or "")


def normalizar_telefone(valor):
    digitos = somente_digitos(valor)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if digitos.startswith("0") and len(digitos) in (11, 12):
        digitos = digitos[1:]
    return digitos


def telefone_valido(digitos):
    return bool(re.fullmatch(r"\d{10,11}", digitos or ""))


def formatar_telefone(digitos):
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return digitos


def link_whatsapp_cliente(telefone, texto=""):
    base = f"https://wa.me/55{telefone}"
    if texto:
        return f"{base}?text={quote(texto)}"
    return base
