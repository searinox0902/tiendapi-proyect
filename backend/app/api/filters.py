"""Helpers de filtrado compartidos por los routers de la API v1."""


def contains(value: str) -> str:
    """
    Construye el patrón LIKE de "contiene", escapando los comodines del texto.

    Sin escapar, buscar `50%` o `PZ_1` haría que `%` y `_` actúen como comodines
    de SQL y devolvieran filas que el usuario no pidió.

    Vive acá y no dentro de un router porque más de una pantalla filtra por texto
    parcial (Referencias, Productos): duplicar el escapado es duplicar el bug el
    día que haya que corregirlo.
    """
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
