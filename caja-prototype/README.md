# Caja registradora — prototipo TiendAPI

Prototipo **solo frontend** de la pantalla de Caja, para explorar la experiencia de usuario. Vue 3 + Pinia, persistencia en `localStorage` (no requiere backend). Independiente de `frontend/` (la app real).

## Correr

```bash
cd caja-prototype
npm install
npm run dev
```

Abre **http://localhost:5180**.

## Qué prueba (todo lo decidido en la doc)

- **Escaneo / SKU manual:** escribe un SKU y presiona Enter. El lector de código de barras funciona igual (actúa como teclado). Prueba: `ACE-001`, `FIL-002`, `BUJ-003`, `CAR-004`, `CAD-005`, `GUA-006`.
- **Acceso rápido:** grid de productos del catálogo (con stock disponible en vivo) — clic para agregar.
- **Item serializado (D-41):** cada producto tiene stock de unidades; la caja no deja vender más de lo disponible. El precio se puede editar **por línea** (descuento a esa unidad) haciendo clic en el precio.
- **Venta libre (D-42):** si escribes un código que no existe, se abre el formulario de venta libre (descripción + precio) — para lo no catalogado (peso/volumen). No descuenta inventario, va marcado con badge.
- **Cobro:** modal de pago (efectivo con cálculo de cambio, o tarjeta). Al cobrar, emite la factura, descuenta stock y la archiva.
- **Facturas generadas:** la lista de "Últimas facturas" se llena con cada cobro; clic para ver el detalle.
- **Persistencia:** todo (carrito, stock, facturas) sobrevive a recargar la página. "Reiniciar demo" limpia el estado.

## Colores

Tokens HSL estilo shadcn/vue copiados de `frontend/src/style.css` (regla 90/7/3, púrpura provisional `#7C3AED`), para que se vea consistente con la app real.

## Notas

- Es un **prototipo desechable** de UX. Los patrones (store de Pinia, cálculo con Decimal.js, estructura de líneas) se trasladan directo a la app real en TypeScript.
- JavaScript en vez de TypeScript a propósito, para que arranque con `npm run dev` sin pasos de type-check.
