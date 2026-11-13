import re
import secrets

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODIGO = re.compile(r"[A-Z0-9]{6}")


def gerar_codigo():
    corpo = "".join(secrets.choice(ALFABETO) for _ in range(6))
    return f"CLM-{corpo}"


def normalizar_codigo(valor):
    bruto = re.sub(r"[^A-Za-z0-9]", "", valor or "").upper()
    if bruto.startswith("CLM"):
        bruto = bruto[3:]
    if not _CODIGO.fullmatch(bruto):
        return ""
    return f"CLM-{bruto}"
