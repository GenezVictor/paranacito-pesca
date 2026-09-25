from extensions import db


class Numero(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    numero = db.Column(
        db.Integer,
        nullable=False
    )

    estado = db.Column(
        db.String(20),
        default="disponible",
        nullable=False
    )

    sorteo_id = db.Column(
        db.Integer,
        db.ForeignKey("sorteo.id"),
        nullable=False
    )

    participacion_id = db.Column(
        db.Integer,
        db.ForeignKey("participacion.id"),
        nullable=True
    )

    def __repr__(self):
        return f"<Numero {self.numero}>"
