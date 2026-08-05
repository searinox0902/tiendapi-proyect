import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { d, lineSubtotal, ivaOf } from "./money";

const STORAGE_KEY = "tiendapi.caja.v1";

// Catálogo semilla (referencias con stock de unidades serializadas — D-41).
// Tema: repuestos de moto, coherente con los ejemplos de la doc.
const SEED_CATALOG = [
  // Lubricantes
  { sku: "ACE-001", name: "Aceite Motul 5100 10W40", basePrice: 45000, ivaPct: 19, stock: 24 },
  { sku: "ACE-002", name: "Aceite Motul 3000 20W50", basePrice: 32000, ivaPct: 19, stock: 30 },
  { sku: "ACE-003", name: "Aceite Yamalube 4T 20W40", basePrice: 38000, ivaPct: 19, stock: 18 },
  { sku: "ACE-004", name: "Aceite Castrol Power1 10W40", basePrice: 41000, ivaPct: 19, stock: 15 },
  { sku: "ACE-005", name: "Aceite de horquilla Motul 10W", basePrice: 28000, ivaPct: 19, stock: 12 },
  { sku: "GRA-001", name: "Grasa para cadena Motul", basePrice: 22000, ivaPct: 19, stock: 20 },
  // Filtros
  { sku: "FIL-002", name: "Filtro de aceite Hiflo", basePrice: 18000, ivaPct: 19, stock: 40 },
  { sku: "FIL-003", name: "Filtro de aire K&N", basePrice: 65000, ivaPct: 19, stock: 10 },
  { sku: "FIL-004", name: "Filtro de aire genérico", basePrice: 15000, ivaPct: 19, stock: 25 },
  { sku: "FIL-005", name: "Filtro de gasolina universal", basePrice: 9000, ivaPct: 19, stock: 30 },
  // Encendido / eléctrico
  { sku: "BUJ-003", name: "Bujía NGK Iridium", basePrice: 12500, ivaPct: 19, stock: 60 },
  { sku: "BUJ-004", name: "Bujía NGK estándar", basePrice: 6500, ivaPct: 19, stock: 80 },
  { sku: "BAT-001", name: "Batería Yuasa YTX7A", basePrice: 185000, ivaPct: 19, stock: 8 },
  { sku: "BAT-002", name: "Batería Motobatt 12Ah", basePrice: 210000, ivaPct: 19, stock: 5 },
  { sku: "CAB-001", name: "Cable de acelerador universal", basePrice: 14000, ivaPct: 19, stock: 22 },
  { sku: "CAB-002", name: "Cable de embrague", basePrice: 16000, ivaPct: 19, stock: 18 },
  { sku: "FOC-001", name: "Foco H4 halógeno", basePrice: 12000, ivaPct: 19, stock: 35 },
  { sku: "FOC-002", name: "Foco LED direccional", basePrice: 8500, ivaPct: 19, stock: 40 },
  { sku: "REL-001", name: "Relay de arranque", basePrice: 25000, ivaPct: 19, stock: 10 },
  // Frenos
  { sku: "PAS-001", name: "Pastillas de freno delanteras", basePrice: 32000, ivaPct: 19, stock: 20 },
  { sku: "PAS-002", name: "Pastillas de freno traseras", basePrice: 28000, ivaPct: 19, stock: 20 },
  { sku: "DIS-001", name: "Disco de freno delantero", basePrice: 95000, ivaPct: 19, stock: 6 },
  { sku: "LIQ-001", name: "Líquido de frenos DOT4", basePrice: 14000, ivaPct: 19, stock: 25 },
  { sku: "MAN-001", name: "Manguera de freno reforzada", basePrice: 45000, ivaPct: 19, stock: 8 },
  // Transmisión
  { sku: "CAD-005", name: "Kit de arrastre DID 428", basePrice: 210000, ivaPct: 19, stock: 8 },
  { sku: "CAD-006", name: "Cadena reforzada 520", basePrice: 98000, ivaPct: 19, stock: 10 },
  { sku: "PIN-001", name: "Piñón delantero 15 dientes", basePrice: 22000, ivaPct: 19, stock: 12 },
  { sku: "COR-001", name: "Corona trasera 45 dientes", basePrice: 65000, ivaPct: 19, stock: 9 },
  { sku: "EMB-001", name: "Kit de embrague completo", basePrice: 145000, ivaPct: 19, stock: 4 },
  // Carrocería y accesorios
  { sku: "CAR-004", name: "Carenaje XTZ 250", basePrice: 350000, ivaPct: 19, stock: 3 },
  { sku: "CAR-005", name: "Guardabarros delantero", basePrice: 85000, ivaPct: 19, stock: 5 },
  { sku: "ESP-001", name: "Espejo retrovisor izquierdo", basePrice: 22000, ivaPct: 19, stock: 15 },
  { sku: "ESP-002", name: "Espejo retrovisor derecho", basePrice: 22000, ivaPct: 19, stock: 15 },
  { sku: "MAN-002", name: "Manubrio de aluminio", basePrice: 78000, ivaPct: 19, stock: 6 },
  { sku: "PUN-001", name: "Puños de goma antideslizantes", basePrice: 18000, ivaPct: 19, stock: 20 },
  { sku: "ASI-001", name: "Funda de asiento universal", basePrice: 35000, ivaPct: 19, stock: 10 },
  { sku: "PAR-001", name: "Parrilla trasera", basePrice: 42000, ivaPct: 19, stock: 7 },
  // Llantas y rines
  { sku: "LLA-001", name: "Llanta trasera 110/90-17", basePrice: 195000, ivaPct: 19, stock: 8 },
  { sku: "LLA-002", name: "Llanta delantera 90/90-19", basePrice: 175000, ivaPct: 19, stock: 8 },
  { sku: "RIN-001", name: "Rin trasero de aluminio", basePrice: 320000, ivaPct: 19, stock: 3 },
  { sku: "CAM-001", name: "Cámara de aire 130/70-17", basePrice: 18000, ivaPct: 19, stock: 25 },
  // Protección y casco
  { sku: "CAS-001", name: "Casco integral talla M", basePrice: 220000, ivaPct: 0, stock: 6 },
  { sku: "CAS-002", name: "Casco abierto talla L", basePrice: 165000, ivaPct: 0, stock: 8 },
  { sku: "GUA-006", name: "Guantes de moto talla M", basePrice: 68000, ivaPct: 0, stock: 15 },
  { sku: "GUA-007", name: "Guantes de moto talla L", basePrice: 68000, ivaPct: 0, stock: 12 },
  { sku: "CHA-001", name: "Chaqueta de protección básica", basePrice: 195000, ivaPct: 19, stock: 4 },
  { sku: "ROD-001", name: "Rodilleras de protección", basePrice: 55000, ivaPct: 19, stock: 10 },
  // Herramientas y varios
  { sku: "HER-001", name: "Kit de herramientas básico", basePrice: 48000, ivaPct: 19, stock: 12 },
  { sku: "CAND-001", name: "Candado de disco antirrobo", basePrice: 35000, ivaPct: 19, stock: 15 },
  { sku: "IMP-001", name: "Impermeable para moto", basePrice: 42000, ivaPct: 19, stock: 20 },
];

const CUSTOMERS = ["Consumidor final", "Taller El Piñón", "Motos del Sur", "Juan Carlos R."];

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {
    /* estado corrupto → arranca limpio */
  }
  return null;
}

export const useCajaStore = defineStore("caja", () => {
  const saved = loadState();

  const catalog = ref(saved?.catalog ?? structuredClone(SEED_CATALOG));
  const cart = ref(saved?.cart ?? []);
  const customer = ref(saved?.customer ?? CUSTOMERS[0]);
  const facturaSeq = ref(saved?.facturaSeq ?? 1);
  const facturas = ref(saved?.facturas ?? []);
  let lineId = saved?.lineId ?? 1;

  // ----- Stock disponible en tiempo real (stock catálogo − lo que ya está en el carrito) -----
  function stockOf(sku) {
    const ref_ = catalog.value.find((c) => c.sku === sku);
    return ref_ ? ref_.stock : 0;
  }
  function inCart(sku) {
    return cart.value
      .filter((l) => l.sku === sku)
      .reduce((sum, l) => sum + l.qty, 0);
  }
  function availableOf(sku) {
    return stockOf(sku) - inCart(sku);
  }

  // ----- Totales (Decimal exacto) -----
  const subtotal = computed(() =>
    cart.value.reduce((acc, l) => acc.plus(lineSubtotal(l.unitPrice, l.qty)), d(0))
  );
  const ivaTotal = computed(() =>
    cart.value
      .reduce((acc, l) => acc.plus(ivaOf(lineSubtotal(l.unitPrice, l.qty), l.ivaPct)), d(0))
  );
  const total = computed(() => subtotal.value.plus(ivaTotal.value));
  const itemCount = computed(() => cart.value.reduce((n, l) => n + l.qty, 0));

  // ----- Acciones -----
  // Devuelve { ok, reason } para que la UI dé feedback.
  function addBySku(rawCode) {
    const code = (rawCode || "").trim();
    if (!code) return { ok: false, reason: "empty" };
    const found = catalog.value.find(
      (c) => c.sku.toLowerCase() === code.toLowerCase()
    );
    if (!found) return { ok: false, reason: "not_found", code };
    if (availableOf(found.sku) <= 0) return { ok: false, reason: "no_stock", name: found.name };

    const existing = cart.value.find((l) => l.sku === found.sku && !l.discounted);
    if (existing) {
      existing.qty += 1;
    } else {
      cart.value.push({
        id: lineId++,
        sku: found.sku,
        name: found.name,
        basePrice: found.basePrice,
        unitPrice: found.basePrice,
        ivaPct: found.ivaPct,
        qty: 1,
        freeform: false,
        discounted: false,
      });
    }
    return { ok: true };
  }

  // Venta libre — sin Referencia/Item previo (D-42).
  function addFreeform({ name, price, ivaPct }) {
    cart.value.push({
      id: lineId++,
      sku: null,
      name: name.trim(),
      basePrice: Number(price),
      unitPrice: Number(price),
      ivaPct: Number(ivaPct) || 0,
      qty: 1,
      freeform: true,
      discounted: false,
    });
    return { ok: true };
  }

  function inc(id) {
    const l = cart.value.find((x) => x.id === id);
    if (!l) return { ok: false };
    if (l.sku && availableOf(l.sku) <= 0) return { ok: false, reason: "no_stock", name: l.name };
    l.qty += 1;
    return { ok: true };
  }
  function dec(id) {
    const l = cart.value.find((x) => x.id === id);
    if (!l) return;
    l.qty -= 1;
    if (l.qty <= 0) remove(id);
  }
  function remove(id) {
    cart.value = cart.value.filter((x) => x.id !== id);
  }

  // Descuento a esta línea puntual — refleja el precio por unidad del Item (D-41).
  function setUnitPrice(id, newPrice) {
    const l = cart.value.find((x) => x.id === id);
    if (!l) return;
    const p = Math.max(0, Number(newPrice) || 0);
    l.unitPrice = p;
    l.discounted = !l.freeform && p < l.basePrice;
  }

  function setCustomer(name) {
    customer.value = name;
  }
  function clearCart() {
    cart.value = [];
  }

  // Emite la factura: descuenta stock de las líneas con Item real y la archiva.
  function cobrar({ method, received }) {
    if (cart.value.length === 0) return { ok: false, reason: "empty" };
    const snapshot = {
      number: String(facturaSeq.value).padStart(4, "0"),
      createdAt: new Date().toISOString(),
      customer: customer.value,
      method,
      received: method === "efectivo" ? Number(received) : null,
      subtotal: subtotal.value.toNumber(),
      iva: ivaTotal.value.toNumber(),
      total: total.value.toNumber(),
      lines: cart.value.map((l) => ({
        name: l.name,
        sku: l.sku,
        qty: l.qty,
        unitPrice: l.unitPrice,
        freeform: l.freeform,
      })),
    };
    // Descuenta stock (solo Items reales, la venta libre no toca inventario).
    for (const l of cart.value) {
      if (l.sku) {
        const ref_ = catalog.value.find((c) => c.sku === l.sku);
        if (ref_) ref_.stock = Math.max(0, ref_.stock - l.qty);
      }
    }
    facturas.value.unshift(snapshot);
    if (facturas.value.length > 20) facturas.value.pop();
    facturaSeq.value += 1;
    clearCart();
    return { ok: true, factura: snapshot };
  }

  function resetDemo() {
    catalog.value = structuredClone(SEED_CATALOG);
    cart.value = [];
    customer.value = CUSTOMERS[0];
    facturaSeq.value = 1;
    facturas.value = [];
    lineId = 1;
  }

  // ----- Persistencia manual a localStorage -----
  watch(
    [catalog, cart, customer, facturaSeq, facturas],
    () => {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          catalog: catalog.value,
          cart: cart.value,
          customer: customer.value,
          facturaSeq: facturaSeq.value,
          facturas: facturas.value,
          lineId,
        })
      );
    },
    { deep: true }
  );

  return {
    catalog, cart, customer, facturaSeq, facturas, customers: CUSTOMERS,
    availableOf, subtotal, ivaTotal, total, itemCount,
    addBySku, addFreeform, inc, dec, remove, setUnitPrice, setCustomer,
    clearCart, cobrar, resetDemo,
  };
});
