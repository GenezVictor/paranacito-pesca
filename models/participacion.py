from extensions import db
from datetime import datetime


class Participacion(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        nullable=False
    )

    telefono = db.Column(
        db.String(30),
        nullable=False
    )

    cantidad = db.Column(
        db.Integer,
        nullable=False
    )

    pack_nombre = db.Column(
        db.String(100),
        nullable=True
    )

    pack_precio = db.Column(
        db.Float,
        nullable=True
    )

    estado = db.Column(
        db.String(20),
        nullable=False,
        default="reservado"
    )

    fecha_creacion = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now
    )

    fecha_expiracion = db.Column(
        db.DateTime,
        nullable=True
    )

    sorteo_id = db.Column(
        db.Integer,
        db.ForeignKey("sorteo.id"),
        nullable=False
    )

    def __repr__(self):
        return f"<Participacion {self.id} - {self.nombre}>"
