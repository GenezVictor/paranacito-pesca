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
