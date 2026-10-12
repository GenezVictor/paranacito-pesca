from models.pago import Pago
from models.participacion import Participacion
from sqlalchemy import or_
from servicios.mercado_pago import buscar_pagos_por_referencia
from servicios.procesar_pagos import procesar_pago_aprobado


def verificar_pagos_pendientes():

    verificaciones_fallidas = set()

    pagos = (
        Pago.query
        .join(
            Participacion,
            Pago.participacion_id == Participacion.id
        )
        .filter(
            Pago.estado == "pendiente",
            or_(
                Pago.preferencia_id.isnot(None),
                Participacion.estado == "pago_incierto"
            )
        )
        .all()
    )

    if not pagos:
        print("No hay pagos pendientes para verificar.")
        return verificaciones_fallidas

    for pago in pagos:

        print(
            f"Revisando participación "
            f"{pago.participacion_id}..."
        )

        try:
            respuesta = buscar_pagos_por_referencia(
                pago.participacion_id
            )
        except Exception as error:
            print(
                f"Error consultando Mercado Pago para "
                f"la participación {pago.participacion_id}: {error}"
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

        if (
            not isinstance(respuesta, dict)
            or respuesta.get("status") != 200
        ):
            print(
                f"No se pudo consultar Mercado Pago "
                f"para la participación "
                f"{pago.participacion_id}."
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

        contenido = respuesta.get("response")

        if not isinstance(contenido, dict):
            print(
                f"Respuesta inválida de Mercado Pago para "
                f"la participación {pago.participacion_id}."
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

        resultados = contenido.get("results")

        if not isinstance(resultados, list):
            print(
                f"Lista de pagos inválida para "
                f"la participación {pago.participacion_id}."
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

        try:
            pagos_aprobados = [
                resultado
                for resultado in resultados
                if isinstance(resultado, dict)
                and resultado.get("status") == "approved"
                and resultado.get("transaction_amount") is not None
                and float(resultado["transaction_amount"])
                == float(pago.monto)
            ]
        except (TypeError, ValueError) as error:
            print(
                f"Importe inválido en Mercado Pago para "
                f"la participación {pago.participacion_id}: {error}"
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

        if not resultados:
            print(
                f"No se encontraron pagos para "
                f"la participación "
                f"{pago.participacion_id}."
            )
            continue

        # Buscamos un pago aprobado que corresponda
        # al monto esperado.
        pago_mp = pagos_aprobados[0] if pagos_aprobados else None

        if not pago_mp and any(
            isinstance(resultado, dict)
            and resultado.get("status") == "approved"
            for resultado in resultados
        ):
            print(
                f"ALERTA: pago aprobado con importe diferente "
                f"para la participación {pago.participacion_id}. "
                f"Se conserva la reserva para revisión."
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

        if not pago_mp:
            print(
                f"No hay un pago aprobado por el monto "
                f"esperado para la participación "
                f"{pago.participacion_id}."
            )
            continue

        id_pago = pago_mp.get("id")

        print(
            f"Mercado Pago: approved "
            f"| ID: {id_pago}"
        )

        try:
            procesado = procesar_pago_aprobado(
                id_pago,
                pago_mp
            )
        except Exception as error:
            print(
                f"ALERTA: error procesando pago aprobado "
                f"de participación {pago.participacion_id}: {error}"
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

        if procesado is not True:
            print(
                f"ALERTA: no se pudo confirmar el pago "
                f"de participación {pago.participacion_id}. "
                f"Se conserva la reserva para revisión."
            )
            verificaciones_fallidas.add(pago.participacion_id)
            continue

    print("Verificación de pagos finalizada.")
    return verificaciones_fallidas
