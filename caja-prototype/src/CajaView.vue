<script setup>
import { ref, computed, nextTick, onMounted } from "vue";
import { useCajaStore } from "./store";
import { formatCOP } from "./money";

const store = useCajaStore();
const cop = formatCOP;

const scan = ref("");
const scanInput = ref(null);
const scanFocused = ref(false);
const highlightIndex = ref(-1);
const flash = ref(null);
let flashTimer = null;

function notify(type, text) {
  flash.value = { type, text };
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => (flash.value = null), 2600);
}
function focusScan() {
  nextTick(() => scanInput.value && scanInput.value.focus());
}
onMounted(focusScan);

// ----- Normalización para búsqueda flexible (sin tildes, minúsculas) -----
// Rango Unicode de marcas diacríticas combinantes (U+0300–U+036F) — construido
// por código de punto para no depender de caracteres invisibles en el archivo.
const DIACRITICS_RE = new RegExp(
  "[" + String.fromCharCode(0x0300) + "-" + String.fromCharCode(0x036f) + "]",
  "g"
);
function normalize(str) {
  return (str || "")
    .toString()
    .normalize("NFD")
    .replace(DIACRITICS_RE, "")
    .toLowerCase()
    .trim();
}

// ----- Autocompletado reactivo por carácter -----
// SKU: prioriza exacto/empieza-por/contiene. Nombre: flexible — cada palabra
// escrita debe aparecer en algún lugar del nombre, sin importar el orden ni
// coincidencia exacta de mayúsculas/tildes (pedido explícito: "no carácter
// exacto sino más flexible").
const suggestions = computed(() => {
  const q = normalize(scan.value);
  if (!q) return [];
  const tokens = q.split(/\s+/).filter(Boolean);
  const scored = [];
  for (const p of store.catalog) {
    const skuN = normalize(p.sku);
    const nameN = normalize(p.name);
    const skuExact = skuN === q;
    const skuStarts = skuN.startsWith(q);
    const skuIncludes = skuN.includes(q);
    const nameStarts = nameN.startsWith(q);
    const nameAllTokens = tokens.every((t) => nameN.includes(t));
    if (!(skuIncludes || nameAllTokens)) continue;
    let score = 0;
    if (skuExact) score = 100;
    else if (skuStarts) score = 90;
    else if (nameStarts) score = 80;
    else if (skuIncludes) score = 70;
    else if (nameAllTokens) score = 50 + tokens.length;
    scored.push({ p, score });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, 8).map((s) => s.p);
});
const showDropdown = computed(() => scanFocused.value && scan.value.trim().length > 0);

function selectSuggestion(product) {
  quickAdd(product.sku);
  scan.value = "";
  highlightIndex.value = -1;
  focusScan();
}

// ----- Escaneo / SKU manual -----
function submitScan() {
  const res = store.addBySku(scan.value);
  if (res.ok) {
    scan.value = "";
  } else if (res.reason === "not_found") {
    openFreeform(res.code);
    scan.value = "";
  } else if (res.reason === "no_stock") {
    notify("error", `Sin stock disponible: ${res.name}`);
    scan.value = "";
  }
  focusScan();
}
function onScanKeydown(e) {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    if (suggestions.value.length) {
      highlightIndex.value = (highlightIndex.value + 1) % suggestions.value.length;
    }
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (suggestions.value.length) {
      highlightIndex.value =
        (highlightIndex.value - 1 + suggestions.value.length) % suggestions.value.length;
    }
  } else if (e.key === "Enter") {
    // Con resultados en pantalla, Enter siempre confirma el mejor/resaltado.
    // Solo cae al lookup exacto (o venta libre) cuando no hay ninguna sugerencia.
    if (suggestions.value.length > 0) {
      const idx = highlightIndex.value >= 0 ? highlightIndex.value : 0;
      selectSuggestion(suggestions.value[idx]);
    } else {
      submitScan();
    }
  } else if (e.key === "Escape") {
    scan.value = "";
    highlightIndex.value = -1;
  } else {
    highlightIndex.value = -1;
  }
}
function quickAdd(sku) {
  const res = store.addBySku(sku);
  if (!res.ok && res.reason === "no_stock") notify("error", `Sin stock: ${res.name}`);
  focusScan();
}
function onInc(id) {
  const res = store.inc(id);
  if (!res.ok && res.reason === "no_stock") notify("error", `Sin más stock: ${res.name}`);
}

// ----- Venta libre (D-42) -----
const freeform = ref({ open: false, name: "", price: "", ivaPct: 19 });
function openFreeform(prefill = "") {
  freeform.value = { open: true, name: prefill, price: "", ivaPct: 19 };
  nextTick(() => document.getElementById("ff-name")?.focus());
}
function confirmFreeform() {
  const f = freeform.value;
  if (!f.name.trim() || !(Number(f.price) > 0)) {
    notify("error", "Ingresa descripción y un precio válido");
    return;
  }
  store.addFreeform({ name: f.name, price: f.price, ivaPct: f.ivaPct });
  freeform.value.open = false;
  focusScan();
}

// ----- Descuento por línea -----
const editing = ref(null);
function startEdit(line) {
  editing.value = { id: line.id, value: String(line.unitPrice) };
  nextTick(() => document.getElementById("edit-price")?.focus());
}
function confirmEdit() {
  if (editing.value) {
    store.setUnitPrice(editing.value.id, editing.value.value);
    editing.value = null;
  }
}

// ----- Cobro -----
const pay = ref({ open: false, method: "efectivo", received: "" });
function openPay() {
  if (store.cart.length === 0) {
    notify("error", "La venta está vacía");
    return;
  }
  pay.value = { open: true, method: "efectivo", received: "" };
  nextTick(() => document.getElementById("pay-received")?.focus());
}
const change = computed(() => (Number(pay.value.received) || 0) - store.total.toNumber());
const canCharge = computed(() =>
  pay.value.method === "tarjeta" ? true : Number(pay.value.received) >= store.total.toNumber()
);
function confirmPay() {
  const res = store.cobrar({ method: pay.value.method, received: pay.value.received });
  if (res.ok) {
    pay.value.open = false;
    notify("ok", `Factura #${res.factura.number} cobrada · ${cop(res.factura.total)}`);
    focusScan();
  }
}
function setReceived(v) {
  pay.value.received = String(v);
}

// ----- Facturas (slide-over) -----
const facturasOpen = ref(false);
const viewing = ref(null);
const dayCount = computed(() => store.facturas.length);
const dayTotal = computed(() => store.facturas.reduce((s, f) => s + f.total, 0));

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
}
</script>

<template>
  <div class="pos">
    <!-- ================= HEADER ================= -->
    <header class="pos-header">
      <div class="brand">
        <span class="logo">T</span>
        <div>
          <div class="brand-name">TiendAPI</div>
          <div class="brand-sub muted">Caja registradora</div>
        </div>
      </div>

      <div class="header-right">
        <div class="day-stat">
          <span class="muted">Facturas de hoy</span>
          <strong>{{ dayCount }} · {{ cop(dayTotal) }}</strong>
        </div>
        <button class="btn btn-outline" @click="facturasOpen = true">Ver facturas</button>
        <button class="btn btn-ghost" @click="store.resetDemo()">Reiniciar demo</button>
      </div>
    </header>

    <!-- ================= BODY: dos paneles ================= -->
    <div class="pos-body">
      <!-- ---------- CATÁLOGO (izquierda, ancho) ---------- -->
      <section class="catalog">
        <div class="scanbar">
          <div class="scan-row">
            <span class="scan-icon">⌕</span>
            <input
              ref="scanInput"
              v-model="scan"
              class="scan-field"
              placeholder="Escanea un código de barras o escribe un SKU / nombre…"
              autocomplete="off"
              @keydown="onScanKeydown"
              @focus="scanFocused = true"
              @blur="scanFocused = false"
            />
            <button class="btn btn-outline" @click="openFreeform()">+ Venta libre</button>
          </div>

          <div v-if="showDropdown" class="suggestions">
            <template v-if="suggestions.length">
              <button
                v-for="(s, i) in suggestions"
                :key="s.sku"
                class="suggestion"
                :class="{ active: i === highlightIndex }"
                @mousedown.prevent="selectSuggestion(s)"
                @mouseenter="highlightIndex = i"
              >
                <span class="sg-sku">{{ s.sku }}</span>
                <span class="sg-name">{{ s.name }}</span>
                <span class="sg-meta">
                  <span
                    class="sg-stock"
                    :class="{ low: store.availableOf(s.sku) <= 3 && store.availableOf(s.sku) > 0, out: store.availableOf(s.sku) <= 0 }"
                  >
                    {{ store.availableOf(s.sku) }} disp.
                  </span>
                  <span class="sg-price">{{ cop(s.basePrice) }}</span>
                </span>
              </button>
            </template>
            <div v-else class="suggestion-empty">
              Sin resultados para "<strong>{{ scan }}</strong>" — presiona <kbd>Enter</kbd> para venta libre
            </div>
          </div>

          <transition name="fade">
            <div v-if="flash" class="flash" :class="flash.type">{{ flash.text }}</div>
          </transition>
        </div>

        <div class="catalog-scroll scroll-y">
          <div class="catalog-grid">
            <button
              v-for="c in store.catalog"
              :key="c.sku"
              class="prod"
              :disabled="store.availableOf(c.sku) <= 0"
              @click="quickAdd(c.sku)"
            >
              <div class="prod-top">
                <span class="prod-sku muted">{{ c.sku }}</span>
                <span class="stock-pill" :class="{ low: store.availableOf(c.sku) <= 3 }">
                  {{ store.availableOf(c.sku) }} disp.
                </span>
              </div>
              <div class="prod-name">{{ c.name }}</div>
              <div class="prod-foot">
                <span class="prod-price">{{ cop(c.basePrice) }}</span>
                <span class="prod-add">+ agregar</span>
              </div>
            </button>
          </div>
        </div>
      </section>

      <!-- ---------- TICKET (derecha, fijo) ---------- -->
      <aside class="ticket">
        <div class="ticket-head">
          <div class="ticket-title">
            <span>Venta en curso</span>
            <span class="muted">#{{ String(store.facturaSeq).padStart(4, "0") }}</span>
          </div>
          <select
            class="input customer-select"
            :value="store.customer"
            @change="store.setCustomer($event.target.value)"
          >
            <option v-for="c in store.customers" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <div v-if="store.cart.length === 0" class="ticket-empty">
          <div class="empty-mark">🧾</div>
          <p>La venta está vacía</p>
          <p class="muted">Escanea, elige del catálogo o agrega una venta libre.</p>
        </div>

        <div v-else class="ticket-lines scroll-y">
          <div v-for="l in store.cart" :key="l.id" class="line">
            <div class="line-info">
              <div class="line-name">{{ l.name }}</div>
              <div class="line-tags">
                <span v-if="l.freeform" class="badge badge-free">venta libre</span>
                <span v-else-if="l.discounted" class="badge badge-discount">descuento</span>
                <span class="line-sku muted">{{ l.sku ? l.sku : "sin inventario" }}</span>
              </div>
            </div>

            <div class="line-controls">
              <button v-if="editing && editing.id === l.id ? false : true" class="price-btn" title="Editar precio / descuento" @click="startEdit(l)">
                <span v-if="l.discounted" class="strike">{{ cop(l.basePrice) }}</span>
                <span>{{ cop(l.unitPrice) }}</span>
              </button>
              <input
                v-else
                id="edit-price"
                v-model="editing.value"
                class="input price-input"
                type="number"
                @keydown.enter="confirmEdit"
                @blur="confirmEdit"
              />

              <div class="qty">
                <button class="qbtn" aria-label="Restar" @click="store.dec(l.id)">−</button>
                <span class="qval">{{ l.qty }}</span>
                <button class="qbtn" aria-label="Sumar" @click="onInc(l.id)">+</button>
              </div>
            </div>

            <div class="line-right">
              <div class="line-total">{{ cop(l.unitPrice * l.qty) }}</div>
              <button class="del" aria-label="Quitar" @click="store.remove(l.id)">✕</button>
            </div>
          </div>
        </div>

        <div class="ticket-foot">
          <div class="trow">
            <span class="muted">Subtotal ({{ store.itemCount }} art.)</span>
            <span>{{ cop(store.subtotal.toNumber()) }}</span>
          </div>
          <div class="trow">
            <span class="muted">IVA</span>
            <span>{{ cop(store.ivaTotal.toNumber()) }}</span>
          </div>
          <div class="trow total">
            <span>Total</span>
            <span>{{ cop(store.total.toNumber()) }}</span>
          </div>
          <div class="foot-actions">
            <button
              class="btn btn-ghost"
              :disabled="store.cart.length === 0"
              @click="store.clearCart()"
            >
              Vaciar
            </button>
            <button class="btn btn-primary btn-lg cobrar" @click="openPay">
              Cobrar {{ cop(store.total.toNumber()) }}
            </button>
          </div>
        </div>
      </aside>
    </div>

    <!-- ================= SLIDE-OVER: Facturas ================= -->
    <transition name="slide">
      <div v-if="facturasOpen" class="slideover-wrap">
        <div class="slideover-backdrop" @click="facturasOpen = false"></div>
        <div class="slideover">
          <div class="slideover-head">
            <span>Últimas facturas</span>
            <button class="del" @click="facturasOpen = false">✕</button>
          </div>
          <div v-if="store.facturas.length === 0" class="muted so-empty">
            Las ventas cobradas aparecerán aquí.
          </div>
          <ul v-else class="fact-list scroll-y">
            <li v-for="f in store.facturas" :key="f.number" class="fact-item" @click="viewing = f">
              <div>
                <div class="fact-num">Factura #{{ f.number }}</div>
                <div class="muted fact-meta">{{ fmtTime(f.createdAt) }} · {{ f.customer }} · {{ f.method }}</div>
              </div>
              <div class="fact-total">{{ cop(f.total) }}</div>
            </li>
          </ul>
        </div>
      </div>
    </transition>

    <!-- ================= MODAL: Venta libre ================= -->
    <div v-if="freeform.open" class="overlay" @click.self="freeform.open = false">
      <div class="modal">
        <h3 class="modal-title">Venta libre</h3>
        <p class="muted modal-desc">
          Para algo sin referencia previa (típicamente a peso/volumen, ej. "234gr de azúcar").
          No descuenta inventario.
        </p>
        <label class="field-label muted">Descripción</label>
        <input id="ff-name" v-model="freeform.name" class="input" placeholder="234gr de tornillos surtidos" />
        <div class="ff-grid">
          <div>
            <label class="field-label muted">Precio total</label>
            <input v-model="freeform.price" class="input" type="number" placeholder="6000" min="0" @keydown.enter="confirmFreeform" />
          </div>
          <div>
            <label class="field-label muted">IVA %</label>
            <input v-model="freeform.ivaPct" class="input" type="number" placeholder="19" min="0" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="freeform.open = false">Cancelar</button>
          <button class="btn btn-primary" @click="confirmFreeform">Agregar a la venta</button>
        </div>
      </div>
    </div>

    <!-- ================= MODAL: Cobro ================= -->
    <div v-if="pay.open" class="overlay" @click.self="pay.open = false">
      <div class="modal">
        <h3 class="modal-title">Cobrar {{ cop(store.total.toNumber()) }}</h3>
        <div class="methods">
          <button class="method" :class="{ active: pay.method === 'efectivo' }" @click="pay.method = 'efectivo'">Efectivo</button>
          <button class="method" :class="{ active: pay.method === 'tarjeta' }" @click="pay.method = 'tarjeta'">Tarjeta</button>
        </div>

        <template v-if="pay.method === 'efectivo'">
          <label class="field-label muted">Recibe</label>
          <input id="pay-received" v-model="pay.received" class="input input-lg" type="number" placeholder="0" min="0" @keydown.enter="canCharge && confirmPay()" />
          <div class="quick-cash">
            <button v-for="amt in [20000, 50000, 100000]" :key="amt" class="cash-chip" @click="setReceived(amt)">
              {{ cop(amt) }}
            </button>
            <button class="cash-chip" @click="setReceived(store.total.toNumber())">Exacto</button>
          </div>
          <div class="change" :class="{ neg: change < 0 }">
            <span class="muted">Cambio</span>
            <span>{{ change >= 0 ? cop(change) : "Falta " + cop(-change) }}</span>
          </div>
        </template>
        <p v-else class="muted modal-desc">Se registrará como pago con tarjeta.</p>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="pay.open = false">Cancelar</button>
          <button class="btn btn-primary" :disabled="!canCharge" @click="confirmPay">Confirmar cobro</button>
        </div>
      </div>
    </div>

    <!-- ================= MODAL: Detalle de factura ================= -->
    <div v-if="viewing" class="overlay" @click.self="viewing = null">
      <div class="modal">
        <h3 class="modal-title">Factura #{{ viewing.number }}</h3>
        <div class="muted modal-desc">
          {{ new Date(viewing.createdAt).toLocaleString("es-CO") }} · {{ viewing.customer }} · {{ viewing.method }}
        </div>
        <ul class="detail-lines">
          <li v-for="(l, i) in viewing.lines" :key="i">
            <span>{{ l.qty }}× {{ l.name }}<span v-if="l.freeform" class="badge badge-free">libre</span></span>
            <span>{{ cop(l.unitPrice * l.qty) }}</span>
          </li>
        </ul>
        <div class="ticket-foot-mini">
          <div class="trow"><span class="muted">Subtotal</span><span>{{ cop(viewing.subtotal) }}</span></div>
          <div class="trow"><span class="muted">IVA</span><span>{{ cop(viewing.iva) }}</span></div>
          <div class="trow total"><span>Total</span><span>{{ cop(viewing.total) }}</span></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="viewing = null">Cerrar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pos {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ---------- Header ---------- */
.pos-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.7rem 1.5rem;
  background: hsl(var(--background));
  border-bottom: 1px solid hsl(var(--border));
  flex-shrink: 0;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.logo {
  display: grid;
  place-items: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 0.6rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-weight: 700;
  font-size: 1.15rem;
}
.brand-name {
  font-weight: 600;
  font-size: 1rem;
}
.brand-sub {
  font-size: 0.8rem;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}
.day-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.3;
  margin-right: 0.3rem;
}
.day-stat span {
  font-size: 0.72rem;
}
.day-stat strong {
  font-size: 0.9rem;
  font-weight: 600;
}

/* ---------- Body ---------- */
.pos-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* ---------- Catálogo ---------- */
.catalog {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 1.25rem;
  gap: 1rem;
}
.scanbar {
  flex-shrink: 0;
  position: relative;
}
.scan-row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  padding: 0.5rem 0.6rem 0.5rem 1rem;
}
.scan-row:focus-within {
  border-color: hsl(var(--ring));
  box-shadow: 0 0 0 3px hsl(var(--ring) / 0.18);
}
.scan-icon {
  font-size: 1.35rem;
  color: hsl(var(--muted-foreground));
}
.scan-field {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 1.05rem;
  color: hsl(var(--foreground));
  padding: 0.4rem 0;
}
.scan-field::placeholder {
  color: hsl(var(--muted-foreground));
}

.suggestions {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  box-shadow: 0 10px 28px hsl(240 10% 3.9% / 0.14);
  max-height: 380px;
  overflow-y: auto;
  z-index: 30;
  padding: 0.4rem;
}
.suggestion {
  display: grid;
  grid-template-columns: 84px 1fr auto;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  text-align: left;
  padding: 0.6rem 0.7rem;
  border-radius: var(--radius);
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.88rem;
}
.suggestion:hover,
.suggestion.active {
  background: hsl(var(--accent));
}
.sg-sku {
  font-family: ui-monospace, monospace;
  font-size: 0.74rem;
  color: hsl(var(--muted-foreground));
}
.sg-name {
  font-weight: 500;
  color: hsl(var(--foreground));
}
.sg-meta {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  flex-shrink: 0;
}
.sg-stock {
  font-size: 0.72rem;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
}
.sg-stock.low {
  color: hsl(var(--warning-fg));
}
.sg-stock.out {
  color: hsl(var(--destructive));
}
.sg-price {
  font-weight: 600;
  font-size: 0.88rem;
  min-width: 76px;
  text-align: right;
}
.suggestion-empty {
  padding: 0.9rem 0.85rem;
  font-size: 0.85rem;
  color: hsl(var(--muted-foreground));
}
.suggestion-empty kbd {
  background: hsl(var(--secondary));
  color: hsl(var(--secondary-foreground));
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.78rem;
}

.flash {
  margin-top: 0.6rem;
  padding: 0.55rem 0.85rem;
  border-radius: var(--radius);
  font-size: 0.85rem;
}
.flash.error {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}
.flash.ok {
  background: hsl(var(--success) / 0.14);
  color: hsl(142 71% 30%);
}

.catalog-scroll {
  flex: 1;
  min-height: 0;
}
.catalog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 0.9rem;
  align-content: start;
  padding-bottom: 1rem;
}
.prod {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0.9rem;
  text-align: left;
  min-height: 128px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  padding: 0.85rem 0.95rem;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.05s;
}
.prod:hover:not(:disabled) {
  border-color: hsl(var(--primary) / 0.55);
  box-shadow: 0 2px 10px hsl(var(--primary) / 0.1);
}
.prod:active:not(:disabled) {
  transform: scale(0.985);
}
.prod:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.prod-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.prod-sku {
  font-size: 0.74rem;
  font-family: ui-monospace, monospace;
}
.stock-pill {
  font-size: 0.7rem;
  font-weight: 500;
  background: hsl(var(--secondary));
  color: hsl(var(--secondary-foreground));
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
}
.stock-pill.low {
  background: hsl(var(--warning-bg));
  color: hsl(var(--warning-fg));
}
.prod-name {
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.35;
}
.prod-foot {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.prod-price {
  font-size: 1.05rem;
  font-weight: 600;
}
.prod-add {
  font-size: 0.78rem;
  color: hsl(var(--accent-foreground));
  opacity: 0;
  transition: opacity 0.15s;
}
.prod:hover:not(:disabled) .prod-add {
  opacity: 1;
}

/* ---------- Ticket ---------- */
.ticket {
  width: 440px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: hsl(var(--background));
  border-left: 1px solid hsl(var(--border));
}
.ticket-head {
  padding: 1.1rem 1.25rem 0.85rem;
  border-bottom: 1px solid hsl(var(--border));
  flex-shrink: 0;
}
.ticket-title {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-weight: 600;
  font-size: 1.05rem;
  margin-bottom: 0.7rem;
}
.ticket-title .muted {
  font-size: 0.85rem;
  font-weight: 400;
  font-family: ui-monospace, monospace;
}
.customer-select {
  width: 100%;
}
.ticket-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
}
.empty-mark {
  font-size: 2.4rem;
  margin-bottom: 0.6rem;
  opacity: 0.85;
}
.ticket-empty p {
  margin: 0.2rem 0;
}
.ticket-lines {
  flex: 1;
  min-height: 0;
  padding: 0.5rem 0.5rem;
}
.line {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.4rem 0.75rem;
  padding: 0.7rem 0.75rem;
  border-radius: var(--radius);
  border-bottom: 1px solid hsl(var(--border));
}
.line:hover {
  background: hsl(var(--muted));
}
.line-info {
  grid-column: 1;
}
.line-name {
  font-size: 0.9rem;
  font-weight: 500;
  line-height: 1.3;
}
.line-tags {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.2rem;
}
.line-sku {
  font-size: 0.73rem;
  font-family: ui-monospace, monospace;
}
.line-right {
  grid-column: 2;
  grid-row: 1 / span 2;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.4rem;
}
.line-total {
  font-size: 0.95rem;
  font-weight: 600;
}
.line-controls {
  grid-column: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.15rem;
}
.price-btn {
  background: transparent;
  border: 1px dashed hsl(var(--border));
  border-radius: var(--radius);
  padding: 0.2rem 0.5rem;
  cursor: pointer;
  font-size: 0.82rem;
  display: flex;
  gap: 0.35rem;
  align-items: center;
  color: hsl(var(--foreground));
}
.price-btn:hover {
  background: hsl(var(--accent));
  border-color: hsl(var(--primary) / 0.4);
}
.price-input {
  width: 110px;
  height: 2rem;
}
.qty {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.qbtn {
  width: 1.8rem;
  height: 1.8rem;
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  cursor: pointer;
  font-size: 1.05rem;
  line-height: 1;
}
.qbtn:hover {
  background: hsl(var(--accent));
  border-color: hsl(var(--primary) / 0.4);
}
.qval {
  min-width: 1.6rem;
  text-align: center;
  font-size: 0.95rem;
  font-weight: 600;
}
.del {
  background: transparent;
  border: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  font-size: 0.85rem;
}
.del:hover {
  color: hsl(var(--destructive));
}

.ticket-foot {
  border-top: 1px solid hsl(var(--border));
  padding: 1rem 1.25rem 1.25rem;
  background: hsl(var(--card));
  flex-shrink: 0;
}
.trow {
  display: flex;
  justify-content: space-between;
  padding: 0.22rem 0;
  font-size: 0.9rem;
}
.trow.total {
  font-size: 1.5rem;
  font-weight: 700;
  border-top: 1px solid hsl(var(--border));
  margin-top: 0.5rem;
  padding-top: 0.7rem;
}
.foot-actions {
  display: flex;
  gap: 0.6rem;
  margin-top: 1rem;
}
.foot-actions .btn-ghost {
  flex-shrink: 0;
}
.cobrar {
  flex: 1;
  font-size: 1.05rem;
}

/* ---------- Slide-over facturas ---------- */
.slideover-wrap {
  position: fixed;
  inset: 0;
  z-index: 40;
}
.slideover-backdrop {
  position: absolute;
  inset: 0;
  background: hsl(240 10% 3.9% / 0.35);
}
.slideover {
  position: absolute;
  top: 0;
  right: 0;
  height: 100vh;
  width: 400px;
  background: hsl(var(--background));
  border-left: 1px solid hsl(var(--border));
  display: flex;
  flex-direction: column;
  padding: 1.1rem 1.1rem 1.1rem;
}
.slideover-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 0.9rem;
}
.so-empty {
  font-size: 0.85rem;
  padding: 0.5rem 0;
}
.fact-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
}
.fact-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.7rem 0.5rem;
  border-radius: var(--radius);
  cursor: pointer;
  border-bottom: 1px solid hsl(var(--border));
}
.fact-item:hover {
  background: hsl(var(--muted));
}
.fact-num {
  font-weight: 500;
  font-size: 0.88rem;
}
.fact-meta {
  font-size: 0.73rem;
}
.fact-total {
  font-weight: 600;
  font-size: 0.9rem;
}

/* ---------- Modales ---------- */
.overlay {
  position: fixed;
  inset: 0;
  background: hsl(240 10% 3.9% / 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  z-index: 50;
}
.modal {
  width: 100%;
  max-width: 440px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.85rem;
  padding: 1.4rem;
}
.modal-title {
  margin: 0 0 0.4rem;
  font-size: 1.2rem;
  font-weight: 600;
}
.modal-desc {
  font-size: 0.85rem;
  margin: 0 0 0.9rem;
  line-height: 1.5;
}
.field-label {
  display: block;
  font-size: 0.78rem;
  margin: 0.6rem 0 0.35rem;
}
.ff-grid {
  display: grid;
  grid-template-columns: 1fr 100px;
  gap: 0.7rem;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 1.4rem;
}
.methods {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
  margin-bottom: 1rem;
}
.method {
  padding: 0.8rem;
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  cursor: pointer;
  font-weight: 500;
  font-size: 0.95rem;
}
.method.active {
  border-color: hsl(var(--primary));
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
}
.quick-cash {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.7rem;
  flex-wrap: wrap;
}
.cash-chip {
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  cursor: pointer;
  font-size: 0.85rem;
}
.cash-chip:hover {
  background: hsl(var(--accent));
  border-color: hsl(var(--primary) / 0.4);
}
.change {
  display: flex;
  justify-content: space-between;
  margin-top: 0.9rem;
  font-size: 1.25rem;
  font-weight: 700;
}
.change.neg {
  color: hsl(var(--destructive));
}
.detail-lines {
  list-style: none;
  margin: 0 0 0.8rem;
  padding: 0;
}
.detail-lines li {
  display: flex;
  justify-content: space-between;
  padding: 0.4rem 0;
  font-size: 0.88rem;
  border-bottom: 1px solid hsl(var(--border));
}
.detail-lines .badge {
  margin-left: 0.4rem;
}
.ticket-foot-mini .trow.total {
  font-size: 1.15rem;
}

/* ---------- Transiciones ---------- */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.slide-enter-active .slideover,
.slide-leave-active .slideover {
  transition: transform 0.22s ease;
}
.slide-enter-from .slideover,
.slide-leave-to .slideover {
  transform: translateX(100%);
}
.slide-enter-active .slideover-backdrop,
.slide-leave-active .slideover-backdrop {
  transition: opacity 0.22s;
}
.slide-enter-from .slideover-backdrop,
.slide-leave-to .slideover-backdrop {
  opacity: 0;
}
</style>
