from servicios.fechas import ahora_utc

from extensions import db
from models.participacion import Participacion
from models.numero import Numero
from models.pago import Pago


def liberar_participaciones_vencidas(excluir_ids=None):

    excluir_ids = set(excluir_ids or [])

    ahora = ahora_utc()

    # Consultamos solamente los identificadores.
    ids = [
        fila[0]
        for fila in db.session.query(Participacion.id).filter(
            Participacion.estado == "reservado",
            Participacion.fecha_expiracion <= ahora
        ).all()
    ]

    db.session.rollback()

    for participacion_id in ids:

        if participacion_id in excluir_ids:
            print(f'Reserva {participacion_id}: verificación fallida, se conserva.')
            continue

        try:
            # Mismo orden de bloqueo que el webhook:
            # participación, pago y números.
            participacion = (
                Participacion.query
                .filter_by(id=participacion_id)
                .with_for_update()
                .first()
            )

            if (
                participacion is None
                or participacion.estado != "reservado"
                or participacion.fecha_expiracion is None
                or participacion.fecha_expiracion > ahora_utc()
            ):
                db.session.rollback()
                continue

            pago = (
                Pago.query
                .filter_by(participacion_id=participacion_id)
                .with_for_update()
                .first()
            )

            # No liberar una participación con un pago
            # aprobado o que necesita revisión.
            if pago is None or pago.estado != "pendiente":
                db.session.rollback()
                continue

            numeros = (
                Numero.query
                .filter_by(
                    participacion_id=participacion_id
                )
                .with_for_update()
                .all()
            )

            # No liberar reservas incompletas ni números vendidos.
            if (
                len(numeros) != participacion.cantidad
                or any(
                    numero.estado != "reservado"
                    for numero in numeros
                )
            ):
                db.session.rollback()
                continue

            for numero in numeros:
                numero.estado = "disponible"
                numero.participacion_id = None

            participacion.estado = "vencido"
            pago.estado = "vencido"

            db.session.commit()

            print(
                f"Participación {participacion_id} vencida. "
                f"Números liberados: {len(numeros)}."
            )

        except Exception:
            db.session.rollback()
            raise
