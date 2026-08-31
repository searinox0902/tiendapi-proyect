<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import { toTypedSchema } from "@vee-validate/zod"
import { useForm } from "vee-validate"
import { toast } from "vue-sonner"
import { IconAlertTriangle, IconCurrencyDollar, IconPercentage } from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"

import AppSidebar from "@/components/AppSidebar.vue"
import ImageDropCropper from "@/components/ImageDropCropper.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import ReferenceSearchInput from "@/components/ReferenceSearchInput.vue"
import NumericMaskInput from "@/components/NumericMaskInput.vue"
import { useAnimatedCurrency } from "@/composables/useAnimatedCurrency"
import { toDecimal } from "@/lib/money"
import { normalizeSku } from "@/lib/sku"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { isDark } from "@/composables/useTheme"
import { buildReferenceFormSchema } from "@/api/references/references.schema"
import { referencesApi } from "@/api/references/references.api"
import type { IReference, IReferenceVariantInfo } from "@/api/references/references.types"
import { useReferencesStore } from "@/stores/references"

const props = defineProps<{
  /** Presente solo en la ruta `/referencias/editar/:sku` (D: reutilizar este mismo componente para crear y editar). */
  sku?: string
}>()
const isEditMode = computed(() => !!props.sku)

const router = useRouter()
const store = useReferencesStore()

/** `id` real de la Referencia en edición (la ruta la identifica por SKU, pero `PUT /references/{id}` necesita el UUID). */
const editingId = ref<string | undefined>(undefined)
/** Imagen ya persistida de la Referencia en edición (precarga el preview sin pasar por `croppedImage`). */
const existingImageUrl = ref<string | null>(null)

/* ── Modo variante (D-90) ──────────────────────────────────────────────────
 * Una variante es una Referencia propia y completa con SKU único (`ABC#2`);
 * lo único que comparte con sus hermanas es la base del código. Acá el
 * formulario detecta que el SKU tecleado ya existe y, en vez de bloquear con
 * un error, ofrece crear la variante: precarga los datos de la pieza y deja
 * todo editable. El código lo asigna el servidor (`next_sku`), no el usuario.
 */
const variantInfo = ref<IReferenceVariantInfo | null>(null)
const isVariantMode = ref(false)
const isCheckingVariant = ref(false)

/**
 * El código tecleado/elegido ya existe y el usuario todavía no decidió qué
 * hacer. Mientras eso pase se bloquea **todo el resto del formulario y el botón
 * de crear**: dejarlo llenar 10 campos para que el servidor los rechace con un
 * 409 es peor experiencia que pedirle la decisión primero. Se sale cambiando el
 * código por uno libre, o apretando "Crear variante".
 */
const isGated = computed(() => variantInfo.value !== null && !isVariantMode.value)

const { values, handleSubmit, resetForm, isSubmitting, setFieldValue } = useForm({
  validationSchema: computed(() => toTypedSchema(buildReferenceFormSchema())),
  initialValues: {
    sku: "",
    provider_id: undefined,
    brand: undefined,
    category_id: undefined,
    title: "",
    description: "",
    image_url: "",
    provider_price: undefined,
    base_price: undefined,
    iva_percentage: undefined,
  },
})

/** Marcas: no hay catálogo propio en el backend (`brand` es texto libre en `Reference`), así que por ahora se sugieren las que ya existen en el catálogo cargado. */
const brandOptions = computed(() => {
  const unique = new Set(
    store.references.map(reference => reference.brand).filter((brand): brand is string => !!brand),
  )
  return [...unique].sort((a, b) => a.localeCompare(b))
})

onMounted(() => {
  // Las 4 cargas son independientes entre sí: van en paralelo (no encadenadas
  // con await) para que la referencia a editar no quede esperando detrás del
  // catálogo de categorías/proveedores/marcas.
  store.fetchCategories().catch(() => {
    toast.error("No se pudieron cargar las categorías", { position: "bottom-center" })
  })
  store.fetchProviders().catch(() => {
    toast.error("No se pudieron cargar los proveedores", { position: "bottom-center" })
  })
  store.fetchReferences({ limit: 200 }).catch(() => {
    toast.error("No se pudieron cargar las marcas", { position: "bottom-center" })
  })

  if (isEditMode.value && props.sku) {
    referencesApi.lookupReference(props.sku)
      .then(({ data }) => {
        if (data === null) {
          toast.error("No existe una referencia con ese SKU", { position: "bottom-center" })
          router.push({ name: "references" })
          return
        }
        editingId.value = data.id
        existingImageUrl.value = data.image_url
        resetForm({
          values: {
            sku: data.sku,
            provider_id: data.provider_id,
            brand: data.brand ?? undefined,
            category_id: data.category_id ?? undefined,
            title: data.title,
            description: data.description ?? undefined,
            image_url: data.image_url ?? "",
            provider_price: data.provider_price !== null ? Number(data.provider_price) : undefined,
            base_price: Number(data.base_price),
            iva_percentage: Number(data.iva_percentage),
          },
        })
      })
      .catch(() => {
        toast.error("No se pudo cargar la referencia a editar", { position: "bottom-center" })
      })
  }
})

/**
 * Consulta el grupo de variantes al salir del campo SKU. En el blur y no en
 * cada tecla: la oferta "¿crear una variante?" aparecería y desaparecería
 * mientras se escribe, y además ya se normaliza acá mismo (D-85).
 */
async function checkVariantGroup() {
  const sku = normalizeSku(values.sku ?? "")
  setFieldValue("sku", sku)
  if (isEditMode.value || isVariantMode.value || !sku) {
    return
  }
  //  Se abandonó la pieza precargada (se tecleó otro código): se limpia lo
  //  copiado. Dejarlo sería arrancar una Referencia nueva con el nombre y los
  //  precios de otra — un casi-duplicado creado sin querer.
  if (prefilledFrom.value !== null && sku !== prefilledFrom.value) {
    resetForm()
    croppedImage.value = null
    existingImageUrl.value = null
    prefilledFrom.value = null
    setFieldValue("sku", sku)
  }
  isCheckingVariant.value = true
  try {
    const { data } = await referencesApi.getVariantInfo(sku)
    variantInfo.value = data.exists ? data : null
  } catch {
    //  Silencioso a propósito: esto es una comodidad, no una validación. Si
    //  falla, el usuario sigue con el alta normal y el servidor tiene la
    //  última palabra — el índice único de D-90 rechaza el duplicado igual.
    variantInfo.value = null
  } finally {
    isCheckingVariant.value = false
  }
}

/** SKU del que ya se copiaron los datos, para no volver a pedirlos al servidor. */
const prefilledFrom = ref<string | null>(null)

/**
 * Copia la ficha de una pieza al formulario. **La vista previa se alimenta de
 * los `values`**, así que esto es lo que la hace reflejar la pieza elegida —
 * sin esto el panel quedaba vacío mientras el aviso decía que la pieza existe.
 *
 * El SKU no se toca (lo fija el servidor al crear la variante). La imagen va a
 * `existingImageUrl`, que es solo para mostrar: el payload usa el campo del
 * formulario, así que la variante no hereda la URL de la pieza base — se ve de
 * quién viene, pero se guarda limpia.
 */
function prefillFrom(reference: IReference) {
  setFieldValue("provider_id", reference.provider_id)
  setFieldValue("category_id", reference.category_id ?? undefined)
  setFieldValue("brand", reference.brand ?? undefined)
  setFieldValue("title", reference.title)
  setFieldValue("description", reference.description ?? undefined)
  setFieldValue("base_price", Number(reference.base_price))
  setFieldValue("iva_percentage", Number(reference.iva_percentage))
  setFieldValue("provider_price", reference.provider_price !== null ? Number(reference.provider_price) : undefined)
  existingImageUrl.value = reference.image_url
  prefilledFrom.value = reference.sku
}

/**
 * El usuario eligió una Referencia del autocompletado, o sea que la pieza ya
 * está en el catálogo. Se precarga de una —el objeto ya vino en la búsqueda, no
 * hace falta otra consulta— y se pide el grupo para ofrecer la variante, sin
 * esperar al blur: elegir de la lista ya es una acción deliberada.
 *
 * Precargar acá y no al tipear es deliberado: si alguien ya llenó nombre y
 * precios y después edita el SKU a uno que existe, sobreescribirle lo cargado
 * sería hostil. Elegir de la lista, en cambio, es pedir explícitamente esa pieza.
 */
async function onExistingReferencePicked(reference: IReference) {
  if (isEditMode.value) {
    return
  }
  prefillFrom(reference)
  try {
    const { data } = await referencesApi.getVariantInfo(reference.sku)
    variantInfo.value = data.exists ? data : null
  } catch {
    variantInfo.value = null
  }
}

/** Entra en modo variante: asegura la precarga y desbloquea todo menos el SKU. */
async function startVariant() {
  const info = variantInfo.value
  if (!info) {
    return
  }
  //  Solo se consulta si NO se precargó ya (camino de tipear el código a mano,
  //  donde nunca hubo un objeto que copiar).
  if (prefilledFrom.value !== info.base_sku) {
    try {
      const { data } = await referencesApi.lookupReference(info.base_sku)
      if (data) {
        prefillFrom(data)
      }
    } catch {
      toast.error("No se pudieron precargar los datos de la pieza", { position: "bottom-center" })
    }
  }
  isVariantMode.value = true
  setFieldValue("sku", info.next_sku)
}

function cancelVariant() {
  isVariantMode.value = false
  variantInfo.value = null
  //  Se limpia todo, no solo el SKU: quedaba la ficha de otra pieza cargada, y
  //  seguir desde ahí es la receta para crear un casi-duplicado sin querer.
  resetForm()
  croppedImage.value = null
  existingImageUrl.value = null
  prefilledFrom.value = null
  setFieldValue("sku", "")
}

/**
 * La imagen se recorta y se guarda en memoria (`croppedImage`), pero NO se sube
 * todavía: solo se persiste una vez la Referencia se crea con éxito (abajo, en
 * `onSubmit`), para no dejar imágenes huérfanas en el servidor de desarrollo si
 * la creación falla o el usuario nunca llega a enviar el formulario.
 */
const croppedImage = ref<Blob | null>(null)
const imagePreviewUrl = ref<string | null>(null)

watch(croppedImage, (blob) => {
  if (imagePreviewUrl.value) {
    URL.revokeObjectURL(imagePreviewUrl.value)
  }
  imagePreviewUrl.value = blob ? URL.createObjectURL(blob) : null
})

/**
 * Sube la imagen recién recortada usando el SKU YA confirmado por el backend.
 * Medida temporal de desarrollo (D-40/D-58): en producción esto lo maneja el
 * wrapper Tauri contra `appDataDir`, no el backend central. Como estamos en
 * local-first contra una BBDD/servicio local (sin red de por medio), no hay
 * necesidad real de mandar todo en una sola petición atómica: crear la
 * Referencia y luego subir su imagen en dos pasos secuenciales es igual de
 * confiable aquí, y evita tener que resolver el caso "la imagen se subió pero
 * la Referencia falló" (o viceversa) que sí importaría contra un servidor remoto.
 */
async function uploadPendingImage(sku: string): Promise<void> {
  if (!croppedImage.value) {
    return
  }
  try {
    await referencesApi.uploadImage(sku, croppedImage.value)
  } catch {
    toast.error("La referencia se creó, pero no se pudo guardar la imagen", { position: "bottom-center" })
  }
}

const onSubmit = handleSubmit(
  async (formValues) => {
    //  El botón está deshabilitado cuando `isGated`, pero queda una carrera:
    //  tipear un código existente y apretar "Crear" sin haber salido del campo.
    //  El clic dispara el blur y la consulta en paralelo, así que se re-verifica
    //  acá antes de mandar — con `await`, no confiando en el orden de eventos.
    if (!isEditMode.value && !isVariantMode.value) {
      await checkVariantGroup()
      if (isGated.value) {
        toast.error("Ese SKU ya existe: cambialo o creá una variante", { position: "bottom-center" })
        return
      }
    }
    try {
      const payload = {
        provider_id: formValues.provider_id,
        category_id: formValues.category_id ?? null,
        sku: formValues.sku,
        title: formValues.title,
        brand: formValues.brand ?? null,
        description: formValues.description ?? null,
        //  URL manual del formulario si el usuario la escribió (ej. scraping);
        //  si además recorta/sube un archivo, ese resultado la pisa más abajo
        //  con el segundo PUT — subir un archivo local es la opción preferida
        //  sobre depender de un sitio externo (ver advertencia en el campo).
        image_url: formValues.image_url || null,
        base_price: formValues.base_price,
        iva_percentage: formValues.iva_percentage,
        provider_price: formValues.provider_price,
      }

      if (isEditMode.value && editingId.value) {
        await referencesApi.updateReference(editingId.value, payload)
      } else {
        // La imagen se sube DESPUÉS de crear la referencia, no antes ni junto: si
        // la creación falla, nunca se sube nada (ver comentario de `uploadPendingImage`).
        await referencesApi.createReference(payload)
      }

      // Dejar el archivo en disco con el nombre del SKU **es** asociarlo
      // (D-58/D-84): el backend lo encuentra solo al resolver la imagen. Antes
      // acá iba un segundo PUT que persistía la URL absoluta en `image_url`, y
      // eso era justo lo que quemaba `http://localhost:8000` en la BBDD.
      await uploadPendingImage(formValues.sku)

      toast.success(
        isEditMode.value ? "Referencia actualizada correctamente" : "Referencia creada correctamente",
        { position: "bottom-center", duration: 6000 },
      )

      if (isEditMode.value) {
        router.push({ name: "references" })
      } else {
        resetForm()
        croppedImage.value = null
      }
    } catch (error) {
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
      const fallback = isEditMode.value ? "No se pudo actualizar la referencia" : "No se pudo crear la referencia"
      toast.error(typeof detail === "string" ? detail : fallback, {
        position: "bottom-center",
      })
    }
  },
  () => {
    toast.error("Revisa los campos obligatorios antes de continuar", { position: "bottom-center" })
  },
)

onBeforeUnmount(() => {
  if (imagePreviewUrl.value) {
    URL.revokeObjectURL(imagePreviewUrl.value)
  }
})

const providerPriceDecimal = computed(() => toDecimal(values.provider_price))
const basePriceDecimal = computed(() => toDecimal(values.base_price))
const ivaPercentageDecimal = computed(() => toDecimal(values.iva_percentage))
const ivaAmountDecimal = computed(() => basePriceDecimal.value.times(ivaPercentageDecimal.value).dividedBy(100))
/** Precio de venta (`sale_price`, D-45): derivado de precio base + IVA, nunca capturado a mano. */
const salePriceDecimal = computed(() => basePriceDecimal.value.plus(ivaAmountDecimal.value))

/** Animación de cálculos del MVP (D-54): los totales "corren" entre el valor anterior y el nuevo. */
const providerPriceDisplay = useAnimatedCurrency(providerPriceDecimal)
const basePriceDisplay = useAnimatedCurrency(basePriceDecimal)
const ivaAmountDisplay = useAnimatedCurrency(ivaAmountDecimal)
const salePriceDisplay = useAnimatedCurrency(salePriceDecimal)
</script>

<template>
  <SidebarProvider
    :style="{
      '--sidebar-width': 'calc(var(--spacing) * 72)',
      '--header-height': 'calc(var(--spacing) * 12)',
    }"
  >
    <AppSidebar variant="inset" />
    <SidebarInset>
      <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
        <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
          <SidebarTrigger class="-ml-1" />
          <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
          <ModuleNavSelect current="references" />
          <span class="text-muted-foreground text-sm">
            {{ isEditMode ? "Editar" : "Registrar" }}
          </span>
          <div class="ml-auto flex items-center gap-2">
            <Sun class="size-4 text-muted-foreground" />
            <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
            <Moon class="size-4 text-muted-foreground" />
          </div>
        </div>
      </header>

      <div class="flex w-full flex-1 gap-4 p-4 lg:p-6">
        <!-- Formulario -->
        <div class="min-w-0 flex-1 rounded-lg border border-border p-4 lg:p-6">
          <form class="grid grid-cols-1 gap-4 md:grid-cols-2 items-start" @submit.prevent="onSubmit">
            <FormField v-slot="{ componentField }" name="sku">
              <FormItem>
                <FormLabel>SKU</FormLabel>
                <FormControl>
                  <!-- Se normaliza al salir del campo y no en cada tecla (D-85):
                       convertir el espacio a `-` mientras todavía se escribe le
                       mueve el cursor al usuario a mitad de palabra. -->
                  <!-- Autocompletado por código **o nombre** contra el
                       catálogo. En modo variante el código lo fija el servidor
                       (`next_sku`), por eso queda de solo lectura: el usuario
                       lo VE —que era el pedido— pero no lo teclea. -->
                  <ReferenceSearchInput
                    :model-value="componentField.modelValue ?? ''"
                    :disabled="isEditMode || isVariantMode"
                    placeholder="Código o nombre de la pieza"
                    hint="Ya en el catálogo — elegí una para crear una variante"
                    empty-hint="Tu catálogo — escribí un código o un nombre para filtrar"
                    @update:model-value="value => setFieldValue('sku', value)"
                    @select="onExistingReferencePicked"
                    @blur="checkVariantGroup()"
                  />
                </FormControl>
                <p v-if="!isEditMode && !isVariantMode && !values.sku" class="text-xs text-muted-foreground">
                  Si lo dejás vacío, se genera uno automáticamente (<code>GEN-…</code>).
                </p>
                <FormMessage v-if="!isVariantMode" />
              </FormItem>
            </FormField>

            <!--
              Oferta de variante: el SKU tecleado ya existe. En vez de cerrar
              el paso con un error, se propone el camino correcto (D-90) — un
              mismo código de proveedor cubre a veces piezas distintas
              (delantero/trasero, 120/130 eslabones).
            -->
            <div
              v-if="variantInfo && !isVariantMode"
              class="md:col-span-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 px-4 py-3"
            >
              <p class="flex items-start gap-2 text-sm">
                <IconAlertTriangle class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <span>
                  El SKU <strong>{{ variantInfo.base_sku }}</strong> ya existe
                  <template v-if="variantInfo.variant_count > 1">
                    con {{ variantInfo.variant_count }} variantes</template>.
                  ¿Querés crear una variante?
                  <span class="block text-xs text-muted-foreground">
                    Se guardará como <code>{{ variantInfo.next_sku }}</code>, con ficha propia.
                  </span>
                </span>
              </p>
              <div class="flex shrink-0 items-center gap-2">
                <!-- Salida explícita: mientras está bloqueado, editar el código
                     también sirve, pero un botón lo hace evidente. -->
                <Button type="button" variant="ghost" size="sm" @click="cancelVariant()">
                  Descartar
                </Button>
                <Button type="button" size="sm" @click="startVariant()">
                  Crear variante
                </Button>
              </div>
            </div>

            <!-- Modo variante activo: se dice qué se está creando y cómo salir. -->
            <div
              v-if="isVariantMode && variantInfo"
              class="md:col-span-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-primary/40 bg-primary/10 px-4 py-3"
            >
              <p class="text-sm">
                Creando la <strong>variante {{ variantInfo.variant_count + 1 }}</strong>
                de <strong>{{ variantInfo.base_sku }}</strong> — código
                <code>{{ variantInfo.next_sku }}</code>.
                <span class="block text-xs text-muted-foreground">
                  Los datos vienen de la pieza original; cambiá lo que difiera.
                </span>
              </p>
              <Button type="button" variant="ghost" size="sm" @click="cancelVariant()">
                Cancelar variante
              </Button>
            </div>

            <FormField v-slot="{ componentField }" name="brand">
              <FormItem>
                <FormLabel>Marca</FormLabel>
                <Select :disabled="isGated" v-bind="componentField">
                  <FormControl>
                    <SelectTrigger class="w-full">
                      <SelectValue placeholder="Selecciona una marca" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem v-for="brand in brandOptions" :key="brand" :value="brand">
                      {{ brand }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="category_id">
              <FormItem>
                <FormLabel>Categoría</FormLabel>
                <Select :disabled="isGated" v-bind="componentField">
                  <FormControl>
                    <SelectTrigger class="w-full">
                      <SelectValue placeholder="Selecciona una categoría" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem
                      v-for="category in store.categories"
                      :key="category.id"
                      :value="category.id"
                    >
                      {{ category.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="provider_id">
              <FormItem>
                <FormLabel>Proveedor</FormLabel>
                <Select :disabled="isGated" v-bind="componentField">
                  <FormControl>
                    <SelectTrigger class="w-full">
                      <SelectValue placeholder="Selecciona un proveedor" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem
                      v-for="provider in store.providers"
                      :key="provider.id"
                      :value="provider.id"
                    >
                      {{ provider.title }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="title">
              <FormItem class="md:col-span-2">
                <FormLabel>Nombre</FormLabel>
                <FormControl>
                  <Input placeholder="Ingrese nombre de Referencia" :disabled="isGated" v-bind="componentField" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="description">
              <FormItem class="md:col-span-2">
                <FormLabel>Descripción</FormLabel>
                <FormControl>
                  <Textarea :disabled="isGated" v-bind="componentField" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="provider_price">
              <FormItem>
                <FormLabel>Precio proveedor (sin IVA)</FormLabel>
                <div class="relative">
                  <IconCurrencyDollar class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <FormControl>
                    <NumericMaskInput class="pl-8" :disabled="isGated" v-bind="componentField" />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            </FormField>

            <div class="grid gap-2">
              &nbsp;
            </div>

            <FormField v-slot="{ componentField }" name="base_price">
              <FormItem>
                <FormLabel>Precio base</FormLabel>
                <div class="relative">
                  <IconCurrencyDollar class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <FormControl>
                    <NumericMaskInput class="pl-8" :disabled="isGated" v-bind="componentField" />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="iva_percentage">
              <FormItem>
                <FormLabel>IVA</FormLabel>
                <div class="relative">
                  <IconPercentage class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <FormControl>
                    <NumericMaskInput :max="100" class="pl-8" :disabled="isGated" v-bind="componentField" />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            </FormField>

            <!-- `ImageDropCropper` no tiene prop `disabled` (es un div con @click y
                 @drop, no un control nativo): se apaga el contenedor, que
                 corta tambien el arrastrar-soltar. -->
            <div
              class="grid min-w-0 gap-2 md:col-span-2 mt-4"
              :class="isGated ? 'pointer-events-none opacity-50' : ''"
            >
              <label class="text-sm font-medium leading-none">Imagen Producto</label>
              <ImageDropCropper v-model="croppedImage" :initial-preview-url="existingImageUrl" />
            </div>

            <FormField v-slot="{ componentField }" name="image_url">
              <FormItem class="md:col-span-2">
                <FormLabel>O pegar URL de imagen externa</FormLabel>
                <FormControl>
                  <Input placeholder="https://..." :disabled="isGated" v-bind="componentField" />
                </FormControl>
                <p class="flex items-start gap-1.5 text-xs text-muted-foreground">
                  <IconAlertTriangle class="mt-0.5 size-3.5 shrink-0" />
                  Se carga desde ese sitio cada vez que se muestra la referencia — si el
                  sitio la cambia, la elimina, o trabajás sin internet, la imagen no va a
                  aparecer.
                </p>
                <FormMessage />
              </FormItem>
            </FormField>

            <div class="flex justify-end md:col-span-2">
              <Button type="submit" :disabled="isSubmitting || isGated">
                {{ isSubmitting
                  ? (isEditMode ? "Guardando..." : "Creando...")
                  : (isEditMode ? "Guardar cambios" : "Crear referencia") }}
              </Button>
            </div>
          </form>
        </div>

        <!--Vista Previa-->
        <div class="referencePreview flex w-sm flex-col space-y-8 rounded-lg border border-border p-4 lg:p-6">
          <p class="text-gray-600">
            Vista previa
          </p>

          <div class="h-44 w-44 bg-gray-100">
            <figure v-if="imagePreviewUrl || existingImageUrl">
              <img :src="imagePreviewUrl ?? existingImageUrl ?? undefined" alt="" class="h-full w-full object-cover">
            </figure>
          </div>

          <div class="flex-1 space-y-1">
            <p class="text-lg font-bold uppercase">
              SKU: {{ values.sku || "—" }}
            </p>
            <p class="text-sm">
              {{ values.brand || "—" }}
            </p>
            <p class="mb-2 text-base font-bold uppercase">
              {{ values.title || "—" }}
            </p>
            <Badge variant="secondary">
              <span class="font-mono">{{ store.categoryName(values.category_id ?? null) }}</span>
            </Badge>
          </div>

          <div class="space-y-2 border-t border-t-gray-200 border-b border-b-gray-100 py-4">
            <div class="flex">
              <span class="flex-1 text-gray-600">
                Precio Proveedor:
              </span>

              <span class="font-bold tabular-nums">
                {{ providerPriceDisplay }}
              </span>
            </div>
            <div class="flex">
              <span class="flex-1 text-gray-600">
                Precio Base:
              </span>

              <span class="font-bold tabular-nums">
                {{ basePriceDisplay }}
              </span>
            </div>
            <div class="flex">
              <span class="flex-1 text-gray-600">
                IVA ({{ ivaPercentageDecimal.toFixed(0) }}%):
              </span>

              <span class="font-bold tabular-nums">
                {{ ivaAmountDisplay }}
              </span>
            </div>
          </div>

          <div class="flex items-center">
            <span class="flex-1 text-lg font-bold">
              Precio de Venta:
            </span>

            <span class="rounded-full bg-accent px-3 py-1 text-lg font-bold text-accent-foreground tabular-nums">
              {{ salePriceDisplay }}
            </span>
          </div>
        </div>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
