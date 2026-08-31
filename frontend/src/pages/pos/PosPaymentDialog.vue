<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { watchDebounced } from "@vueuse/core"
import { IconCheck, IconUserPlus } from "@tabler/icons-vue"

import NumericMaskInput from "@/components/NumericMaskInput.vue"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { formatCurrency, toDecimal } from "@/lib/money"
import { customersApi } from "@/api/customers/customers.api"
import CustomerAutocomplete from "./CustomerAutocomplete.vue"
import type { ICustomer } from "@/api/customers/customers.types"
import type Decimal from "decimal.js"

/**
 * Cierre del cobro. Los datos del cliente y el efectivo viven acá y no en el
 * panel lateral (265px) porque ahí entraban a la fuerza: pagar es un momento
 * distinto de armar el detalle, y merece la pantalla completa.
 *
 * Los totales llegan calculados desde el detalle en vez de recalcularse acá:
 * dos fórmulas para la misma cifra es como se termina cobrando un número y
 * mostrando otro.
 */
const props = defineProps<{
  subtotal: Decimal
  ivaTotal: Decimal
  total: Decimal
  isSubmitting?: boolean
}>()

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{
  confirm: [payload: {
    customerId: string | null
    newCustomer: { nit: string | null; fullname: string } | null
    cash: string
  }]
}>()

const documentId = ref("")
const customerName = ref("")
const cash = ref("")
/** Cliente ya existente, resuelto por sugerencia o por coincidencia exacta. `null` = no está en la BBDD. */
const matchedCustomer = ref<ICustomer | null>(null)
const registerCustomer = ref(false)
const isChecking = ref(false)

const nameField = ref<InstanceType<typeof CustomerAutocomplete> | null>(null)
const documentField = ref<InstanceType<typeof CustomerAutocomplete> | null>(null)

/** Cada cobro arranca en blanco: heredar el efectivo del cliente anterior es una vuelta mal dada. */
watch(open, (isOpen) => {
  if (isOpen) {
    documentId.value = ""
    customerName.value = ""
    cash.value = ""
    matchedCustomer.value = null
    registerCustomer.value = false
  }
})

/**
 * Elegir una sugerencia rellena **los dos** campos y fija el cliente: si solo
 * se llenara el campo tocado, el otro quedaría con texto viejo de otro cliente
 * y la factura saldría a nombre de una mezcla de dos personas.
 */
function onCustomerSelected(customer: ICustomer) {
  matchedCustomer.value = customer
  registerCustomer.value = false
  documentField.value?.setQuietly(customer.nit ?? "")
  nameField.value?.setQuietly(customer.fullname)
}

/**
 * Busca coincidencia **exacta** para decidir si hay que ofrecer registrar.
 * Prioriza el documento: es el identificador real del cliente; dos personas
 * pueden llamarse igual, pero no compartir cédula.
 */
async function checkExact() {
  const nit = documentId.value.trim()
  const fullname = customerName.value.trim()
  if (nit === "" && fullname === "") {
    matchedCustomer.value = null
    registerCustomer.value = false
    return
  }
  isChecking.value = true
  try {
    const { data } = await customersApi.lookupCustomer(nit !== "" ? { nit } : { fullname })
    matchedCustomer.value = data
    if (data !== null) {
      registerCustomer.value = false
    }
  } catch {
    matchedCustomer.value = null
  } finally {
    isChecking.value = false
  }
}

watchDebounced([documentId, customerName], checkExact, { debounce: 350 })

/** El cliente no está en la BBDD y hay algo escrito: recién ahí tiene sentido ofrecer registrarlo. */
const isUnknownCustomer = computed(() =>
  !isChecking.value
  && matchedCustomer.value === null
  && (documentId.value.trim() !== "" || customerName.value.trim() !== ""),
)

/** Registrar exige nombre: una cédula suelta no identifica a nadie en una factura. */
const canRegister = computed(() => customerName.value.trim() !== "")

const change = computed(() => toDecimal(cash.value).minus(props.total))
/** Sin efectivo capturado no es que falte plata: es que todavía no la han contado. */
const isCashShort = computed(() => cash.value !== "" && change.value.isNegative())

/**
 * Se puede cobrar si hay plata suficiente **y** el cliente está resuelto: o es
 * uno existente, o se marcó registrarlo (con nombre). Cobrarle a un cliente
 * que no existe y no se va a crear dejaría la factura sin titular.
 */
const canConfirm = computed(() =>
  !props.isSubmitting
  && cash.value !== ""
  && !isCashShort.value
  && (matchedCustomer.value !== null || (registerCustomer.value && canRegister.value)),
)

function onConfirm() {
  emit("confirm", {
    customerId: matchedCustomer.value?.id ?? null,
    newCustomer: matchedCustomer.value !== null
      ? null
      : { nit: documentId.value.trim() || null, fullname: customerName.value.trim() },
    cash: cash.value,
  })
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="sm:max-w-3xl">
      <DialogHeader>
        <DialogTitle>Confirmar pago</DialogTitle>
        <DialogDescription>
          Revisa los totales, identifica al cliente y captura el efectivo recibido.
        </DialogDescription>
      </DialogHeader>

      <!-- Resumen: lo mismo que muestra el panel, para no tener que cerrar el modal a verificar. -->
      <div class="space-y-1.5 rounded-lg border border-border bg-muted/30 p-4 text-sm">
        <div class="flex items-center justify-between gap-2">
          <span class="text-muted-foreground">Subtotal</span>
          <span class="tabular-nums">{{ formatCurrency(subtotal) }}</span>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-muted-foreground">IVA total</span>
          <span class="tabular-nums">{{ formatCurrency(ivaTotal) }}</span>
        </div>
        <div class="flex items-center justify-between gap-2 border-t border-border pt-2">
          <span class="font-medium">Total a pagar</span>
          <span class="text-lg font-bold tabular-nums text-brand-icon">{{ formatCurrency(total) }}</span>
        </div>
      </div>

      <!-- Cédula primero: es el identificador real del cliente, el nombre se repite. -->
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="grid gap-2">
          <Label for="pay-document">Cédula / NIT</Label>
          <CustomerAutocomplete
            id="pay-document"
            ref="documentField"
            v-model="documentId"
            field="nit"
            placeholder="Ingrese"
            @select="onCustomerSelected"
          />
        </div>

        <div class="grid gap-2">
          <Label for="pay-customer">Nombre cliente</Label>
          <CustomerAutocomplete
            id="pay-customer"
            ref="nameField"
            v-model="customerName"
            field="fullname"
            placeholder="Consumidor final"
            @select="onCustomerSelected"
          />
        </div>

        <div class="grid gap-2">
          <Label for="pay-cash">Efectivo</Label>
          <NumericMaskInput
            id="pay-cash"
            v-model="cash"
            placeholder="0"
            :aria-invalid="isCashShort"
          />
        </div>

        <div class="grid gap-2">
          <Label>{{ isCashShort ? "Falta" : "Devuelta" }}</Label>
          <!--
            No es un input: la devuelta se deriva del efectivo menos el total,
            nunca se teclea. Misma altura que el campo de al lado para que la
            fila no se descuadre.

            Y **no se anima**, a diferencia del resto de cifras: es el número
            que el cajero lee para devolver plata de la caja. Mientras el
            contador corre muestra valores que no son el correcto, y acá eso se
            traduce en devolver mal. Que aparezca de una.
          -->
          <div
            class="flex h-9 items-center rounded-md border border-input bg-muted/40 px-3 text-sm font-semibold tabular-nums"
            :class="isCashShort ? 'text-destructive' : ''"
          >
            {{ cash === "" ? "—" : formatCurrency(isCashShort ? change.negated() : change) }}
          </div>
        </div>
      </div>

      <!--
        Solo aparece cuando lo tecleado no coincide **exacto** con ningún
        cliente: es la única situación en la que registrar es la acción
        correcta. Con coincidencia parcial se crearían duplicados del mismo
        cliente ("Andrés" y "Andrés Gómez" como dos personas).
      -->
      <div
        v-if="isUnknownCustomer"
        class="flex items-center gap-3 rounded-lg border border-dashed border-border p-3"
      >
        <IconUserPlus class="size-5 shrink-0 text-muted-foreground" />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium">
            Registrar Cliente
          </p>
          <p class="text-xs text-muted-foreground">
            {{
              canRegister
                ? "Este cliente no está registrado. Se creará junto con la factura."
                : "Escribe el nombre para poder registrarlo."
            }}
          </p>
        </div>
        <Switch
          v-model="registerCustomer"
          :disabled="!canRegister"
          aria-label="Registrar Cliente"
        />
      </div>

      <div
        v-else-if="matchedCustomer"
        class="rounded-lg border border-border bg-muted/30 p-3 text-xs text-muted-foreground"
      >
        Cliente registrado: <span class="font-medium text-foreground">{{ matchedCustomer.fullname }}</span>
      </div>

      <DialogFooter>
        <Button
          class="gap-2 text-white hover:text-white"
          :disabled="!canConfirm"
          @click="onConfirm"
        >
          <IconCheck class="size-4" />
          {{ isSubmitting ? "Cobrando…" : "Confirmar Pago" }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
