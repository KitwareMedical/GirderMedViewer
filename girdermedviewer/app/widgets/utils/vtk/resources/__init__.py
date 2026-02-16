from pathlib import Path


def resources_path() -> Path:
    return Path(__file__).parent


__all__ = [
    "resources_path",
]
