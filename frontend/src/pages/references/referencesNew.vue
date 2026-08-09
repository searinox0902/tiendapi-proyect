<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import { toTypedSchema } from "@vee-validate/zod"
import { useForm } from "vee-validate"
import { toast } from "vue-sonner"
import { IconCurrencyDollar, IconPercentage } from "@tabler/icons-vue"

import AppSidebar from "@/components/AppSidebar.vue"
import ImageDropCropper from "@/components/ImageDropCropper.vue"
import NumericMaskInput from "@/components/NumericMaskInput.vue"
import { useAnimatedCurrency } from "@/composables/useAnimatedCurrency"
import { toDecimal } from "@/lib/money"
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
import { Textarea } from "@/components/ui/textarea"
import { buildReferenceFormSchema } from "@/api/references/references.schema"
import { referencesApi } from "@/api/references/references.api"
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

const { values, handleSubmit, resetForm, isSubmitting } = useForm({
  validationSchema: computed(() => toTypedSchema(buildReferenceFormSchema(props.sku))),
  initialValues: {
    sku: "",
    provider_id: undefined,
    brand: undefined,
    category_id: undefined,
    title: "",
    description: "",
    precio_proveedor: undefined,
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
            precio_proveedor: data.precio_proveedor !== null ? Number(data.precio_proveedor) : undefined,
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
async function uploadPendingImage(sku: string): Promise<string | null> {
  if (!croppedImage.value) {
    return null
  }
  try {
    const { data } = await referencesApi.uploadImage(sku, croppedImage.value)
    return `${import.meta.env.VITE_API_URL}${data.url}`
  } catch {
    toast.error("La referencia se creó, pero no se pudo guardar la imagen", { position: "bottom-center" })
    return null
  }
}

const onSubmit = handleSubmit(
  async (formValues) => {
    try {
      const payload = {
        provider_id: formValues.provider_id,
        category_id: formValues.category_id ?? null,
        sku: formValues.sku,
        title: formValues.title,
        brand: formValues.brand ?? null,
        description: formValues.description ?? null,
        image_url: existingImageUrl.value,
        base_price: formValues.base_price,
        iva_percentage: formValues.iva_percentage,
        precio_proveedor: formValues.precio_proveedor,
      }

      let referenceId: string
      if (isEditMode.value && editingId.value) {
        const { data } = await referencesApi.updateReference(editingId.value, payload)
        referenceId = data.id
      } else {
        // La imagen se sube DESPUÉS de crear la referencia, no antes ni junto: si
        // la creación falla, nunca se sube nada (ver comentario de `uploadPendingImage`).
        const { data } = await referencesApi.createReference(payload)
        referenceId = data.id
      }

      // `uploadImage` solo guarda el archivo (D-58); la URL resultante hay que
      // persistirla aparte en `image_url` con un segundo PUT, o la Referencia
      // se queda sin imagen aunque el archivo sí se haya subido.
      const uploadedImageUrl = await uploadPendingImage(formValues.sku)
      if (uploadedImageUrl) {
        await referencesApi.updateReference(referenceId, { ...payload, image_url: uploadedImageUrl })
      }

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

const precioProveedorDecimal = computed(() => toDecimal(values.precio_proveedor))
const basePriceDecimal = computed(() => toDecimal(values.base_price))
const ivaPercentageDecimal = computed(() => toDecimal(values.iva_percentage))
const ivaAmountDecimal = computed(() => basePriceDecimal.value.times(ivaPercentageDecimal.value).dividedBy(100))
/** Precio de venta (`sale_price`, D-45): derivado de precio base + IVA, nunca capturado a mano. */
const salePriceDecimal = computed(() => basePriceDecimal.value.plus(ivaAmountDecimal.value))

/** Animación de cálculos del MVP (D-54): los totales "corren" entre el valor anterior y el nuevo. */
const precioProveedorDisplay = useAnimatedCurrency(precioProveedorDecimal)
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
          <h1 class="text-base font-medium">
            {{ isEditMode ? "Editar referencia" : "Registrar referencia" }}
          </h1>
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
                  <Input placeholder="Ingrese SKU" :disabled="isEditMode" v-bind="componentField" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="brand">
              <FormItem>
                <FormLabel>Marca</FormLabel>
                <Select v-bind="componentField">
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
                <Select v-bind="componentField">
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
                <Select v-bind="componentField">
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
                  <Input placeholder="Ingrese nombre de Referencia" v-bind="componentField" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="description">
              <FormItem class="md:col-span-2">
                <FormLabel>Descripción</FormLabel>
                <FormControl>
                  <Textarea v-bind="componentField" />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="precio_proveedor">
              <FormItem>
                <FormLabel>Precio proveedor</FormLabel>
                <div class="relative">
                  <IconCurrencyDollar class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <FormControl>
                    <NumericMaskInput class="pl-8" v-bind="componentField" />
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
                    <NumericMaskInput class="pl-8" v-bind="componentField" />
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
                    <NumericMaskInput :max="100" class="pl-8" v-bind="componentField" />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            </FormField>

            <div class="grid min-w-0 gap-2 md:col-span-2 mt-4">
              <label class="text-sm font-medium leading-none">Imagen Producto</label>
              <ImageDropCropper v-model="croppedImage" :initial-preview-url="existingImageUrl" />
            </div>

            <div class="flex justify-end md:col-span-2">
              <Button type="submit" :disabled="isSubmitting">
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
                {{ precioProveedorDisplay }}
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

            <span class="rounded-full bg-purple-100 px-3 py-1 text-lg font-bold text-purple-700 tabular-nums">
              {{ salePriceDisplay }}
            </span>
          </div>
        </div>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
