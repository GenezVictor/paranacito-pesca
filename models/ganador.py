from datetime import date

from extensions import db


class Ganador(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(
        db.String(150),
        nullable=False
    )

    descripcion = db.Column(
        db.Text,
        nullable=True
    )

    fecha = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )

    activo = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    multimedia = db.relationship(
        "GanadorMultimedia",
        backref="ganador",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="GanadorMultimedia.orden"
    )

    def __repr__(self):
        return f"<Ganador {self.titulo}>"


class GanadorMultimedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    ganador_id = db.Column(
        db.Integer,
        db.ForeignKey("ganador.id"),
        nullable=False
    )

    tipo = db.Column(
        db.String(20),
        nullable=False
    )

    url = db.Column(
        db.String(500),
        nullable=False
    )

    orden = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    def __repr__(self):
        return f"<GanadorMultimedia {self.id} - {self.tipo}>"
