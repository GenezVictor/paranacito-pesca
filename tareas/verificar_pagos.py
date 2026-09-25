import sys
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))

from app import app
from servicios.verificador_pagos import verificar_pagos_pendientes
from servicios.vencimientos import liberar_participaciones_vencidas


if __name__ == "__main__":
    with app.app_context():

        print("Iniciando tareas automáticas...")

        liberar_participaciones_vencidas()

        verificar_pagos_pendientes()

        print("Tareas automáticas finalizadas.")
