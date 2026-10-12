import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from servicios import procesar_pagos as modulo


class TestPagosDuplicados(unittest.TestCase):

    def probar_pago(self, id_original, id_recibido):
        participacion = SimpleNamespace(id=123)
        pago = SimpleNamespace(
            estado="aprobado",
            id_externo=id_original,
            monto=1000.0
        )

        with patch.object(modulo, "Participacion") as P, \
             patch.object(modulo, "Pago") as G, \
             patch.object(modulo, "Numero") as N, \
             patch.object(modulo, "db") as db:

            P.query.filter_by.return_value.with_for_update.return_value.first.return_value = participacion
            G.query.filter_by.return_value.with_for_update.return_value.first.return_value = pago

            resultado = modulo.procesar_pago_aprobado(
                id_recibido,
                {
                    "status": "approved",
                    "external_reference": "123",
                    "transaction_amount": 1000.0
                }
            )

            db.session.commit.assert_not_called()
            db.session.rollback.assert_called_once()
            N.query.filter_by.assert_not_called()

            return resultado, pago.id_externo

    def test_mismo_pago_no_se_repite(self):
        resultado, id_guardado = self.probar_pago("456", "456")
        self.assertTrue(resultado)
        self.assertEqual(id_guardado, "456")

    def test_pago_diferente_no_sobrescribe(self):
        resultado, id_guardado = self.probar_pago("456", "789")
        self.assertFalse(resultado)
        self.assertEqual(id_guardado, "456")


if __name__ == "__main__":
    unittest.main()
