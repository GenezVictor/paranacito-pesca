from uuid import uuid4
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from servicios.supabase_storage import obtener_cliente_supabase, SUPABASE_BUCKET


EXTENSIONES_IMAGEN = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

FORMATOS_IMAGEN = {
    "JPEG",
    "PNG",
    "WEBP"
}


def extension_permitida(nombre_archivo):

    if "." not in nombre_archivo:
        return False

    extension = nombre_archivo.rsplit(
        ".",
        1
    )[1].lower()

    return extension in EXTENSIONES_IMAGEN


def validar_imagen(archivo):

    try:

        archivo.stream.seek(0)

        imagen = Image.open(
            archivo.stream
        )

        formato = imagen.format

        imagen.verify()

        archivo.stream.seek(0)

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ):

        archivo.stream.seek(0)

        raise ValueError(
            "El archivo no es una imagen válida."
        )

    if formato not in FORMATOS_IMAGEN:

        raise ValueError(
            "Formato de imagen no permitido."
        )

    return formato


def guardar_imagen(archivo, sorteo_id):

    if not archivo or not archivo.filename:
        raise ValueError(
            "No se recibió ninguna imagen."
        )

    if not extension_permitida(
        archivo.filename
    ):
        raise ValueError(
            "Formato no permitido. "
            "Usá JPG, JPEG, PNG o WEBP."
        )

    validar_imagen(archivo)

    # Abrimos nuevamente la imagen después de validarla.
    archivo.stream.seek(0)

    try:
        imagen = Image.open(archivo.stream)

        # Corrige imágenes con modos incompatibles con WEBP.
        if imagen.mode not in ("RGB", "RGBA"):
            imagen = imagen.convert("RGB")

        # Evita subir imágenes con dimensiones excesivas.
        imagen.thumbnail(
            (1920, 1920),
            Image.Resampling.LANCZOS
        )

        salida = BytesIO()

        imagen.save(
            salida,
            format="WEBP",
            quality=82,
            method=6
        )

        contenido = salida.getvalue()

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ) as error:
        raise ValueError(
            "No se pudo procesar la imagen."
        ) from error

    # Límite de seguridad antes de enviar a Supabase.
    limite_bytes = 5 * 1024 * 1024

    if len(contenido) > limite_bytes:
        raise ValueError(
            "La imagen sigue siendo demasiado grande "
            "después de comprimirla."
        )

    nombre_nuevo = (
        f"sorteos/sorteo_{sorteo_id}/"
        f"{uuid4().hex}.webp"
    )

    supabase = obtener_cliente_supabase()

    supabase.storage.from_(SUPABASE_BUCKET).upload(
        nombre_nuevo,
        contenido,
        {
            "content-type": "image/webp"
        }
    )

    return supabase.storage.from_(
        SUPABASE_BUCKET
    ).get_public_url(
        nombre_nuevo
    )
