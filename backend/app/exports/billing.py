"""
Paquete de exportación de Facturación (D-78) — zip = Excel índice + un PDF por
factura.

**No contradice D-61.** Lo que D-61 prohíbe es que *el sistema* persista un PDF
espejo junto al registro, que quedaría mintiendo al corregirse un dato. Acá el
archivo lo pide *el usuario*, acotado por los filtros que él mismo tiene
puestos en pantalla, con la fecha del corte impresa: sale del sistema y el
sistema no lo vuelve a leer nunca. Sigue rigiendo la asimetría de D-73 — **las
facturas salen, jamás entran**: no hay ni habrá contraparte de importación,
porque re-firmar `hmac`/`prev_hash` con la clave del destino es exactamente el
ataque que D-07 existe para detectar.

Las tres condiciones del contador (D-78) están implementadas acá y no son
cosméticas: anuladas marcadas **en el nombre del archivo y dentro del PDF**,
filtro del corte impreso en la hoja "Alcance" del Excel, y el sello de "no
válido ante la DIAN" en cada documento.
"""
from __future__ import annotations

import re
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO

from fpdf import FPDF
from fpdf.enums import Align, XPos, YPos
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.exports.generic import Column, build_payload, render_xlsx
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.customer import Customer
from app.models.item import Item
from app.models.reference import Reference
from app.models.tenant import Tenant

FORMAT_VERSION = 1
KIND = "billing.package"

#  Carpeta interna del zip. Los PDFs no van en la raíz para que el Excel índice
#  se vea de una al abrir el archivo, sin scrollear entre cientos de facturas.
PDF_DIR = "facturas"
INDEX_NAME = "indice-facturas.xlsx"

#  Colombia es UTC-5 fijo y sin horario de verano desde 1993, así que un offset
#  constante es exacto y no puede fallar. Se prefiere a `zoneinfo`, que en
#  Windows exige el paquete `tzdata` y ahí sí fallaría en tiempo de ejecución.
#
#  **Esto no es un detalle de formato.** `created_at` se guarda en UTC y la
#  pantalla lo pinta con `Intl.DateTimeFormat("es-CO", …)`, o sea en hora local
#  del equipo. Estampar UTC en el PDF haría que una venta de las 8 p.m. saliera
#  fechada al día siguiente y que el papel contradijera la pantalla — que es
#  justo lo que un contador detecta al cuadrar un mes.
BOGOTA = timezone(timedelta(hours=-5))

#  Mismo texto que la hoja en pantalla (`InvoiceDocument.vue`). Va en cada PDF
#  porque un paquete de facturas "autorizadas" cuyos documentos son nuestra
#  reconstrucción —y no la copia firmada del proveedor— es exactamente donde
#  alguien se confunde y lo toma por soporte fiscal.
DISCLAIMER = (
    "Documento reconstruido desde los registros del sistema. "
    "NO CONSTITUYE FACTURA ELECTRONICA VALIDA ANTE LA DIAN."
)

INDEX_COLUMNS: tuple[Column, ...] = (
    Column("file", "Archivo", width=26),
    Column("path", "Ruta dentro del zip", width=32),
    Column("bill_number", "Codigo", width=14),
    Column("issued_at", "Fecha de emision", width=20),
    Column("customer", "Cliente", width=32),
    Column("nit", "NIT / Cedula", width=18),
    Column("subtotal", "Base gravable", numeric=True, width=16),
    Column("total_iva", "IVA", numeric=True, width=14),
    Column("total", "Total", numeric=True, width=16),
    Column("fiscal_status", "Estado DIAN", width=18),
    Column("voided", "Anulada", width=10),
    Column("void_reason", "Motivo de anulacion", width=40),
)

FISCAL_LABELS = {
    "contingencia": "Contingencia",
    "pendiente": "Pendiente",
    "autorizada": "Autorizada",
    "rechazada": "Rechazada",
}


def _group_integer(digitos: str) -> str:
    """
    Convención colombiana completa: punto de miles y **apóstrofo en el
    millón** — `2'500.000`, `1.234'567.890`.

    Espejo exacto de `groupInteger` en `frontend/src/lib/money.ts`. Si cambias
    uno, cambia el otro: el papel y la pantalla mostrando la misma plata
    distinto es la divergencia que D-78 se compromete a evitar.
    """
    grupos = [digitos[max(0, fin - 3):fin] for fin in range(len(digitos), 0, -3)][::-1]
    salida = grupos[0]
    for indice in range(1, len(grupos)):
        #  Posición del grupo contando desde la derecha: 0 = unidades,
        #  1 = miles, 2 = millones. El separador que queda justo antes del
        #  grupo de los miles es el del millón, y ese lleva apóstrofo.
        desde_derecha = len(grupos) - 1 - indice
        salida += ("'" if desde_derecha == 1 else ".") + grupos[indice]
    return salida


def _money(value: Decimal | None) -> str:
    """
    `Decimal` → `"$ 182.000,00"` / `"$ 2'500.000,00"`, misma convención que
    `formatCurrency` del frontend.

    Se formatea a mano y no con `locale` porque `locale` depende de qué idiomas
    tenga instalado el contenedor: un servidor sin `es_CO` devolvería otro
    formato sin avisar.
    """
    if value is None:
        return "-"
    entero, decimales = f"{value.quantize(Decimal('0.01')):.2f}".split(".")
    negativo = entero.startswith("-")
    return f"$ {'-' if negativo else ''}{_group_integer(entero.lstrip('-'))},{decimales}"


def _quantity(value: Decimal | None) -> str:
    """
    Cantidad legible: `1`, `2,5` — **nunca `1.000`**.

    `BillItem.quantity` es `Numeric(12,3)`, así que una unidad llega como
    `Decimal("1.000")`. Imprimir eso tal cual es un error de lectura grave en
    Colombia, donde el punto **es** el separador de miles: "1.000" en la columna
    Cant. de una factura se lee *mil unidades*. La pantalla ya lo resuelve
    (`toDecimalPlaces(2).toString()` → `"1"`); esto es su equivalente.

    La parte decimal sale con **coma** y no con punto —única diferencia de
    formato con la pantalla, deliberada— para no mezclar dos convenciones en la
    misma tabla, donde la columna de al lado dice `$ 255.850,00`.
    """
    if value is None:
        return ""
    if value == value.to_integral_value():
        return str(int(value))
    return str(value.normalize()).replace(".", ",")


def _decimal_str(value: Decimal | None) -> str | None:
    """Plata como string con dos decimales (D-05) — nunca float en el archivo."""
    return None if value is None else str(value.quantize(Decimal("0.01")))


def _local(moment: datetime) -> datetime:
    """UTC almacenado → hora de Colombia. Ver `BOGOTA` para por qué importa."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(BOGOTA)


def _issued_at(moment: datetime) -> str:
    """
    Fecha del índice en ISO (`2026-08-17 20:14`) y no en formato largo: el
    contador ordena y filtra la columna en Excel, y una cadena ISO ordena
    correctamente incluso tratada como texto. En el PDF sí va el formato largo,
    que es donde lo lee un humano.
    """
    return _local(moment).strftime("%Y-%m-%d %H:%M")


def _latin1(text: str) -> str:
    """
    Deja el texto imprimible con las fuentes core de fpdf2, que son latin-1.

    Los acentos y la ñ del español entran en latin-1 sin problema; lo que no
    entra es el carácter suelto que llegue pegado en un nombre de cliente (una
    comilla tipográfica, un emoji, un guion largo). Sin este filtro, **una sola
    factura con un carácter raro tumba la exportación completa** con
    `FPDFUnicodeEncodingException`. Se prefiere degradar ese carácter a
    incrustar una TTF Unicode en el repo solo para esto.
    """
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _slug_filename(value: str) -> str:
    """
    El nombre del archivo lo elige el usuario indirectamente (el consecutivo
    puede venir importado o migrado, D-73), así que se sanitiza: un `/` o un
    `:` en un nombre de entrada de zip es una ruta inválida en Windows.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned or "factura"


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower() or "negocio"


def invoice_filename(bill_number: str, *, voided: bool) -> str:
    """
    `FV-0012.pdf`, o `FV-0012-ANULADA.pdf` si lo está (D-60).

    La marca va en el **nombre** y no solo dentro del documento por pedido
    expreso del contador: si el paquete se le entrega a un tercero, una anulada
    que se ve igual que una vigente es dinero que parece haber entrado.
    """
    suffix = "-ANULADA" if voided else ""
    return f"{_slug_filename(bill_number)}{suffix}.pdf"


def package_filename(business_name: str | None) -> str:
    stamp = datetime.now(BOGOTA).strftime("%Y%m%d")
    return f"tiendapi-facturas-{_slugify(business_name or 'negocio')}-{stamp}.zip"


def fetch_bills(db: Session, tenant_id: uuid.UUID, conditions: list) -> list[dict]:
    """
    Trae las facturas del corte con su cliente y sus líneas ya agrupadas.

    **Dos consultas, no una por factura.** La agrupación por Referencia es la
    misma de `GET /{bill_id}/detail` (una fila por unidad física en la base, un
    renglón por Referencia en el documento), pero resuelta para **todo el
    conjunto filtrado en una pasada**: con un paquete de mil facturas, llamar
    al detalle en un bucle serían mil viajes a la base.

    Las líneas se filtran con las **mismas `conditions`** que las cabeceras y
    no por un `IN (...)` de los ids ya traídos: además de ahorrar una lista de
    mil UUIDs en el SQL, garantiza que ninguna línea se cuele o se pierda por
    filtrar distinto en las dos consultas.
    """
    cabeceras = db.execute(
        select(Bill, Customer.fullname, Customer.nit)
        .join(Customer, Customer.id == Bill.customer_id)
        .where(*conditions)
        .order_by(Bill.created_at.desc(), Bill.id.desc())
    ).all()

    lineas = db.execute(
        select(
            Bill.id,
            Reference.sku,
            Reference.title,
            BillItem.unit_price,
            BillItem.iva_percentage,
            func.sum(BillItem.quantity),
            func.sum(BillItem.iva_amount),
            func.sum(BillItem.total),
        )
        .select_from(BillItem)
        .join(Bill, Bill.id == BillItem.bill_id)
        .join(Customer, Customer.id == Bill.customer_id)
        .join(Item, Item.id == BillItem.item_id)
        .join(Reference, Reference.id == Item.reference_id)
        .where(*conditions)
        .group_by(
            Bill.id,
            Reference.sku,
            Reference.title,
            BillItem.unit_price,
            BillItem.iva_percentage,
        )
        #  Orden estable: sin esto el mismo documento puede salir con los
        #  renglones en otro orden en cada exportación.
        .order_by(Bill.id, Reference.sku, BillItem.unit_price)
    ).all()

    por_factura: dict[uuid.UUID, list[dict]] = {}
    for bill_id, sku, title, unit_price, iva_pct, cantidad, iva, total in lineas:
        por_factura.setdefault(bill_id, []).append(
            {
                "sku": sku,
                "title": title,
                "quantity": cantidad,
                "unit_price": unit_price,
                "iva_percentage": iva_pct,
                "iva_amount": iva,
                "total": total,
            }
        )

    facturas = []
    for bill, fullname, nit in cabeceras:
        facturas.append(
            {
                "id": bill.id,
                "bill_number": bill.bill_number,
                "customer": fullname,
                "nit": nit,
                "subtotal": bill.subtotal,
                "total_iva": bill.total_iva,
                "total": bill.total,
                "fiscal_status": bill.fiscal_status,
                "voided_at": bill.voided_at,
                "void_reason": bill.void_reason,
                "created_at": bill.created_at,
                "lines": por_factura.get(bill.id, []),
            }
        )
    return facturas


def render_invoice_pdf(factura: dict, business_name: str) -> bytes:
    """
    Un PDF por factura, tamaño carta.

    ⚠️ **Riesgo asumido y declarado en D-78:** este layout es una *segunda*
    implementación del documento y **va a divergir** de `InvoiceDocument.vue`
    con el tiempo. La mitigación es que los **datos** no pueden divergir —
    ambos leen la misma agrupación por Referencia calculada en el servidor— y
    que este layout se mantiene deliberadamente mínimo para que haya poco que
    divergir. Si vas a "mejorarlo", vale más portar el cambio a los dos lados
    que dejar que se separen.
    """
    pdf = FPDF(format="letter", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    ancho = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("helvetica", "B", 15)
    pdf.cell(0, 8, _latin1(business_name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("helvetica", "B", 11)
    pdf.cell(
        0, 7, _latin1(f"Factura de venta {factura['bill_number']}"),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )

    pdf.set_font("helvetica", "", 9)
    emitida = _local(factura["created_at"]).strftime("%d/%m/%Y %H:%M")
    estado = FISCAL_LABELS.get(factura["fiscal_status"] or "", "Sin declarar ante la DIAN")
    pdf.cell(0, 5, _latin1(f"Emitida: {emitida}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, _latin1(f"Estado DIAN: {estado}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0, 5, _latin1(f"Cliente: {factura['customer']}"),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    if factura["nit"]:
        pdf.cell(
            0, 5, _latin1(f"NIT / Cedula: {factura['nit']}"),
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

    #  Banda de anulada arriba y no al pie: quien recibe el papel tiene que
    #  verlo antes de leer los montos, no después (mismo criterio que la
    #  advertencia de cifrado de D-77).
    if factura["voided_at"] is not None:
        pdf.ln(3)
        pdf.set_font("helvetica", "B", 11)
        pdf.set_fill_color(120, 20, 20)
        pdf.set_text_color(255, 255, 255)
        anulada = _local(factura["voided_at"]).strftime("%d/%m/%Y")
        pdf.cell(
            ancho, 8, _latin1(f"ANULADA el {anulada}"),
            align=Align.C, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        pdf.set_text_color(0, 0, 0)
        if factura["void_reason"]:
            pdf.set_font("helvetica", "", 9)
            pdf.multi_cell(ancho, 5, _latin1(f"Motivo: {factura['void_reason']}"))

    pdf.ln(4)

    #  Anchos derivados del ancho útil y no absolutos, para que la tabla no se
    #  salga del margen si algún día cambia el tamaño de página.
    cols = [
        ("SKU", 0.14, Align.L),
        ("Descripcion", 0.38, Align.L),
        ("Cant.", 0.08, Align.R),
        ("Precio unit.", 0.14, Align.R),
        ("IVA", 0.12, Align.R),
        ("Total", 0.14, Align.R),
    ]

    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(238, 238, 238)
    for etiqueta, fraccion, alineacion in cols:
        pdf.cell(ancho * fraccion, 7, etiqueta, border=1, align=alineacion, fill=True)
    pdf.ln()

    pdf.set_font("helvetica", "", 8)
    for linea in factura["lines"]:
        #  El nombre se recorta y no se envuelve: una fila de altura variable
        #  descuadraría la grilla, y el nombre completo ya está en el sistema.
        titulo = linea["title"] or ""
        if len(titulo) > 46:
            #  "..." en ASCII y no el carácter "…" (U+2026), que no existe en
            #  latin-1 y `_latin1` convertiría en un "?" desconcertante.
            titulo = titulo[:43] + "..."
        valores = [
            (linea["sku"] or "", Align.L),
            (titulo, Align.L),
            (_quantity(linea["quantity"]), Align.R),
            (_money(linea["unit_price"]), Align.R),
            (_money(linea["iva_amount"]), Align.R),
            (_money(linea["total"]), Align.R),
        ]
        for (texto, alineacion), (_etiqueta, fraccion, _al) in zip(valores, cols):
            pdf.cell(ancho * fraccion, 6, _latin1(str(texto)), border=1, align=alineacion)
        pdf.ln()

    if not factura["lines"]:
        pdf.cell(ancho, 6, "Sin lineas registradas", border=1, align=Align.C)
        pdf.ln()

    pdf.ln(3)
    pdf.set_font("helvetica", "", 9)
    etiqueta_ancho = ancho * 0.72
    for etiqueta, valor, negrita in (
        ("Base gravable", factura["subtotal"], False),
        ("IVA", factura["total_iva"], False),
        ("Total", factura["total"], True),
    ):
        pdf.set_font("helvetica", "B" if negrita else "", 10 if negrita else 9)
        pdf.cell(etiqueta_ancho, 6, etiqueta, align=Align.R)
        pdf.cell(ancho - etiqueta_ancho, 6, _money(valor), align=Align.R,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    pdf.set_font("helvetica", "B", 7)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(ancho, 4, _latin1(DISCLAIMER))

    return bytes(pdf.output())


def scope_rows(
    *,
    business_name: str | None,
    total_bills: int,
    voided_bills: int,
    filters: dict[str, object],
) -> list[tuple[str, str]]:
    """
    Hoja "Alcance" del Excel — **qué filtro produjo este paquete** (D-78).

    Sin esto, en tres meses una carpeta suelta no dice si contiene "las
    facturas de marzo" o "todas las autorizadas", que son paquetes distintos
    imposibles de distinguir mirando los archivos.
    """
    def _texto(valor: object) -> str:
        if valor is None or valor == "":
            return "(sin filtrar)"
        if isinstance(valor, date):
            return valor.isoformat()
        return str(getattr(valor, "value", valor))

    return [
        ("Negocio", business_name or "-"),
        ("Generado", datetime.now(BOGOTA).strftime("%Y-%m-%d %H:%M (UTC-5)")),
        ("Version de plataforma", settings.app_version),
        ("Facturas incluidas", str(total_bills)),
        ("De ellas, anuladas", str(voided_bills)),
        ("Filtro: desde", _texto(filters.get("date_from"))),
        ("Filtro: hasta", _texto(filters.get("date_to"))),
        ("Filtro: cliente", _texto(filters.get("customer"))),
        ("Filtro: codigo de factura", _texto(filters.get("bill_number"))),
        ("Filtro: estado DIAN", _texto(filters.get("fiscal_status"))),
        (
            "Advertencia",
            "Los PDF de este paquete son documentos reconstruidos. No constituyen "
            "factura electronica valida ante la DIAN.",
        ),
    ]


def build_package(
    db: Session,
    tenant_id: uuid.UUID,
    conditions: list,
    filters: dict[str, object],
) -> tuple[bytes, str, int]:
    """
    Arma el zip completo. Devuelve `(contenido, nombre_archivo, facturas)`.

    El índice se genera con el motor genérico ya existente (D-75) más las
    columnas `Archivo`/`Ruta`, que son lo propio de este paquete: son las que
    convierten una carpeta de PDFs en algo navegable desde la hoja.
    """
    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
    business_name = tenant.business_name if tenant else None

    facturas = fetch_bills(db, tenant_id, conditions)

    buffer = BytesIO()
    filas_indice = []
    #  ZIP_DEFLATED y no ZIP_STORED: son PDFs de texto, comprimen muy bien y un
    #  paquete de un mes puede ser la diferencia entre 4 MB y 40 MB en el
    #  correo del contador.
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archivo:
        usados: set[str] = set()
        for factura in facturas:
            anulada = factura["voided_at"] is not None
            nombre = invoice_filename(factura["bill_number"], voided=anulada)
            #  El consecutivo **no** tiene UNIQUE en base (D-73 lo dejó con
            #  unicidad blanda), así que dos facturas pueden compartir número y
            #  una entrada de zip pisaría a la otra en silencio: se desempata.
            if nombre in usados:
                raiz, _, extension = nombre.rpartition(".")
                nombre = f"{raiz}-{str(factura['id'])[:8]}.{extension}"
            usados.add(nombre)

            ruta = f"{PDF_DIR}/{nombre}"
            archivo.writestr(ruta, render_invoice_pdf(factura, business_name or "Negocio"))

            filas_indice.append(
                {
                    "file": nombre,
                    "path": ruta,
                    "bill_number": factura["bill_number"],
                    "issued_at": _issued_at(factura["created_at"]),
                    "customer": factura["customer"],
                    "nit": factura["nit"],
                    "subtotal": _decimal_str(factura["subtotal"]),
                    "total_iva": _decimal_str(factura["total_iva"]),
                    "total": _decimal_str(factura["total"]),
                    "fiscal_status": FISCAL_LABELS.get(
                        factura["fiscal_status"] or "", "Sin declarar"
                    ),
                    "voided": "Si" if anulada else "No",
                    "void_reason": factura["void_reason"],
                }
            )

        payload = build_payload(
            filas_indice, INDEX_COLUMNS, KIND, FORMAT_VERSION, settings.app_version
        )
        archivo.writestr(
            INDEX_NAME,
            render_xlsx(
                payload,
                INDEX_COLUMNS,
                sheet_title="Facturas",
                scope_rows=scope_rows(
                    business_name=business_name,
                    total_bills=len(facturas),
                    voided_bills=sum(1 for f in facturas if f["voided_at"] is not None),
                    filters=filters,
                ),
            ),
        )

    return buffer.getvalue(), package_filename(business_name), len(facturas)
