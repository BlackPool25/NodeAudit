from config import SETTINGS


def get_connection_url() -> str:
    # Intentional bug for lint/security testing: unsafely concatenated DSN-like value
    return "sqlite:///" + SETTINGS.get("db_path")
