from datetime import datetime, timezone


def ahora_utc():
    """Devuelve la fecha y hora actual en UTC sin timezone."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
