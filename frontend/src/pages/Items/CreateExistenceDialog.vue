<script setup lang="ts">
import { ref, watch } from "vue"
import { toTypedSchema } from "@vee-validate/zod"
import { useForm } from "vee-validate"
import { z } from "zod"
import { IconMinus, IconPlus } from "@tabler/icons-vue"
import { toast } from "vue-sonner"

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
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { numericField, toDecimal } from "@/lib/money"
import { itemsApi } from "@/api/items/items.api"
import { locationsApi } from "@/api/locations/locations.api"
import type { ILocation } from "@/api/locations/locations.types"
import type { IProvider } from "@/api/references/references.types"

/**
 * Una de varias formas posibles de crear existencias (alta manual, aquí).
 * Import/carga masiva desde proveedor, etc. quedan para más adelante — no se
 * diseña esta pantalla para cubrirlas todas de una vez.
 */
const props = defineProps<{
  referenceId: string
  /** Precio de catálogo (D-45/D-46) — precarga el campo, editable por si esta tanda entra con descuento. */
  defaultPrice: string
  providers: IProvider[]
}>()

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{
  /** El padre decide cómo refrescar (`fetchDetail`) — este diálogo no conoce el store. */
  created: []
}>()

/** Tope de la botonera: pasado esto, un lote es justo el caso que va a necesitar el input numérico que menciona el negocio. */
const MAX_QUANTITY = 100
const quantity = ref(1)
/**
 * Texto tal cual lo escribe el usuario — separado de `quantity` para poder
 * dejar el input momentáneamente vacío mientras retipea (ej. borrar "1" para
 * escribir "30") sin que cada tecla dispare un clamp que lo vuelva a "1" a
 * medio camino.
 */
const quantityInput = ref("1")

watch(quantityInput, (raw) => {
  const parsed = Math.trunc(Number(raw))
  if (Number.isInteger(parsed) && parsed >= 1 && parsed <= MAX_QUANTITY) {
    quantity.value = parsed
  }
})

/** Al salir del campo, lo que haya quedado (vacío, 0, fuera de rango) se corrige al último valor válido. */
function normalizeQuantityInput() {
  quantityInput.value = String(quantity.value)
}

const locations = ref<ILocation[]>([])
const isLoadingLocations = ref(false)

/**
 * `SelectItem` de reka-ui no acepta value vacío, y proveedor/ubicación son
 * opcionales (migración 0005: el alta manual rápida no exige elegirlos en el
 * momento) — así que "sin asignar" necesita un centinela, igual que el patrón
 * ya usado para "todas las categorías" en otras pantallas.
 */
const NONE_PROVIDER = "__none_provider__"
const NONE_LOCATION = "__none_location__"

const formSchema = toTypedSchema(z.object({
  provider_id: z.string(),
  location_id: z.string(),
  current_price: numericField("El precio es obligatorio").pipe(
    z.number().positive("El precio debe ser mayor a 0"),
  ),
}))

const { handleSubmit, resetForm, isSubmitting } = useForm({
  validationSchema: formSchema,
  initialValues: {
    provider_id: NONE_PROVIDER,
    location_id: NONE_LOCATION,
    current_price: undefined,
  },
})

/**
 * Locaciones y precio inicial se cargan/prellenan **al abrir**, no al montar:
 * el diálogo vive montado detrás de escena entre aperturas (`v-model:open`),
 * así que "al montar" solo correría la primera vez.
 */
watch(open, (isOpen) => {
  if (!isOpen) {
    return
  }
  quantity.value = 1
  quantityInput.value = "1"
  resetForm({
    values: {
      provider_id: NONE_PROVIDER,
      location_id: NONE_LOCATION,
      // `Number`, no un string con ".00": `NumericMaskInput` reprocesa
      // `el.value` con Maska al montarse, y un punto decimal literal en el
      // string lo confunde (concatena los dígitos y agrupa mal, ej.
      // "216600.00" → "21'660.000"). Mismo patrón que usa `referencesNew.vue`
      // al precargar precios en modo edición.
      current_price: toDecimal(props.defaultPrice).toNumber(),
    },
  })
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

function decrement() {
  quantity.value = Math.max(1, quantity.value - 1)
  quantityInput.value = String(quantity.value)
}

function increment() {
  quantity.value = Math.min(MAX_QUANTITY, quantity.value + 1)
  quantityInput.value = String(quantity.value)
}

const onSubmit = handleSubmit(async (values) => {
  const price = String(values.current_price)
  const payload = {
    reference_id: props.referenceId,
    // El centinela vuelve a `null` al salir: proveedor/ubicación son
    // opcionales, "sin asignar" no es un ID real.
    provider_id: values.provider_id === NONE_PROVIDER ? null : values.provider_id,
    location_id: values.location_id === NONE_LOCATION ? null : values.location_id,
    // Una fila por unidad física (D-41): un lote de N no es un `Item` con
    // `quantity: N`, son N Ítems con `quantity: 1` — así se puede dar de baja
    // o descontar una sola unidad sin partir el lote.
    quantity: "1",
    current_price: price,
  }

  const results = await Promise.allSettled(
    Array.from({ length: quantity.value }, () => itemsApi.createItem(payload)),
  )
  const succeeded = results.filter(result => result.status === "fulfilled").length
  const failed = results.length - succeeded

  if (succeeded > 0) {
    toast.success(
      succeeded === 1 ? "Existencia agregada" : `${succeeded} existencias agregadas`,
      { position: "bottom-center" },
    )
    emit("created")
    open.value = false
  }
  if (failed > 0) {
    toast.error(
      succeeded > 0
        ? `${failed} de ${results.length} no se pudieron crear`
        : "No se pudo agregar la existencia",
      { position: "bottom-center" },
    )
  }
})
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>
          Agregar existencia
        </DialogTitle>
        <DialogDescription>
          Alta manual — precio de esta tanda. Proveedor y ubicación son opcionales, se pueden completar después.
        </DialogDescription>
      </DialogHeader>

      <form class="space-y-4" @submit="onSubmit">
        <FormField v-slot="{ componentField }" name="provider_id">
          <FormItem>
            <FormLabel>Proveedor <span class="font-normal text-muted-foreground">(opcional)</span></FormLabel>
            <Select v-bind="componentField">
              <FormControl>
                <SelectTrigger class="w-full">
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem :value="NONE_PROVIDER">
                  Sin asignar
                </SelectItem>
                <SelectItem v-for="provider in providers" :key="provider.id" :value="provider.id">
                  {{ provider.title }}
                </SelectItem>
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormField v-slot="{ componentField }" name="location_id">
          <FormItem>
            <FormLabel>Ubicación <span class="font-normal text-muted-foreground">(opcional)</span></FormLabel>
            <Select v-bind="componentField">
              <FormControl>
                <SelectTrigger class="w-full">
                  <SelectValue :placeholder="isLoadingLocations ? 'Cargando…' : undefined" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem :value="NONE_LOCATION">
                  Sin asignar
                </SelectItem>
                <SelectItem v-for="location in locations" :key="location.id" :value="location.id">
                  {{ location.name }}
                </SelectItem>
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormField v-slot="{ componentField }" name="current_price">
          <FormItem>
            <FormLabel>Precio de venta de esta tanda</FormLabel>
            <FormControl>
              <NumericMaskInput v-bind="componentField" />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>

        <!-- Botonera + input: para un lote grande (30, 50…) escribir el número gana a hacer 30 clicks. -->
        <div class="grid gap-2">
          <span class="text-sm font-medium">Cantidad</span>
          <div class="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon"
              class="shrink-0"
              :disabled="quantity <= 1"
              @click="decrement"
            >
              <IconMinus class="size-4" />
            </Button>
            <Input
              v-model="quantityInput"
              type="number"
              inputmode="numeric"
              min="1"
              :max="MAX_QUANTITY"
              class="w-20 text-center text-lg font-semibold tabular-nums"
              @blur="normalizeQuantityInput"
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              class="shrink-0"
              :disabled="quantity >= MAX_QUANTITY"
              @click="increment"
            >
              <IconPlus class="size-4" />
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button type="submit" :disabled="isSubmitting" class="text-white hover:text-white">
            {{ isSubmitting ? "Agregando…" : quantity === 1 ? "Agregar Existencia" : `Agregar ${quantity} Existencias` }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
