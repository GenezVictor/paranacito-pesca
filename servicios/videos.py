from urllib.parse import urlparse, parse_qs


def preparar_video(url):
    """
    Detecta el origen de un video y devuelve
    la información necesaria para mostrarlo.
    """

    if not url:
        return {
            "tipo": "externo",
            "url": ""
        }

    url = url.strip()
    parsed = urlparse(url)

    host = parsed.netloc.lower()
    path = parsed.path

    # YouTube normal:
    # youtube.com/watch?v=VIDEO_ID
    if "youtube.com" in host:
        video_id = parse_qs(
            parsed.query
        ).get("v", [None])[0]

        # También soporta /shorts/ID y /embed/ID
        if not video_id:
            partes = [
                parte
                for parte in path.split("/")
                if parte
            ]

            if len(partes) >= 2 and partes[0] in {
                "shorts",
                "embed"
            }:
                video_id = partes[1]

        if video_id:
            return {
                "tipo": "youtube",
                "url": (
                    "https://www.youtube.com/embed/"
                    f"{video_id}"
                )
            }

    # YouTube corto:
    # youtu.be/VIDEO_ID
    if "youtu.be" in host:
        video_id = path.strip("/").split("/")[0]

        if video_id:
            return {
                "tipo": "youtube",
                "url": (
                    "https://www.youtube.com/embed/"
                    f"{video_id}"
                )
            }

    # Vimeo
    if "vimeo.com" in host:
        partes = [
            parte
            for parte in path.split("/")
            if parte
        ]

        video_id = next(
            (
                parte
                for parte in reversed(partes)
                if parte.isdigit()
            ),
            None
        )

        if video_id:
            return {
                "tipo": "vimeo",
                "url": (
                    "https://player.vimeo.com/video/"
                    f"{video_id}"
                )
            }

    # Videos directos
    path_lower = path.lower()

    if path_lower.endswith(
        (".mp4", ".webm", ".ogg")
    ):
        return {
            "tipo": "directo",
            "url": url
        }

    # Cualquier otro origen queda como enlace externo.
    return {
        "tipo": "externo",
        "url": url
    }
