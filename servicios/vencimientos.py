from datetime import datetime

from extensions import db
from models.participacion import Participacion
from models.numero import Numero
from models.pago import Pago


def liberar_participaciones_vencidas():

    ahora = datetime.now()

    participaciones = Participacion.query.filter(
        Participacion.estado == "reservado",
        Participacion.fecha_expiracion <= ahora
    ).all()

    if not participaciones:
        return

    for participacion in participaciones:

        numeros = Numero.query.filter_by(
            participacion_id=participacion.id
        ).all()

        for numero in numeros:
            numero.estado = "disponible"
            numero.participacion_id = None

        participacion.estado = "vencido"

        pago = Pago.query.filter_by(
            participacion_id=participacion.id
        ).first()

        if pago:
            pago.estado = "vencido"

    db.session.commit()