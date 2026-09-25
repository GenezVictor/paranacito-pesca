from extensions import db


class Sorteo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio_numero = db.Column(db.Float, nullable=False)
    max_numeros_por_persona = db.Column(db.Integer, nullable=False, default=1)
    cantidad_numeros = db.Column(db.Integer, nullable=False, default=100)
    activo = db.Column(db.Boolean, default=True)

    multimedia = db.relationship(
        "Multimedia",
        backref="sorteo",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Multimedia.orden"
    )

    def __repr__(self):
        return f"<Sorteo {self.titulo}>"
