import os
from uuid import uuid4

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")


def obtener_cliente_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_BUCKET:
        raise RuntimeError("Faltan SUPABASE_URL, SUPABASE_KEY o SUPABASE_BUCKET en .env")

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def subir_archivo_supabase(archivo, carpeta="sorteos"):
    supabase = obtener_cliente_supabase()

    extension = archivo.filename.rsplit(".", 1)[-1].lower()
    nombre_archivo = f"{carpeta}/{uuid4()}.{extension}"

    contenido = archivo.read()

    supabase.storage.from_(SUPABASE_BUCKET).upload(
        nombre_archivo,
        contenido,
        {"content-type": archivo.content_type},
    )

    return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(nombre_archivo)


def eliminar_archivo_supabase(url):
    if not url or not url.startswith("http"):
        return False

    marcador = (
        f"/storage/v1/object/public/"
        f"{SUPABASE_BUCKET}/"
    )

    if marcador not in url:
        return False

    ruta_objeto = url.split(
        marcador,
        1
    )[1]

    if not ruta_objeto:
        return False

    supabase = obtener_cliente_supabase()

    supabase.storage.from_(
        SUPABASE_BUCKET
    ).remove(
        [ruta_objeto]
    )

    return True


def subir_comprobante_supabase(archivo):
    from io import BytesIO
    from PIL import Image

    extensiones_permitidas = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "pdf": "application/pdf"
    }

    if not archivo or not archivo.filename:
        raise ValueError("No se seleccionó ningún comprobante.")

    extension = archivo.filename.rsplit(".", 1)[-1].lower()

    if extension not in extensiones_permitidas:
        raise ValueError("Formato de comprobante no permitido.")

    contenido = archivo.read()

    if not contenido:
        raise ValueError("El archivo está vacío.")

    if len(contenido) > 5 * 1024 * 1024:
        raise ValueError("El comprobante no puede superar los 5 MB.")

    if extension == "pdf":
        if not contenido.startswith(b"%PDF-"):
            raise ValueError("El archivo PDF no es válido.")
    else:
        try:
            imagen = Image.open(BytesIO(contenido))
            imagen.verify()

            formatos = {
                "jpg": "JPEG",
                "jpeg": "JPEG",
                "png": "PNG",
                "webp": "WEBP"
            }

            if imagen.format != formatos[extension]:
                raise ValueError("El contenido no coincide con la extensión.")
        except ValueError:
            raise
        except Exception:
            raise ValueError("La imagen del comprobante no es válida.")

    nombre_archivo = f"transferencias/{uuid4()}.{extension}"

    cliente = obtener_cliente_supabase()

    bucket = os.getenv(
        "SUPABASE_BUCKET_COMPROBANTES",
        "comprobantes"
    )

    cliente.storage.from_(bucket).upload(
        nombre_archivo,
        contenido,
        {
            "content-type": extensiones_permitidas[extension],
            "upsert": "false"
        }
    )

    return nombre_archivo


def obtener_url_comprobante_supabase(ruta):
    cliente = obtener_cliente_supabase()

    bucket = os.getenv(
        "SUPABASE_BUCKET_COMPROBANTES",
        "comprobantes"
    )

    resultado = cliente.storage.from_(bucket).create_signed_url(
        ruta,
        600
    )

    return (
        resultado.get("signedURL")
        or resultado.get("signedUrl")
        or resultado.get("signed_url")
    )
