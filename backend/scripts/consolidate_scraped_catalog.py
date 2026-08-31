"""Consolida un catálogo scrapeado a **una Referencia por SKU** (D-89).

Un sitio de repuestos publica **un anuncio por cada moto compatible**, todos con
el mismo código de pieza: la culata `VA10300` aparece 7 veces —CBF125, CBF150,
RTX150…— porque es literalmente la misma culata. Importar eso tal cual rompe el
inventario, no la estética: un `Item` (unidad física) apunta a UNA `Reference`,
así que 20 culatas recibidas quedan bajo una de las 7 y las otras 6 muestran
cero stock; buscar "CBF150 culata" en la caja encuentra la que no tiene
existencias, y el histórico de ventas se parte en 7 productos, con lo que "top
productos" y "reponer ya" del tablero (D-66/D-69) quedan mal.

**Por qué acá y no en el importador.** D-73 fija que la importación *suma,
nunca fusiona*, y la convención `<MODELO> - <PIEZA>` es de **este sitio**, no de
todos los clientes: hornearla en el motor genérico sería meter el formato de un
proveedor dentro del producto. Esto es preparación del archivo, y su lugar es
`scripts/`, junto a `import_scraped_references.py`.

**La compatibilidad no se pierde, se estaciona.** Los modelos de moto se
acumulan en `description` como una línea `Compatible: …`, que es lo que ya
insinuaba `import_scraped_references.py` con su `description or
compatible_model`. Cuando exista **A-22** (Módulo 3 — `SpecProfile` +
`ReferenceCompatibility`, diferido post-DIAN y posicionado como plan superior,
D-44) el dato se parsea desde ahí. No se adelanta el módulo: se conserva la
materia prima.

**Un SKU, una fila** en el archivo de Referencias: es identidad, y códigos
inventados tipo `SKU-2` ensucian el catálogo con algo que no existe en ningún
lado. Cuando un mismo código del sitio cubre piezas realmente distintas
—`41080-0578-11H` es a la vez DISCO FRENO DELANTERO ($93.900) y TRASERO
($154.900)— se queda la variante con más anuncios y **las demás se apartan a un
segundo archivo `_productos.xlsx`**: no se descartan, quedan listas para
cargarlas cuando exista la importación de Productos (**A-30**), donde el SKU
repetido sí tiene semántica propia (cada repetición = una unidad, D-41).

Uso, desde `backend/`:

    python -m scripts.consolidate_scraped_catalog ENTRADA.xlsx SALIDA.xlsx
    python -m scripts.consolidate_scraped_catalog ENTRADA.xlsx SALIDA.xlsx --iva 0

Genera `SALIDA.xlsx` y, si hubo variantes apartadas, `SALIDA_productos.xlsx`.

Las filas **sin SKU** no se fusionan entre sí: sin código no hay evidencia de
que dos anuncios sean la misma pieza. Cada una recibe su `GEN-` determinista en
la importación (D-86), único porque conservan el título completo.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.core.money import parse_money
from app.core.sku import normalize_sku

DEFAULT_IVA = Decimal("19")

#  `<MODELO DE MOTO> - <NOMBRE DE LA PIEZA>`: el 99% de los títulos del sitio
#  sigue esta forma.
#
#  `.*` **greedy**, o sea corta en el ÚLTIMO guion, no en el primero. El modelo
#  suele traer guiones propios ("XTZ - R 150 - Balancines VITRIX") y cortar en
#  el primero dejaba `R 150 - Balancines VITRIX` como nombre de pieza, distinto
#  de `Balancines VITRIX` de la fila de al lado: una pieza partida en dos por un
#  guion. Medido sobre el catálogo real, el último guion baja los SKU partidos
#  de 26 a 11 — los 15 restantes son separaciones legítimas.
TITLE_PATTERN = re.compile(r"^(.*)\s*-\s*(.+)$")

#  Un código de pieza real **siempre trae al menos un dígito** en este catálogo
#  (`VH50013`, `164CB`, `CADI156S20V2`, `41080-0578-11H`). Los que no lo traen
#  son errores de la fuente: el scraper levantó una palabra suelta en vez del
#  código — `Kit`, `Cadena`, `Sellos`, `Disco FrenoD`. Se tratan como **SKU
#  vacío** para que reciban su `GEN-` determinista (D-86) en vez de fusionar
#  productos que no tienen nada que ver: los 3 anuncios con SKU `Kit` eran kits
#  de arrastre de DUCATI, HONDA y KAWASAKI, tres productos distintos.
HAS_DIGIT = re.compile(r"\d")

OUTPUT_COLUMNS = (
    "sku", "title", "brand", "category", "price_offer",
    "description", "image_url", "iva_percentage", "provider_price",
)


def _split_title(title: str) -> tuple[str | None, str]:
    """`"CBF125 - Culata VITRIX"` → `("CBF125", "Culata VITRIX")`."""
    match = TITLE_PATTERN.match(title or "")
    if not match:
        return None, (title or "").strip()
    return match.group(1).strip() or None, match.group(2).strip()


def _fold(text: str) -> str:
    """Nombre de pieza → forma comparable, para que 'Válvulas ' y 'valvulas' agrupen juntas."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped).strip().lower()


def _most_common(values) -> str:
    """El valor no vacío que más se repite; `""` si no hay ninguno."""
    counter = Counter(v.strip() for v in values if v and str(v).strip())
    return counter.most_common(1)[0][0] if counter else ""


def consolidate(source: Path, iva: Decimal) -> tuple[list[dict], dict]:
    sheet = load_workbook(source, data_only=True).active
    rows = list(sheet.iter_rows(values_only=True))
    header = [str(c or "").strip() for c in rows[0]]
    index = {name: header.index(name) for name in header}

    def cell(row, name: str) -> str:
        position = index.get(name)
        if position is None or position >= len(row) or row[position] is None:
            return ""
        return str(row[position]).strip()

    #  Se agrupa por **(SKU normalizado, nombre de pieza)**, no por SKU solo.
    #
    #  Normalizado (D-85) porque es la forma con la que el importador va a
    #  comparar: agrupar por el crudo dejaría `AB 1` y `AB-1` en grupos
    #  distintos que colisionan igual al importar.
    #
    #  Y con el nombre de pieza porque un mismo código del sitio puede cubrir
    #  piezas realmente distintas — `41080-0578-11H` es a la vez DISCO FRENO
    #  DELANTERO ($93.900) y TRASERO ($154.900) — y fusionarlas borraría un
    #  producto. Que el nombre coincida es la evidencia de que es la misma
    #  pieza; que no coincida, de que no lo es. **El sesgo es deliberado:**
    #  separar de más deja dos fichas parecidas que se revisan a ojo, fusionar
    #  de más borra un producto y nadie se entera.
    #
    #  Las filas **sin SKU** se agrupan por su título **completo**, no por el
    #  nombre de pieza recortado, y por eso conservan el prefijo de modelo.
    #
    #  El SKU es lo que prueba que dos anuncios son la misma pieza; sin él no
    #  hay tal evidencia y fusionar por nombre es adivinar. Medido: agrupar
    #  esas 92 filas por marca+pieza las bajaba a 42 pero metía en un mismo
    #  producto precios de $507.900 a $744.900 — piezas distintas de motos
    #  distintas que comparten un nombre genérico.
    #
    #  Conservar el título entero además mantiene único el `GEN-` que les
    #  asigna el importador (D-86), porque su semilla es marca+título:
    #  recortarlo dejaba "CBF125 - Válvulas" y "CB110 - Válvulas" como
    #  "Válvulas" y les daba **el mismo** código, rompiendo la unicidad que
    #  este script existe para garantizar. Sí se agrupan los duplicados
    #  exactos (mismo título y marca), que son seguros.
    report = {
        "price_conflicts": [], "displaced": [], "merged": 0, "generated": 0,
        "discarded_skus": Counter(),
    }

    grouped: dict[tuple[str, str], list] = defaultdict(list)
    for row in rows[1:]:
        key = normalize_sku(cell(row, "sku"))
        if key and not HAS_DIGIT.search(key):
            report["discarded_skus"][key] += 1
            key = ""
        if key:
            _, part = _split_title(cell(row, "title"))
            grouped[(key, _fold(part))].append(row)
        else:
            grouped[("", f"{_fold(cell(row, 'brand'))}|{_fold(cell(row, 'title'))}")].append(row)

    output: list[dict] = []
    displaced_output: list[dict] = []

    by_sku: dict[str, list[tuple[str, list]]] = defaultdict(list)
    for (sku, folded), group in grouped.items():
        by_sku[sku].append((folded, group))

    #  **Un SKU, una fila** en el archivo de Referencias — sin códigos
    #  inventados. Cuando un mismo código cubre piezas distintas
    #  (`41080-0578-11H` = disco delantero Y trasero) se queda la variante con
    #  más anuncios y las demás **se apartan al archivo de Productos**, no se
    #  descartan: el dato sobrevive para cargarlo cuando exista la importación
    #  de Productos (A-30), donde el SKU repetido sí tiene semántica propia.
    #
    #  Desempate por nombre de pieza cuando dos variantes tienen la misma
    #  cantidad de anuncios: sin eso, dos corridas del mismo insumo podrían
    #  elegir distinto según el orden del diccionario.
    resolved: list[tuple[str, list]] = []
    displaced: list[tuple[str, list]] = []
    for sku, variants in by_sku.items():
        if not sku:
            #  Sin SKU no hay código que compartir: cada grupo es su propia
            #  Referencia y ninguna desplaza a otra. El `GEN-` lo pone el
            #  importador (D-86), único porque la semilla es marca+título.
            resolved.extend(("", group) for _, group in variants)
            report["generated"] = len(variants)
            continue
        variants.sort(key=lambda pair: (-len(pair[1]), pair[0]))
        resolved.append((sku, variants[0][1]))
        displaced.extend((sku, group) for _, group in variants[1:])
        if len(variants) > 1:
            names = [_most_common(_split_title(cell(r, "title"))[1] for r in g) for _, g in variants]
            report["displaced"].append((sku, names))

    def build_row(sku: str, group: list) -> dict | None:
        """Un grupo de anuncios → una fila de salida. `None` si no tiene precio legible."""
        prices = []
        for row in group:
            try:
                prices.append(parse_money(cell(row, "price_offer")))
            except ValueError:
                continue
        if not prices:
            return None
        #  Gana el precio MÁS ALTO cuando el sitio publica varios para el mismo
        #  código: vender por debajo es el error caro, y son pocos casos —
        #  quedan listados en el reporte para revisarlos a mano.
        price = max(prices)
        if len(set(prices)) > 1:
            report["price_conflicts"].append((sku, sorted(set(prices))))

        models: list[str] = []
        if sku:
            #  Con SKU: el nombre es la pieza sola y los modelos se acumulan
            #  como compatibilidad — es la consolidación que motiva el script.
            part_names = []
            for row in group:
                model, part = _split_title(cell(row, "title"))
                if model and model not in models:
                    models.append(model)
                if part:
                    part_names.append(part)
            title = _most_common(part_names) or sku
        else:
            #  Sin SKU: el título va entero (incluido el modelo) y no hay lista
            #  de compatibilidad que armar — el grupo es una sola fila del sitio.
            title = _most_common(cell(r, "title") for r in group)

        #  Se conserva la descripción más completa del grupo, no la primera:
        #  los anuncios del sitio varían y quedarse con la más corta tira dato.
        description = max((cell(r, "description") for r in group), key=len, default="")
        if models:
            compatible = "Compatible: " + ", ".join(models)
            description = f"{description}\n{compatible}".strip() if description else compatible

        base = (price / (Decimal(1) + iva / Decimal(100))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return {
            "sku": sku,
            "title": title,
            "brand": _most_common(cell(r, "brand") for r in group),
            "category": _most_common(cell(r, "category") for r in group),
            "price_offer": float(price),
            "description": description,
            "image_url": _most_common(cell(r, "image_url") for r in group),
            "iva_percentage": float(iva),
            "provider_price": float(base),
        }

    for sku, group in resolved:
        row = build_row(sku, group)
        if row is None:
            continue
        if len(group) > 1:
            report["merged"] += len(group) - 1
        output.append(row)

    for sku, group in displaced:
        row = build_row(sku, group)
        if row is not None:
            displaced_output.append(row)

    return output, displaced_output, report


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(list(OUTPUT_COLUMNS))
    for row in rows:
        sheet.append([row[column] for column in OUTPUT_COLUMNS])
    workbook.save(path)


def main(source: Path, destination: Path, products: Path | None, iva: Decimal) -> None:
    rows, displaced, report = consolidate(source, iva)
    _write(destination, rows)

    #  Segundo archivo solo si hay algo que poner: no tiene sentido dejar un
    #  .xlsx con puros encabezados si ningún SKU cubría piezas distintas.
    products_path = products or destination.with_name(
        f"{destination.stem}_productos{destination.suffix}"
    )
    if displaced:
        _write(products_path, displaced)

    print(f"Referencias: {destination}")
    print(f"  Filas de salida       : {len(rows)}  (un SKU, una fila)")
    print(f"  Filas fusionadas      : {report['merged']}")
    print(f"  Sin SKU (reciben GEN-): {report['generated']}")
    print(f"  IVA aplicado          : {iva}%")
    if displaced:
        print(f"\nUnidades / Productos (para cargar luego, A-30): {products_path}")
        print(f"  Variantes apartadas   : {len(displaced)}")

    if report["discarded_skus"]:
        total = sum(report["discarded_skus"].values())
        print(f"\n  [i] {total} filas traian un SKU sin digitos (error de la fuente) - se vaciaron para que reciban GEN-:")
        for value, count in report["discarded_skus"].most_common():
            print(f"      {value!r} x{count}")

    #  Marcadores ASCII y no simbolos: la consola de Windows usa cp1252 por
    #  defecto y un caracter fuera de esa tabla tumba el print con
    #  UnicodeEncodeError DESPUES de haber escrito el archivo — el peor momento.
    if report["price_conflicts"]:
        print(f"\n  [!] {len(report['price_conflicts'])} SKU con precios distintos - se tomo el mayor:")
        for sku, prices in report["price_conflicts"][:10]:
            print(f"      {sku}: {' / '.join(f'{p:,.0f}' for p in prices)}")
        if len(report["price_conflicts"]) > 10:
            print(f"      … y {len(report['price_conflicts']) - 10} más")

    if report["displaced"]:
        print(f"\n  [i] {len(report['displaced'])} SKU cubrian piezas distintas - queda la 1a, el resto va al archivo de productos:")
        for sku, names in report["displaced"][:10]:
            print(f"      {sku}: {' | '.join(n[:36] for n in names)}")
        if len(report["displaced"]) > 10:
            print(f"      ... y {len(report['displaced']) - 10} mas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("source", type=Path, help="Excel scrapeado (una fila por anuncio)")
    parser.add_argument("destination", type=Path, help="Excel de Referencias a generar (un SKU, una fila)")
    parser.add_argument(
        "--productos", type=Path, default=None,
        help="Ruta del Excel de unidades/Productos (default: <destino>_productos.xlsx)",
    )
    parser.add_argument(
        "--iva", type=Decimal, default=DEFAULT_IVA,
        help="IVA incluido en el precio scrapeado (default 19; usar 0 para no derivar)",
    )
    args = parser.parse_args()
    if not args.source.exists():
        print(f"No existe el archivo: {args.source}", file=sys.stderr)
        sys.exit(1)
    main(args.source, args.destination, args.productos, args.iva)
