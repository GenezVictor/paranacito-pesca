import unittest
from unittest.mock import patch

from app import app


class TestWebhookMercadoPago(unittest.TestCase):

    def setUp(self):
        self.cliente = app.test_client()
        self.url = "/webhook/mercadopago"
        self.datos = {
            "type": "payment",
            "data": {"id": "789"}
        }

    def enviar(self):
        return self.cliente.post(
            self.url,
            json=self.datos
        )

    def test_firma_invalida(self):
        with patch(
            "servicios.validar_webhook.validar_webhook",
            return_value=False
        ):
            respuesta = self.enviar()

        self.assertEqual(respuesta.status_code, 401)

    def test_error_consultando_mercado_pago(self):
        with (
            patch(
                "servicios.validar_webhook.validar_webhook",
                return_value=True
            ),
            patch(
                "app.consultar_pago",
                side_effect=ConnectionError("Sin conexión")
            )
        ):
            respuesta = self.enviar()

        self.assertEqual(respuesta.status_code, 503)

    def test_pago_pendiente(self):
        with (
            patch(
                "servicios.validar_webhook.validar_webhook",
                return_value=True
            ),
            patch(
                "app.consultar_pago",
                return_value={
                    "status": 200,
                    "response": {"status": "pending"}
                }
            ),
            patch("app.procesar_pago_aprobado") as procesar
        ):
            respuesta = self.enviar()

        self.assertEqual(respuesta.status_code, 200)
        procesar.assert_not_called()

    def test_pago_aprobado(self):
        with (
            patch(
                "servicios.validar_webhook.validar_webhook",
                return_value=True
            ),
            patch(
                "app.consultar_pago",
                return_value={
                    "status": 200,
                    "response": {"status": "approved"}
                }
            ),
            patch(
                "app.procesar_pago_aprobado",
                return_value=True
            ) as procesar
        ):
            respuesta = self.enviar()

        self.assertEqual(respuesta.status_code, 200)
        procesar.assert_called_once()

    def test_confirmacion_fallida(self):
        with (
            patch(
                "servicios.validar_webhook.validar_webhook",
                return_value=True
            ),
            patch(
                "app.consultar_pago",
                return_value={
                    "status": 200,
                    "response": {"status": "approved"}
                }
            ),
            patch(
                "app.procesar_pago_aprobado",
                return_value=False
            )
        ):
            respuesta = self.enviar()

        self.assertEqual(respuesta.status_code, 503)


if __name__ == "__main__":
    unittest.main()
