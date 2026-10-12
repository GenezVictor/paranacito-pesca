import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from servicios import vencimientos as v


class TestVencimientos(unittest.TestCase):

    def probar(self, excluidos=(), estado_pago="pendiente",
               estados=("reservado", "reservado"), cantidad=2):
        p = SimpleNamespace(
            estado="reservado",
            cantidad=cantidad,
            fecha_expiracion=v.ahora_utc()
        )
        pago = SimpleNamespace(estado=estado_pago)
        numeros = [
            SimpleNamespace(estado=e, participacion_id=123)
            for e in estados
        ]

        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.all.return_value = [(123,)]

        with patch.object(v, "db") as db, \
             patch.object(v, "Participacion") as P, \
             patch.object(v, "Pago") as G, \
             patch.object(v, "Numero") as N:
            P.fecha_expiracion.__le__.return_value = True
            db.session = sesion
            P.query.filter_by.return_value.with_for_update.return_value.first.return_value = p
            G.query.filter_by.return_value.with_for_update.return_value.first.return_value = pago
            N.query.filter_by.return_value.with_for_update.return_value.all.return_value = numeros

            v.liberar_participaciones_vencidas(excluir_ids=excluidos)
            return sesion.commit.call_count, p, pago, numeros

    def test_reserva_vencida_se_libera(self):
        commits, p, pago, nums = self.probar()

        self.assertEqual(commits, 1)
        self.assertEqual(p.estado, "vencido")
        self.assertEqual(pago.estado, "vencido")

        for numero in nums:
            self.assertEqual(numero.estado, "disponible")
            self.assertIsNone(numero.participacion_id)

    def test_reserva_protegida(self):
        commits, _, _, nums = self.probar(excluidos={123})
        self.assertEqual(commits, 0)
        self.assertEqual(nums[0].estado, "reservado")

    def test_pago_aprobado(self):
        commits, _, _, nums = self.probar(estado_pago="aprobado")
        self.assertEqual(commits, 0)
        self.assertEqual(nums[0].estado, "reservado")

    def test_pago_incierto_no_se_libera(self):
        with patch.object(v, "db") as db, \
             patch.object(v, "Participacion") as P:

            db.session.query.return_value.filter.return_value.all.return_value = []
            P.fecha_expiracion.__le__.return_value = True

            v.liberar_participaciones_vencidas()

            db.session.commit.assert_not_called()
            P.query.filter_by.assert_not_called()

    def test_reserva_incompleta(self):
        commits, _, _, nums = self.probar(estados=("reservado",))
        self.assertEqual(commits, 0)
        self.assertEqual(nums[0].estado, "reservado")


if __name__ == "__main__":
    unittest.main()
