from uuid import uuid4

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

    formato = validar_imagen(
        archivo
    )

    nombre_seguro = secure_filename(
        archivo.filename
    )

    extension = nombre_seguro.rsplit(
        ".",
        1
    )[1].lower()

    extensiones_por_formato = {
        "JPEG": {"jpg", "jpeg"},
        "PNG": {"png"},
        "WEBP": {"webp"}
    }

    if extension not in extensiones_por_formato[
        formato
    ]:
        raise ValueError(
            "La extensión del archivo no coincide "
            "con el contenido de la imagen."
        )

    nombre_nuevo = (
        f"sorteos/sorteo_{sorteo_id}/"
        f"{uuid4().hex}."
        f"{extension}"
    )

    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp"
    }

    archivo.stream.seek(0)
    contenido = archivo.read()

    supabase = obtener_cliente_supabase()

    supabase.storage.from_(SUPABASE_BUCKET).upload(
        nombre_nuevo,
        contenido,
        {
            "content-type": content_types[extension]
        }
    )

    return supabase.storage.from_(
        SUPABASE_BUCKET
    ).get_public_url(
        nombre_nuevo
    )
