import os

import mercadopago
from dotenv import load_dotenv


load_dotenv()


access_token = os.getenv("MP_ACCESS_TOKEN")

if not access_token:
    raise ValueError(
        "No se encontró MP_ACCESS_TOKEN en el archivo .env"
    )


sdk = mercadopago.SDK(access_token)


def crear_preferencia(
    titulo,
    cantidad,
    precio,
    referencia
):

    datos = {
        "items": [
            {
                "title": titulo,
                "quantity": cantidad,
                "unit_price": precio
            }
        ],
        "external_reference": str(referencia)
    }

    respuesta = sdk.preference().create(datos)

    return respuesta


def consultar_pago(
    id_pago
):

    respuesta = sdk.payment().get(
        id_pago
    )

    return respuesta


def buscar_pagos_por_referencia(referencia):
    respuesta = sdk.payment().search(
        {
            "external_reference": str(referencia),
            "sort": "date_created",
            "criteria": "desc"
        }
    )
    return respuesta
