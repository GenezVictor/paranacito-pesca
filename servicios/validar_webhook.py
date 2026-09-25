import os
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()


def validar_webhook(x_signature, x_request_id, data_id):

    secret = os.getenv("MP_WEBHOOK_SECRET")

    if not secret:
        print("ERROR: no se encontró MP_WEBHOOK_SECRET.")
        return False

    if not x_signature or not x_request_id or not data_id:
        print("ERROR: faltan datos necesarios para validar el webhook.")
        return False

    ts = None
    v1 = None

    partes = x_signature.split(",")

    for parte in partes:
        clave_valor = parte.split("=", 1)

        if len(clave_valor) != 2:
            continue

        clave = clave_valor[0].strip()
        valor = clave_valor[1].strip()

        if clave == "ts":
            ts = valor

        elif clave == "v1":
            v1 = valor

    if not ts or not v1:
        print("ERROR: x-signature no contiene ts o v1.")
        return False

    manifest = (
        f"id:{data_id};"
        f"request-id:{x_request_id};"
        f"ts:{ts};"
    )

    firma_calculada = hmac.new(
        secret.encode(),
        manifest.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        firma_calculada,
        v1
    )
