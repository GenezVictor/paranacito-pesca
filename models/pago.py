from extensions import db


class Pago(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    participacion_id = db.Column(
        db.Integer,
        db.ForeignKey("participacion.id"),
        nullable=False
    )

    monto = db.Column(
        db.Float,
        nullable=False
    )

    estado = db.Column(
        db.String(20),
        nullable=False,
        default="pendiente"
    )

    metodo = db.Column(
        db.String(30),
        nullable=False,
        default="mercado_pago"
    )

    preferencia_id = db.Column(
        db.String(100),
        nullable=True
    )

    id_externo = db.Column(
        db.String(100),
        nullable=True
    )

    def __repr__(self):
        return f"<Pago {self.id} - {self.estado}>"
