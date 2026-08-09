"""Reglas de precio compartidas por la API.

Vive acá y no dentro de un router porque más de una pantalla necesita el precio
de venta (grilla de Productos, carrusel de recién agregados, seeds). Duplicar
una fórmula de dinero es duplicar el bug el día que cambie la regla de redondeo
— y los cálculos financieros son zona de alto riesgo del proyecto (CLAUDE.md).
"""
from decimal import ROUND_HALF_UP, Decimal

#  El precio de venta se redondea al múltiplo de $50 más cercano (D-46).
PRICE_ROUNDING_STEP = Decimal("50")


def sale_price(base_price: Decimal, iva_percentage: Decimal) -> Decimal:
    """
    Precio de venta con IVA del catálogo: `base_price × (1 + iva/100)`
    redondeado al múltiplo de $50 más cercano (D-45/D-46).

    Se calcula y no se lee de una columna porque `Reference.sale_price` —que
    D-45 define como valor derivado y **persistido**— todavía no existe en el
    esquema. Mientras tanto ésta es la única implementación de la fórmula:
    cuando se agregue la columna, los consumidores deben leerla en vez de
    recalcularla, para que catálogo y existencias no puedan divergir.

    Aritmética decimal exacta de punta a punta (regla del proyecto): `Numeric`
    de SQLAlchemy ya entrega `Decimal`, y nunca se pasa por `float`.
    """
    con_iva = base_price * (Decimal(1) + iva_percentage / Decimal(100))
    pasos = (con_iva / PRICE_ROUNDING_STEP).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return pasos * PRICE_ROUNDING_STEP
