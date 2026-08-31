"""Importa Referencias de catálogo a partir de un JSON scrapeado con Firecrawl.

Flujo completo (desde `backend/`, con la BBDD levantada y migrada):

    1. Mapear el sitio para descubrir URLs de producto:
       firecrawl map <site> --limit 5000 --json -o scripts/scraped/urls.json

    2. Filtrar a mano/con script las URLs que son productos (no categorías,
       no cuenta, no carrito) y guardarlas una por línea en un .txt.

    3. Scrapear con extracción estructurada usando scrape_product_schema.json:
       firecrawl crawl <site> --include-paths "<patron-de-producto>/*" \
         --limit 500 --delay 500 --wait --progress \
         --scrape-options '{"formats":["json"],"jsonOptions":{"schema":"scripts/scrape_product_schema.json"}}' \
         -o scripts/scraped/products.json

    4. Revisar SIEMPRE una muestra de scripts/scraped/products.json a mano antes
       de importar: los precios y el IVA son zona de alto riesgo (CLAUDE.md) y
       este script solo puede *adivinar* si el precio scrapeado incluye IVA.

    5. Dry-run (no toca la BBDD, solo imprime qué crearía):
       python -m scripts.import_scraped_references scripts/scraped/products.json

    6. Confirmar e insertar:
       python -m scripts.import_scraped_references scripts/scraped/products.json --commit

Supuestos que DEBES verificar contra el sitio real antes de --commit:
  - Se asume que `price_offer` YA incluye IVA (normal en retail colombiano) y
    se calcula `base_price = price_offer / (1 + iva/100)`, con IVA por defecto
    19% (--iva para cambiarlo). Es una aproximación para poblar datos de
    desarrollo, no una fórmula de negocio — no reproduce el redondeo exacto
    que haya usado el sitio de origen.
  - Los productos scrapeados no tienen Proveedor real: se agrupan bajo un
    Provider placeholder ("Catálogo Externo (Scraping)") que este script crea
    si no existe. Reasígnalos a proveedores reales antes de ir a producción.
  - `sku`: si el sitio no expone uno, se genera un slug estable a partir del
    título + marca. Dos corridas del mismo input producen el mismo sku, así
    que --commit es idempotente (no duplica) mientras no cambie el título.
"""
import argparse
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.provider import Provider
from app.models.reference import Reference
from app.models.user import User

DEMO_EMAIL = "demo@tiendapi.co"
PLACEHOLDER_PROVIDER_TITLE = "Catálogo Externo (Scraping)"
DEFAULT_IVA = Decimal("19")


def _slugify_sku(title: str, brand: str | None) -> str:
    base = f"{brand or ''}-{title}".strip("-")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").upper()
    return f"SCR-{slug[:60]}"


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _load_scraped_products(path: Path) -> list[dict]:
    """Acepta tanto `{"data": [...]}` (salida típica de `firecrawl crawl --json`)
    como una lista plana `[...]`. Cada item puede traer el resultado bajo
    `json`, `extract` o `data.json` según la versión del CLI — se prueban
    todas las rutas conocidas."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("data", raw) if isinstance(raw, dict) else raw
    products = []
    for item in items:
        payload = item.get("json") or item.get("extract") or item.get("data", {}).get("json")
        if not payload:
            continue
        source_url = item.get("metadata", {}).get("sourceURL") or item.get("url")
        products.append({**payload, "_source_url": source_url})
    return products


def _ensure_provider(db, tenant_id) -> Provider:
    provider = db.execute(
        select(Provider).where(
            Provider.tenant_id == tenant_id, Provider.title == PLACEHOLDER_PROVIDER_TITLE
        )
    ).scalar_one_or_none()
    if provider is None:
        provider = Provider(
            tenant_id=tenant_id,
            title=PLACEHOLDER_PROVIDER_TITLE,
            description="Referencias importadas por scraping — reasignar a proveedor real antes de producción.",
        )
        db.add(provider)
        db.flush()
    return provider


def _ensure_category(db, tenant_id, name: str, cache: dict) -> Category | None:
    if not name:
        return None
    if name in cache:
        return cache[name]
    category = db.execute(
        select(Category).where(Category.tenant_id == tenant_id, Category.name == name)
    ).scalar_one_or_none()
    if category is None:
        category = Category(tenant_id=tenant_id, name=name)
        db.add(category)
        db.flush()
    cache[name] = category
    return category


def main(input_path: Path, commit: bool, iva: Decimal) -> None:
    products = _load_scraped_products(input_path)
    if not products:
        print(f"No se encontraron productos con datos extraídos en {input_path}")
        return
    print(f"Leídos {len(products)} productos scrapeados de {input_path}")

    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if user is None:
            print(f"No existe {DEMO_EMAIL}. Corre primero: python -m scripts.seed")
            return
        tenant_id = user.tenant_id

        existing_skus = {
            r.sku
            for r in db.execute(
                select(Reference.sku).where(Reference.tenant_id == tenant_id)
            ).scalars()
        }

        provider = _ensure_provider(db, tenant_id) if commit else None
        category_cache: dict = {}

        to_create, skipped, no_price = [], 0, 0
        for p in products:
            price = _to_decimal(p.get("price_offer"))
            if price is None:
                no_price += 1
                continue
            sku = p.get("sku") or _slugify_sku(p.get("title", ""), p.get("brand"))
            if sku in existing_skus:
                skipped += 1
                continue
            existing_skus.add(sku)

            base_price = (price / (Decimal(1) + iva / Decimal(100))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            to_create.append(
                {
                    "sku": sku,
                    "title": p.get("title", "").strip(),
                    "brand": p.get("brand"),
                    "description": p.get("description") or p.get("compatible_model"),
                    "image_url": p.get("image_url"),
                    "base_price": base_price,
                    "iva_percentage": iva,
                    "category_name": p.get("category"),
                    "_source_url": p.get("_source_url"),
                }
            )

        print(
            f"Nuevas: {len(to_create)} | Ya existían (sku duplicado): {skipped} | "
            f"Sin precio (descartadas): {no_price}"
        )
        for row in to_create[:10]:
            print(
                f"  [{row['sku']}] {row['title']!r} — base_price={row['base_price']} "
                f"(iva {iva}%) cat={row['category_name']!r} src={row['_source_url']}"
            )
        if len(to_create) > 10:
            print(f"  ... y {len(to_create) - 10} más")

        if not commit:
            print("\nDry-run: no se escribió nada. Repite con --commit para insertar.")
            return

        for row in to_create:
            category = _ensure_category(db, tenant_id, row.pop("category_name"), category_cache)
            row.pop("_source_url")
            db.add(
                Reference(
                    tenant_id=tenant_id,
                    provider_id=provider.id,
                    category_id=category.id if category else None,
                    **row,
                )
            )
        db.commit()
        print(f"Creadas {len(to_create)} Referencias bajo proveedor {PLACEHOLDER_PROVIDER_TITLE!r}.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="JSON de salida de `firecrawl crawl --json`")
    parser.add_argument("--commit", action="store_true", help="Inserta en la BBDD (por defecto: dry-run)")
    parser.add_argument(
        "--iva", type=Decimal, default=DEFAULT_IVA, help="IVA asumido en el precio scrapeado (default 19)"
    )
    args = parser.parse_args()
    if not args.input.exists():
        print(f"No existe el archivo: {args.input}", file=sys.stderr)
        sys.exit(1)
    main(args.input, args.commit, args.iva)
