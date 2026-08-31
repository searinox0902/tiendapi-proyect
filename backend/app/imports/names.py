"""Resolución de entidades por nombre — índice plegado, una consulta por corrida.

Reemplaza al `func.lower(Model.campo) == nombre.lower()` que usaban los tres
importadores. Ese criterio cubría `Honda`/`HONDA` pero **no** `Pírelli`/`Pirelli`
ni `"Pirelli "`/`"Pirelli"`, así que un archivo scrapeado sembraba proveedores y
categorías duplicados que después hay que unificar a mano. La regla de qué
cuenta como el mismo nombre vive en `app/core/text.py:fold` y es la misma para
todo el sistema.

**Por qué un índice en memoria y no un `WHERE` plegado:** plegar en SQL exige la
extensión `unaccent` de Postgres, que no está instalada y que ataría el criterio
al motor —la BBDD local es SQLite (D-01/D-02), donde no existe—. Cargar la tabla
entera es barato y además determinista: el Directorio real tiene entre 7 y 53
filas por entidad, así que **una** consulta por corrida reemplaza a una consulta
por nombre distinto del archivo. Con catálogos de cientos de miles de filas
habría que revisarlo; con estos tamaños, no.

**Colisiones entre lo que ya existe.** Si la base ya trae `Pirelli` y `Pírelli`
como dos registros —creados antes de que esta regla existiera— los dos pliegan
al mismo nombre. Gana el **más viejo** (orden por `created_at`, `id`), para que
dos corridas del mismo archivo elijan siempre igual. No se fusionan ni se
tocan: unificar registros existentes es una migración de datos con
consecuencias (FKs, historial), no un efecto secundario de importar un archivo.
"""
from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import fold
from app.models.brand import Brand
from app.models.reference import Reference


class NameIndex:
    """
    Índice `nombre plegado → registro` de una entidad, para un tenant.

    Se construye una vez al empezar la importación y se usa para las tres
    preguntas que los importadores hacen sobre un nombre: si ya existe
    (`find`), cuáles del archivo son nuevos (`missing`) y dámelo o creálo
    (`resolve`).

    Lo que se crea queda en el índice, así que dos filas del mismo archivo que
    escriben `Honda` y `HONDA` caen en **un** registro — la deduplicación
    dentro del propio archivo sale gratis del mismo mecanismo.
    """

    def __init__(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        model: type,
        column,
        batch_id: Optional[uuid.UUID] = None,
        defaults: Optional[dict] = None,
    ):
        self._db = db
        self._tenant_id = tenant_id
        self._model = model
        self._column = column
        self._field = column.key
        #  Se estampa en lo autocreado para que deshacer el lote se lleve
        #  también el Directorio que el archivo inventó (D-92).
        self._batch_id = batch_id
        #  Columnas obligatorias que el nombre no alcanza a determinar — hoy
        #  solo `Location.type`, que es NOT NULL con CHECK (D-25).
        self._defaults = defaults or {}

        self._by_folded: dict[str, object] = {}
        rows = db.execute(
            select(model)
            .where(model.tenant_id == tenant_id)
            .order_by(model.created_at, model.id)
        ).scalars()
        for row in rows:
            #  `setdefault`: ante dos registros que pliegan igual gana el más
            #  viejo, que es el primero de este orden. Determinista entre
            #  corridas, a diferencia de "el último que responda la consulta".
            self._by_folded.setdefault(fold(getattr(row, self._field)), row)

    def find(self, name: Optional[str]):
        """Registro cuyo nombre pliega igual, o `None`. No crea nada."""
        if not name:
            return None
        return self._by_folded.get(fold(name))

    def missing(self, names: Iterable[str]) -> set[str]:
        """
        Cuáles de esos nombres **no** existen todavía — para la previsualización.

        Devuelve los nombres **tal como vienen en el archivo**, que es lo que el
        usuario tiene que leer, no su forma plegada.

        **Uno por nombre plegado, no uno por grafía.** Si el archivo trae
        `Honda` y `HONDA` y ninguno existe, se va a crear **un** proveedor: la
        previsualización tiene que anunciar uno, o promete más registros de los
        que el commit hace.

        **Gana la primera aparición**, por eso `names` se recibe como iterable
        ordenado y no como `set`: `resolve()` guarda la grafía de la primera
        fila que nombra a ese proveedor, así que anunciar otra —la primera
        alfabética, por ejemplo— mostraría `PIRELLI` cuando en el catálogo va a
        quedar `Pirelli`. El orden del archivo es el que hace coincidir lo que
        se promete con lo que se guarda.
        """
        representantes: dict[str, str] = {}
        for name in names:
            if not name:
                continue
            key = fold(name)
            if key not in self._by_folded:
                representantes.setdefault(key, name)
        return set(representantes.values())

    def resolve(self, name: Optional[str]):
        """
        Devuelve el registro con ese nombre, creándolo si no existe (criterio D-42).

        **Al crear se guarda el nombre tal cual lo trae el archivo**, sin
        plegar: `fold()` es para comparar, nunca para almacenar. El primero que
        aparece fija la grafía, y los que vengan después con otras mayúsculas o
        tildes se enganchan a ése en vez de crear otro.
        """
        if not name:
            return None
        key = fold(name)
        existing = self._by_folded.get(key)
        if existing is not None:
            return existing
        created = self._model(
            tenant_id=self._tenant_id,
            import_batch_id=self._batch_id,
            **{self._field: name},
            **self._defaults,
        )
        self._db.add(created)
        #  `flush` y no `commit`: el llamador necesita el `id` para las FKs de
        #  la misma transacción, pero el lote se confirma o se descarta entero.
        self._db.flush()
        self._by_folded[key] = created
        return created


class NameCanonicalizer:
    """
    Grafía canónica de un nombre de **texto libre**, para lo que no es una FK.

    Existe por `Reference.brand`, que D-57/D-71 mantienen deliberadamente como
    string suelto y **no** como FK a `Brand`: no hay registro que resolver, así
    que el valor del archivo se guardaba tal cual y `Honda`, `HONDA`, `hónda` y
    `Hónda` quedaban como cuatro marcas en el catálogo. Verificado importando
    esas cuatro grafías: cuatro filas distintas en `SELECT DISTINCT brand`.

    No normaliza el valor guardado —guardar `honda` en minúscula sería destruir
    la grafía que el usuario eligió—: **reusa la grafía que ya existe**. La
    primera aparición fija la forma y las siguientes convergen ahí.

    Las fuentes se pasan en orden de autoridad: primero la curada (la tabla
    `Brand` del Directorio), después lo que ya hay en el catálogo. Así una
    marca registrada a mano impone su forma sobre la que trajo un scraper.
    """

    def __init__(self, *sources: Iterable[Optional[str]]):
        self._canonical: dict[str, str] = {}
        for source in sources:
            for value in source:
                if value and value.strip():
                    self._canonical.setdefault(fold(value), value.strip())

    def canonical(self, name: Optional[str]) -> Optional[str]:
        """
        Grafía a guardar: la ya conocida si alguna pliega igual, o `name` tal cual.

        Lo no conocido se registra, así que dos filas del mismo archivo con
        `Honda` y `HONDA` terminan las dos en `Honda` aunque el catálogo
        estuviera vacío.
        """
        if not name or not name.strip():
            return None
        limpio = name.strip()
        return self._canonical.setdefault(fold(limpio), limpio)


def build_brand_canonicalizer(db: Session, tenant_id: uuid.UUID) -> NameCanonicalizer:
    """
    Grafías de marca ya conocidas, para que un archivo no siembre una quinta.

    Vive acá y no en uno de los dos importadores porque **los dos** escriben
    `Reference.brand` —el de Referencias al crear la ficha, el de Productos al
    crear una Referencia o una variante— y una segunda implementación de la
    regla es el bug del día que cambie.

    Mira las dos fuentes, en orden de autoridad: primero la tabla `Brand` del
    Directorio, que es la forma curada a mano, y después las marcas ya escritas
    en el catálogo. `Reference.brand` es texto libre (D-57) y `Brand` está
    desacoplada a propósito (D-71), así que ninguna de las dos sola alcanza.
    """
    del_directorio = db.execute(
        select(Brand.name).where(Brand.tenant_id == tenant_id).order_by(Brand.created_at, Brand.id)
    ).scalars()
    del_catalogo = db.execute(
        select(Reference.brand)
        .where(Reference.tenant_id == tenant_id, Reference.brand.is_not(None))
        .distinct()
        .order_by(Reference.brand)
    ).scalars()
    return NameCanonicalizer(del_directorio, del_catalogo)
