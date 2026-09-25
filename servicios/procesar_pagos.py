from extensions import db
from models.participacion import Participacion
from models.pago import Pago
from models.numero import Numero
from servicios.email import (
    preparar_confirmacion_pago,
    enviar_email,
)


def procesar_pago_aprobado(id_pago, pago_mp):

    estado_mp = pago_mp.get("status")
    referencia = pago_mp.get("external_reference")
    monto_mp = pago_mp.get("transaction_amount")

    if estado_mp != "approved":
        print(
            f"El pago {id_pago} no está aprobado. "
            f"Estado: {estado_mp}"
        )
        return False

    try:
        participacion_id = int(referencia)
    except (TypeError, ValueError):
        print(
            f"Referencia inválida para el pago {id_pago}: "
            f"{referencia}"
        )
        return False

    participacion = db.session.get(
        Participacion,
        participacion_id
    )

    if not participacion:
        print(
            f"No se encontró la participación "
            f"{participacion_id}."
        )
        return False

    pago = Pago.query.filter_by(
        participacion_id=participacion.id
    ).first()

    if not pago:
        print(
            f"No se encontró el pago de la "
            f"participación {participacion.id}."
        )
        return False

    # Evitamos procesar nuevamente un pago ya confirmado.
    if (
        pago.estado == "aprobado"
        and pago.id_externo == str(id_pago)
    ):
        print(
            f"El pago {id_pago} ya fue procesado."
        )
        return True

    # Verificamos que el monto pagado coincida
    # con el monto esperado.
    if monto_mp is None or float(monto_mp) != float(pago.monto):
        print(
            f"El monto del pago {id_pago} no coincide. "
            f"Esperado: {pago.monto} | "
            f"Recibido: {monto_mp}"
        )
        return False

    pago.estado = "aprobado"
    pago.id_externo = str(id_pago)

    numeros = Numero.query.filter_by(
        participacion_id=participacion.id
    ).all()

    enviar_confirmacion = False

    if (
        participacion.estado == "reservado"
        and numeros
    ):
        participacion.estado = "confirmada"

        for numero in numeros:
            numero.estado = "vendido"

        enviar_confirmacion = True

        print(
            f"Pago {id_pago} confirmado. "
            f"Números vendidos."
        )

    else:
        participacion.estado = "requiere_revision"

        print(
            f"Pago {id_pago} aprobado, pero la "
            f"reserva ya no tiene números. "
            f"Marcada como requiere_revision."
        )

    # Primero guardamos el pago y la participación.
    db.session.commit()

    # El correo se envía después del commit.
    # Si falla el email, el pago sigue correctamente confirmado.
    if enviar_confirmacion:
        try:
            datos_email = preparar_confirmacion_pago(
                participacion
            )

            enviado = enviar_email(
                destinatario=datos_email["destinatario"],
                asunto=datos_email["asunto"],
                contenido_html=datos_email["html"],
            )

            if enviado:
                print(
                    f"Email de confirmación enviado para "
                    f"la participación {participacion.id}."
                )
            else:
                print(
                    f"No se pudo enviar el email de "
                    f"la participación {participacion.id}."
                )

        except Exception as error:
            print(
                f"Error preparando/enviando email de "
                f"la participación {participacion.id}: "
                f"{error}"
            )

    return True
