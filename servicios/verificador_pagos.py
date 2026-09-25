from models.pago import Pago
from servicios.mercado_pago import buscar_pagos_por_referencia
from servicios.procesar_pagos import procesar_pago_aprobado


def verificar_pagos_pendientes():

    pagos = Pago.query.filter(
        Pago.estado == "pendiente",
        Pago.preferencia_id.isnot(None)
    ).all()

    if not pagos:
        print("No hay pagos pendientes para verificar.")
        return

    for pago in pagos:

        print(
            f"Revisando participación "
            f"{pago.participacion_id}..."
        )

        respuesta = buscar_pagos_por_referencia(
            pago.participacion_id
        )

        if respuesta["status"] != 200:
            print(
                f"No se pudo consultar Mercado Pago "
                f"para la participación "
                f"{pago.participacion_id}."
            )
            continue

        resultados = respuesta["response"].get(
            "results",
            []
        )

        if not resultados:
            print(
                f"No se encontraron pagos para "
                f"la participación "
                f"{pago.participacion_id}."
            )
            continue

        # Buscamos un pago aprobado que corresponda
        # al monto esperado.
        pago_mp = next(
            (
                resultado
                for resultado in resultados
                if resultado.get("status") == "approved"
                and resultado.get("transaction_amount") is not None
                and float(resultado["transaction_amount"])
                == float(pago.monto)
            ),
            None
        )

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

        procesar_pago_aprobado(
            id_pago,
            pago_mp
        )

    print("Verificación de pagos finalizada.")
