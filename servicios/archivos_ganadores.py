from io import BytesIO
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from servicios.supabase_storage import (
    obtener_cliente_supabase,
    SUPABASE_BUCKET,
)


EXTENSIONES_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}

FORMATOS_PERMITIDOS = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
}


def guardar_imagen_ganador(archivo):
    if not archivo or not archivo.filename:
        raise ValueError("No se seleccionó ninguna imagen.")

    if "." not in archivo.filename:
        raise ValueError("El archivo no tiene una extensión válida.")

    extension = archivo.filename.rsplit(".", 1)[1].lower()

    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValueError("Formato no permitido. Usá JPG, JPEG, PNG o WEBP.")

    try:
        archivo.stream.seek(0)
        imagen = Image.open(archivo.stream)

        if imagen.format != FORMATOS_PERMITIDOS[extension]:
            raise ValueError("El contenido de la imagen no coincide con su extensión.")

        imagen.verify()
        archivo.stream.seek(0)

        imagen = Image.open(archivo.stream)

        if imagen.mode not in ("RGB", "RGBA"):
            imagen = imagen.convert("RGB")

        imagen.thumbnail((1920, 1920), Image.Resampling.LANCZOS)

        salida = BytesIO()
        imagen.save(
            salida,
            format="WEBP",
            quality=82,
            method=6
        )

        contenido = salida.getvalue()

    except ValueError:
        raise
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("La imagen no es válida o no se pudo procesar.") from error

    if not contenido:
        raise ValueError("No se pudo procesar la imagen.")

    if len(contenido) > 5 * 1024 * 1024:
        raise ValueError("La imagen supera los 5 MB después de comprimirla.")

    nombre_archivo = f"ganadores/{uuid4().hex}.webp"

    supabase = obtener_cliente_supabase()

    supabase.storage.from_(SUPABASE_BUCKET).upload(
        nombre_archivo,
        contenido,
        {"content-type": "image/webp"}
    )

    return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(
        nombre_archivo
    )
