import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from sqlalchemy import column

from servicios import verificador_pagos as modulo


class TestVerificadorPagos(unittest.TestCase):

    def setUp(self):
        self.pago = SimpleNamespace(
            participacion_id=123,
            monto=1000.0
        )

    def ejecutar(self, respuesta=None, error=None):
        consulta = MagicMock()

        if error is not None:
            consulta.side_effect = error
        else:
            consulta.return_value = respuesta

        with patch.object(
            modulo,
            "Pago"
        ) as modelo_pago, patch.object(
            modulo,
            "buscar_pagos_por_referencia",
            consulta
        ), patch.object(
            modulo,
            "procesar_pago_aprobado"
        ) as procesar:

            # Expresiones SQL reales para construir la consulta.
            modelo_pago.estado = column("estado")
            modelo_pago.preferencia_id = column("preferencia_id")
            modelo_pago.participacion_id = column("participacion_id")

            with patch.object(modulo, "Participacion") as participacion:
                participacion.id = column("id")
                participacion.estado = column("estado_participacion")

                modelo_pago.query.join.return_value.filter.return_value.all.return_value = [
                    self.pago
                ]

                resultado = modulo.verificar_pagos_pendientes()

            procesar.assert_not_called()

            return resultado

    def test_consulta_incluye_pago_incierto_sin_preferencia(self):
        from sqlalchemy import column
        from sqlalchemy.dialects import postgresql
        from sqlalchemy.sql import select
        from models.pago import Pago
        from models.participacion import Participacion

        consulta = (
            select(Pago.id)
            .join(
                Participacion,
                Pago.participacion_id == Participacion.id
            )
            .where(
                Pago.estado == "pendiente",
                modulo.or_(
                    Pago.preferencia_id.isnot(None),
                    Participacion.estado == "pago_incierto"
                )
            )
        )

        sql = str(
            consulta.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True}
            )
        )

        self.assertIn("pago_incierto", sql)
        self.assertIn("IS NOT NULL", sql)
        self.assertIn(" OR ", sql)

    def test_procesamiento_devuelve_false(self):
        self.comprobar_fallo_procesamiento(resultado=False)

    def test_procesamiento_lanza_excepcion(self):
        self.comprobar_fallo_procesamiento(
            error=RuntimeError("Error al confirmar pago")
        )

    def comprobar_fallo_procesamiento(self, resultado=None, error=None):
        respuesta = {
            "status": 200,
            "response": {
                "results": [{
                    "id": 789,
                    "status": "approved",
                    "transaction_amount": 1000.0
                }]
            }
        }

        from sqlalchemy import column

        with (
            patch.object(modulo, "Pago") as modelo_pago,
            patch.object(modulo, "Participacion") as participacion,
            patch.object(
                modulo,
                "buscar_pagos_por_referencia",
                return_value=respuesta
            ),
            patch.object(modulo, "procesar_pago_aprobado") as procesar
        ):
            modelo_pago.estado = column("estado")
            modelo_pago.preferencia_id = column("preferencia_id")
            modelo_pago.participacion_id = column("participacion_id")

            participacion.id = column("id")
            participacion.estado = column("estado_participacion")

            consulta = modelo_pago.query.join.return_value
            consulta.filter.return_value.all.return_value = [self.pago]

            if error is not None:
                procesar.side_effect = error
            else:
                procesar.return_value = resultado

            protegidas = modulo.verificar_pagos_pendientes()

            procesar.assert_called_once()
            self.assertEqual(protegidas, {123})

    def test_error_de_conexion(self):
        resultado = self.ejecutar(
            error=ConnectionError("Sin conexión")
        )
        self.assertEqual(resultado, {123})

    def test_respuesta_invalida(self):
        resultado = self.ejecutar(
            respuesta={"status": 200, "response": None}
        )
        self.assertEqual(resultado, {123})

    def test_pago_aprobado_con_importe_diferente(self):
        resultado = self.ejecutar(
            respuesta={
                "status": 200,
                "response": {
                    "results": [
                        {
                            "id": 789,
                            "status": "approved",
                            "transaction_amount": 900.0
                        }
                    ]
                }
            }
        )
        self.assertEqual(resultado, {123})

    def test_sin_pagos(self):
        resultado = self.ejecutar(
            respuesta={
                "status": 200,
                "response": {"results": []}
            }
        )
        self.assertEqual(resultado, set())


if __name__ == "__main__":
    unittest.main()
