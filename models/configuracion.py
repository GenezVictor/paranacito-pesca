from extensions import db


class ConfiguracionBancaria(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    titular = db.Column(
        db.String(150),
        nullable=False,
        default=""
    )

    cbu = db.Column(
        db.String(22),
        nullable=False,
        default=""
    )

    alias = db.Column(
        db.String(100),
        nullable=False,
        default=""
    )
