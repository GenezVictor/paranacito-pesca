from extensions import db


class Pack(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)

    activo = db.Column(db.Boolean, nullable=False, default=True)
    orden = db.Column(db.Integer, nullable=False, default=0)

    sorteo_id = db.Column(
        db.Integer,
        db.ForeignKey("sorteo.id"),
        nullable=False
    )
