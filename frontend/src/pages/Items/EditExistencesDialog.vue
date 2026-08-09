<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { toast } from "vue-sonner"
import { IconCurrencyDollar, IconPercentage } from "@tabler/icons-vue"

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { computeSalePrice, toDecimal } from "@/lib/money"
import { useAnimatedCurrency } from "@/composables/useAnimatedCurrency"
import { itemsApi } from "@/api/items/items.api"
import { locationsApi } from "@/api/locations/locations.api"
import type { ILocation } from "@/api/locations/locations.types"
import type { IItemExistence, IItemUpdatePayload } from "@/api/items/items.types"
import type { IProvider } from "@/api/references/references.types"

/**
 * Reasigna proveedor, ubicación y/o los numéricos por unidad (costo de
 * proveedor, precio base, IVA — D-45/migración 0007-0008) a **todas** las
 * existencias seleccionadas de una sola vez. Cada existencia puede tener
 * legítimamente un valor propio distinto al catálogo (lotes de compra
 * distintos, ajustes puntuales) — "vida propia" frente a la Referencia que
 * la origina — así que esto es exactamente para ese caso: corregir varias
 * juntas cuando divergieron por alguna razón real.
 *
 * El precio de venta NO se captura acá — misma dinámica que crear una
 * Referencia: se deriva de precio base + IVA (D-45/D-46) y se muestra como
 * vista previa calculada, nunca como input. El servidor recalcula el valor
 * real al guardar.
 */
const props = defineProps<{
  itemIds: string[]
  providers: IProvider[]
  /** Existencias visibles en pantalla — de acá se lee el proveedor/ubicación actual para prellenar. */
  existences: IItemExistence[]
}>()

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{
  updated: []
}>()

/** `SelectItem` de reka-ui no acepta value vacío, así que "sin asignar" necesita un centinela. */
const NONE = "__none__"

/**
 * Valor inicial de un select: si TODAS las existencias seleccionadas
 * comparten el mismo proveedor/ubicación (incluido "ninguna" para las dos),
 * se prellena con ese valor — igual que editar una sola. Si divergen, el
 * campo arranca vacío en vez de insinuar una uniformidad que no existe.
 */
function uniformValue(ids: string[], existences: IItemExistence[], getValue: (e: IItemExistence) => string | null) {
  const selected = existences.filter(existence => ids.includes(existence.item_id))
  if (selected.length === 0) return NONE
  const first = getValue(selected[0])
  const allShareValue = selected.every(existence => getValue(existence) === first)
  return allShareValue ? (first ?? NONE) : NONE
}

/**
 * Igual que `uniformValue`, pero para los numéricos: compara por valor
 * decimal (no por texto) para no fallar por un formato distinto del mismo
 * número, y devuelve el valor ya en el formato que espera `NumericMaskInput`
 * al prellenar — un `Number` limpio, no el string decimal crudo del backend
 * ("38900.00"), que hace que Maska reprocese mal el punto al montar.
 */
function uniformDecimalValue(ids: string[], existences: IItemExistence[], getValue: (e: IItemExistence) => string | null): string {
  const selected = existences.filter(existence => ids.includes(existence.item_id))
  if (selected.length === 0) return ""
  const first = getValue(selected[0])
  if (first === null) return ""
  const allShareValue = selected.every((existence) => {
    const value = getValue(existence)
    return value !== null && toDecimal(value).equals(toDecimal(first))
  })
  return allShareValue ? String(toDecimal(first).toNumber()) : ""
}

const providerValue = ref(NONE)
const locationValue = ref(NONE)
/** Snapshot del valor con el que se abrió el modal — lo que no cambió acá no se manda. */
const providerInitial = ref(NONE)
const locationInitial = ref(NONE)
const isSubmitting = ref(false)

/**
 * Los numéricos son texto libre, no un `Select` con opciones fijas, así que
 * "sin cambios" no necesita centinela: vacío ya significa eso. Igual que
 * proveedor/ubicación, se prellenan con el valor vigente de la existencia
 * (`uniformDecimalValue`) para que el usuario vea de una el dato que va a
 * ajustar en vez de tener que ir a buscarlo en la card. `xInitial` guarda ese
 * arranque para no reenviar lo que nadie tocó — y para poder distinguir
 * "lo dejé como estaba" de "lo vacié a propósito" (esto último resetea al
 * catálogo, ver `ItemUpdate` en el backend).
 */
const basePriceInput = ref("")
const ivaInput = ref("")
const providerPriceInput = ref("")
const basePriceInitial = ref("")
const ivaInitial = ref("")
const providerPriceInitial = ref("")

const basePriceError = computed(() => {
  if (basePriceInput.value === "") return null
  return toDecimal(basePriceInput.value).lte(0) ? "Debe ser mayor a 0" : null
})
const ivaError = computed(() => {
  if (ivaInput.value === "") return null
  const value = toDecimal(ivaInput.value)
  return value.lt(0) || value.gt(100) ? "Debe estar entre 0 y 100" : null
})
const providerPriceError = computed(() => {
  if (providerPriceInput.value === "") return null
  return toDecimal(providerPriceInput.value).lt(0) ? "No puede ser negativo" : null
})
const hasFieldErrors = computed(() =>
  basePriceError.value !== null || ivaError.value !== null || providerPriceError.value !== null,
)

/**
 * Vista previa de precio de venta: solo se puede calcular cuando base e IVA
 * están los dos presentes y válidos — igual que en crear Referencia, es un
 * valor derivado, no algo que el usuario tipee. Con `useAnimatedCurrency`
 * necesitamos un `Decimal` siempre disponible; `hasSalePricePreview` es la
 * bandera real que decide si se muestra el valor o el placeholder.
 */
const hasSalePricePreview = computed(() =>
  basePriceInput.value !== "" && ivaInput.value !== "" && basePriceError.value === null && ivaError.value === null,
)
const salePriceDecimal = computed(() =>
  hasSalePricePreview.value ? computeSalePrice(basePriceInput.value, ivaInput.value) : toDecimal(0),
)
const salePriceDisplay = useAnimatedCurrency(salePriceDecimal)

const locations = ref<ILocation[]>([])
const isLoadingLocations = ref(false)

watch(open, (isOpen) => {
  if (!isOpen) {
    return
  }
  providerValue.value = uniformValue(props.itemIds, props.existences, existence => existence.provider_id)
  locationValue.value = uniformValue(props.itemIds, props.existences, existence => existence.location_id)
  providerInitial.value = providerValue.value
  locationInitial.value = locationValue.value

  basePriceInput.value = uniformDecimalValue(props.itemIds, props.existences, existence => existence.base_price)
  ivaInput.value = uniformDecimalValue(props.itemIds, props.existences, existence => existence.iva_percentage)
  providerPriceInput.value = uniformDecimalValue(props.itemIds, props.existences, existence => existence.provider_price)
  basePriceInitial.value = basePriceInput.value
  ivaInitial.value = ivaInput.value
  providerPriceInitial.value = providerPriceInput.value
  if (locations.value.length === 0) {
    isLoadingLocations.value = true
    locationsApi.getLocations()
      .then(({ data }) => { locations.value = data })
      .catch(() => {
        toast.error("No se pudieron cargar las ubicaciones", { position: "bottom-center" })
      })
      .finally(() => { isLoadingLocations.value = false })
  }
})

/** Sin esto no hay nada que mandar: nada tocado es un submit vacío. */
const hasChanges = computed(() =>
  providerValue.value !== providerInitial.value
  || locationValue.value !== locationInitial.value
  || basePriceInput.value !== basePriceInitial.value
  || ivaInput.value !== ivaInitial.value
  || providerPriceInput.value !== providerPriceInitial.value,
)

async function onSubmit() {
  const payload: IItemUpdatePayload = {}
  if (providerValue.value !== providerInitial.value) {
    payload.provider_id = providerValue.value === NONE ? null : providerValue.value
  }
  if (locationValue.value !== locationInitial.value) {
    payload.location_id = locationValue.value === NONE ? null : locationValue.value
  }
  //  Vaciar un campo que arrancó con valor es una decisión explícita de
  //  volver al catálogo (`null` → COALESCE en el backend), no "no tocar".
  if (basePriceInput.value !== basePriceInitial.value) {
    payload.base_price = basePriceInput.value === "" ? null : basePriceInput.value
  }
  if (ivaInput.value !== ivaInitial.value) {
    payload.iva_percentage = ivaInput.value === "" ? null : ivaInput.value
  }
  if (providerPriceInput.value !== providerPriceInitial.value) {
    payload.provider_price = providerPriceInput.value === "" ? null : providerPriceInput.value
  }

  isSubmitting.value = true
  try {
    const results = await Promise.allSettled(
      props.itemIds.map(id => itemsApi.updateItem(id, payload)),
    )
    const succeeded = results.filter(result => result.status === "fulfilled").length
    const failed = results.length - succeeded

    if (succeeded > 0) {
      toast.success(
        succeeded === 1 ? "Existencia actualizada" : `${succeeded} existencias actualizadas`,
        { position: "bottom-center" },
      )
      emit("updated")
      open.value = false
    }
    if (failed > 0) {
      toast.error(
        succeeded > 0
          ? `${failed} de ${results.length} no se pudieron actualizar`
          : "No se pudo actualizar",
        { position: "bottom-center" },
      )
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle>
          Editar {{ itemIds.length === 1 ? "existencia" : `${itemIds.length} existencias` }}
        </DialogTitle>
        <DialogDescription>
          Proveedor y ubicación son opcionales — se guardan tal como queden. Los campos numéricos vacíos no se tocan.
        </DialogDescription>
      </DialogHeader>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div class="grid gap-2">
          <Label>Proveedor</Label>
          <Select v-model="providerValue">
            <SelectTrigger class="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem :value="NONE">
                Sin asignar
              </SelectItem>
              <SelectItem v-for="provider in providers" :key="provider.id" :value="provider.id">
                {{ provider.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="grid gap-2">
          <Label>Ubicación</Label>
          <Select v-model="locationValue">
            <SelectTrigger class="w-full">
              <SelectValue :placeholder="isLoadingLocations ? 'Cargando…' : undefined" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem :value="NONE">
                Sin asignar
              </SelectItem>
              <SelectItem v-for="location in locations" :key="location.id" :value="location.id">
                {{ location.name }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!--
          Prellenados con el valor vigente de la existencia (`uniformDecimalValue`):
          si todas las seleccionadas comparten el mismo número, de una se ve —
          si divergen o no hay dato, arranca vacío en vez de mentir una uniformidad.
        -->
        <div class="grid gap-2">
          <Label>Precio proveedor</Label>
          <div class="relative">
            <IconCurrencyDollar class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <NumericMaskInput v-model="providerPriceInput" class="pl-8" placeholder="Sin cambios" />
          </div>
          <p v-if="providerPriceError" class="text-xs text-destructive">
            {{ providerPriceError }}
          </p>
        </div>

        <div class="grid gap-2">
          <Label>Precio base</Label>
          <div class="relative">
            <IconCurrencyDollar class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <NumericMaskInput v-model="basePriceInput" class="pl-8" placeholder="Sin cambios" />
          </div>
          <p v-if="basePriceError" class="text-xs text-destructive">
            {{ basePriceError }}
          </p>
        </div>

        <div class="grid gap-2">
          <Label>IVA</Label>
          <div class="relative">
            <IconPercentage class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <NumericMaskInput v-model="ivaInput" :max="100" class="pl-8" placeholder="Sin cambios" />
          </div>
          <p v-if="ivaError" class="text-xs text-destructive">
            {{ ivaError }}
          </p>
        </div>

        <!--
          No es un input: el precio de venta se deriva de base + IVA, misma
          dinámica que crear una Referencia (D-45/D-46) — nunca se captura a
          mano. El servidor recalcula el valor real al guardar.
        -->
        <div class="grid gap-2">
          <Label>Precio de venta</Label>
          <div class="flex h-9 items-center rounded-md border border-input bg-muted/40 px-3 text-sm">
            <span v-if="hasSalePricePreview">{{ salePriceDisplay }}</span>
            <span v-else class="text-muted-foreground">Se calcula con precio base + IVA</span>
          </div>
        </div>
      </div>

      <DialogFooter>
        <Button
          type="button"
          :disabled="!hasChanges || hasFieldErrors || isSubmitting"
          class="text-white hover:text-white"
          @click="onSubmit"
        >
          {{ isSubmitting ? "Guardando…" : "Guardar cambios" }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
