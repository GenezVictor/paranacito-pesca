from extensions import db


class Multimedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sorteo_id = db.Column(
        db.Integer,
        db.ForeignKey("sorteo.id"),
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

    principal = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    orden = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    def __repr__(self):
        return f"<Multimedia {self.id} - {self.tipo}>"
