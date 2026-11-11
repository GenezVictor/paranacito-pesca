from app import app
from extensions import db
from models.ganador import Ganador, GanadorMultimedia

with app.app_context():
    db.create_all()

    print("Tablas de Ganadores creadas correctamente.")
    print(" - ganador")
    print(" - ganador_multimedia")
