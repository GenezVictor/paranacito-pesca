import re
from urllib.parse import urlparse, parse_qs


PATRON_ID_YOUTUBE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
PATRON_ID_VIMEO = re.compile(r"^\d+$")


def preparar_video_ganador(url):
    if not url:
        return {"tipo": "externo", "url": ""}

    url = url.strip()

    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        puerto = parsed.port
    except ValueError:
        return {"tipo": "externo", "url": ""}

    if (
        parsed.scheme not in ("http", "https")
        or not host
        or parsed.username
        or parsed.password
    ):
        return {"tipo": "externo", "url": ""}

    def pertenece_a(dominio):
        return host == dominio or host.endswith("." + dominio)

    # YouTube
    if pertenece_a("youtube.com"):
        video_id = parse_qs(parsed.query).get("v", [None])[0]

        if not video_id:
            partes = [p for p in parsed.path.split("/") if p]

            if len(partes) >= 2 and partes[0] in ("shorts", "embed"):
                video_id = partes[1]

        if video_id and PATRON_ID_YOUTUBE.fullmatch(video_id):
            return {
                "tipo": "youtube",
                "url": f"https://www.youtube.com/embed/{video_id}"
            }

    # YouTube corto
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]

        if PATRON_ID_YOUTUBE.fullmatch(video_id):
            return {
                "tipo": "youtube",
                "url": f"https://www.youtube.com/embed/{video_id}"
            }

    # Vimeo
    if pertenece_a("vimeo.com"):
        partes = [p for p in parsed.path.split("/") if p]
        video_id = next(
            (p for p in reversed(partes) if PATRON_ID_VIMEO.fullmatch(p)),
            None
        )

        if video_id:
            return {
                "tipo": "vimeo",
                "url": f"https://player.vimeo.com/video/{video_id}"
            }

    # Videos alojados directamente
    if parsed.path.lower().endswith((".mp4", ".webm", ".ogg")):
        return {
            "tipo": "directo",
            "url": url
        }

    return {
        "tipo": "externo",
        "url": url
    }
