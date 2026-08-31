<script setup lang="ts">
import { computed, ref } from "vue"
import { IconAlertTriangle, IconFile } from "@tabler/icons-vue"
import axios from "axios"
import { toast } from "vue-sonner"
import { Badge } from "@/components/ui/badge"
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
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { itemsApi } from "@/api/items/items.api"
import type { IProductImportPreview } from "@/api/items/items.types"

/**
 * Importación de Productos/existencias (A-30) — hermana de
 * `references/ImportCatalogDialog.vue`, con una diferencia que manda sobre
 * toda la pantalla: acá **una fila del archivo no es un producto, son N
 * unidades**. Por eso el titular cuenta existencias y no filas.
 *
 * Lo que esta pantalla tiene que dejar ver antes de confirmar:
 *
 * 1. **Las variantes que se van a crear.** Con el mismo SKU y otro nombre, el
 *    backend crea una Referencia variante (`#2`) sin preguntar — decisión del
 *    dueño de producto. Automático no puede significar invisible: se listan
 *    con el código que van a recibir, porque un archivo que escribe el mismo
 *    producto con dos nombres distintos crearía dos fichas.
 * 2. **Las discrepancias.** El archivo NUNCA edita el catálogo: si una fila
 *    trae otra marca o otro precio para un SKU que ya existe, se ignora. Hay
 *    que decirlo, o el usuario cree que actualizó algo que no cambió.
 *
 * Igual que en Referencias, el cliente no parsea el archivo: lo sube tal cual
 * y el backend detecta JSON vs. .xlsx (D-29/D-31 — nada de librerías de Excel
 * en el bundle de Tauri).
 */
const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{ imported: [] }>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const fileName = ref("")
const selectedFile = ref<File | null>(null)
const preview = ref<IProductImportPreview | null>(null)
const isPreviewing = ref(false)
const isImporting = ref(false)
/**
 * Arranca en `true` (A-30): un SKU que no está en el catálogo se crea junto
 * con sus existencias, que es lo que permite cargar el inventario inicial de
 * un negocio en una sola pasada. El interruptor está para poder apagarlo, no
 * porque haya que prenderlo.
 */
const createMissing = ref(true)
const errorMessage = ref("")

function pickFile(accept?: string) {
  if (fileInputRef.value && accept) {
    fileInputRef.value.accept = accept
  }
  fileInputRef.value?.click()
}

defineExpose({ pickFile })

/** Solo para el subtítulo bajo el nombre — la validación real la hace el backend. */
const fileTypeLabel = computed(() =>
  fileName.value.toLowerCase().endsWith(".xlsx") ? "Excel" : "JSON",
)

const newReferencesCount = computed(() => preview.value?.new_references.length ?? 0)
const newVariantsCount = computed(() => preview.value?.new_variants.length ?? 0)

async function runPreview() {
  if (!selectedFile.value) {
    return
  }
  isPreviewing.value = true
  errorMessage.value = ""
  try {
    const { data } = await itemsApi.previewProductImport(selectedFile.value, createMissing.value)
    preview.value = data
  } catch (error) {
    console.error("Preview product import failed:", error)
    preview.value = null
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
    errorMessage.value = typeof detail === "string" ? detail : "No se pudo leer el archivo"
  } finally {
    isPreviewing.value = false
  }
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  //  Se limpia ya mismo: sin esto, elegir el MISMO archivo dos veces seguidas
  //  no dispara `change` la segunda vez.
  input.value = ""
  if (!file) {
    return
  }

  selectedFile.value = file
  preview.value = null
  errorMessage.value = ""
  createMissing.value = true
  fileName.value = file.name
  open.value = true
  await runPreview()
}

/**
 * Cambiar el interruptor **vuelve a previsualizar** en vez de recalcular en el
 * cliente: `create_missing` no mueve un contador, cambia el plan entero (las
 * filas de SKU nuevo pasan de crear producto a ser inválidas). Estimarlo acá
 * sería fabricar un número que el servidor no prometió.
 */
async function onCreateMissingChange() {
  if (selectedFile.value && !isPreviewing.value) {
    await runPreview()
  }
}

async function confirmImport() {
  if (!selectedFile.value || isImporting.value || !preview.value?.units_total) {
    return
  }
  isImporting.value = true
  try {
    const { data } = await itemsApi.importProducts(selectedFile.value, createMissing.value)
    open.value = false
    emit("imported")

    const summary = [`${data.units_created} existencias`]
    if (data.references_created > 0) {
      summary.push(`${data.references_created} productos nuevos`)
    }
    if (data.variants_created > 0) {
      summary.push(`${data.variants_created} variantes`)
    }
    if (data.invalid > 0) {
      summary.push(`${data.invalid} inválidas`)
    }

    const batchId = data.batch_id
    toast.success(summary.join(" · "), {
      position: "bottom-center",
      //  El deshacer importa más acá que en Referencias: un archivo de 500
      //  filas puede crear miles de unidades, y borrarlas a mano una por una
      //  no es una opción real.
      action: batchId ? { label: "Deshacer", onClick: () => undoImport(batchId) } : undefined,
    })
  } catch (error) {
    console.error("Import products failed:", error)
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
    toast.error(
      typeof detail === "string" ? detail : "No se pudieron importar las existencias",
      { position: "bottom-center" },
    )
  } finally {
    isImporting.value = false
  }
}

async function undoImport(batchId: string) {
  try {
    const { data } = await itemsApi.undoProductImportBatch(batchId)
    emit("imported")
    toast.success(`Importación deshecha · ${data.units_deleted} existencias`, {
      position: "bottom-center",
    })
  } catch (error) {
    console.error("Undo product import failed:", error)
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
    toast.error(
      typeof detail === "string" ? detail : "No se pudo deshacer la importación",
      { position: "bottom-center" },
    )
  }
}
</script>

<template>
  <input
    ref="fileInputRef"
    type="file"
    accept="application/json,.json,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    class="hidden"
    @change="onFileChange"
  >

  <Dialog v-model:open="open">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Importar existencias</DialogTitle>
        <DialogDescription>
          Acepta JSON o el Excel exportado por el sistema. Suma unidades al
          inventario; nunca modifica los productos que ya existen.
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-4">
        <!-- Identidad del archivo: ícono + nombre, siempre visible una vez elegido. -->
        <div class="flex items-center gap-3 rounded-lg border border-border p-3">
          <div class="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
            <IconFile class="size-5 text-brand-icon" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium" :title="fileName">
              {{ fileName }}
            </p>
            <p class="text-xs text-muted-foreground">
              {{ fileTypeLabel }}
            </p>
          </div>
        </div>

        <div v-if="isPreviewing" class="flex flex-col items-center gap-3 py-6">
          <Spinner class="size-6 text-brand-icon" />
          <p class="text-sm text-muted-foreground">
            Analizando archivo…
          </p>
        </div>

        <p v-else-if="errorMessage" class="flex items-start gap-2 text-sm text-destructive">
          <IconAlertTriangle class="mt-0.5 size-4 shrink-0" />
          {{ errorMessage }}
        </p>

        <div v-else-if="preview" class="grid gap-4">
          <!-- El titular cuenta UNIDADES, no filas: es lo que el archivo agrega
               al inventario, y una sola fila puede traer 20 (D-41). -->
          <div class="rounded-lg bg-primary/10 px-4 py-3 text-center">
            <p class="text-3xl font-bold tabular-nums text-brand-icon">
              +{{ preview.units_total }}
            </p>
            <p class="text-sm text-muted-foreground">
              {{ preview.units_total === 1 ? "existencia" : "existencias" }}
            </p>
          </div>

          <div
            v-if="newReferencesCount > 0 || newVariantsCount > 0 || preview.invalid.length > 0"
            class="grid grid-cols-3 gap-3 text-center"
          >
            <div v-if="newReferencesCount > 0">
              <p class="text-lg font-semibold tabular-nums">
                {{ newReferencesCount }}
              </p>
              <p class="text-xs text-muted-foreground">
                Productos nuevos
              </p>
            </div>
            <div v-if="newVariantsCount > 0">
              <p class="text-lg font-semibold tabular-nums">
                {{ newVariantsCount }}
              </p>
              <p class="text-xs text-muted-foreground">
                Variantes
              </p>
            </div>
            <div v-if="preview.invalid.length > 0">
              <p class="text-lg font-semibold tabular-nums text-destructive">
                {{ preview.invalid.length }}
              </p>
              <p class="text-xs text-muted-foreground">
                Inválidas
              </p>
            </div>
          </div>

          <!--
            Variantes: el archivo trae el mismo código con otro nombre, así que
            son piezas distintas que comparten código de proveedor. Se crean
            solas, pero se muestran una por una con el código que van a recibir
            — es la única forma de notar a tiempo que el archivo escribió dos
            veces el mismo producto con nombres levemente distintos.
          -->
          <div v-if="newVariantsCount > 0" class="grid gap-2 rounded-md border border-border p-3">
            <p class="text-sm font-medium">
              Mismo código, otro nombre
            </p>
            <p class="text-xs text-muted-foreground">
              Se crean como variantes del producto que ya existe, con código propio.
            </p>
            <div
              v-for="variant in preview.new_variants.slice(0, 6)"
              :key="variant.sku"
              class="flex items-center justify-between gap-2 text-xs"
            >
              <span class="min-w-0 truncate" :title="variant.title">{{ variant.title }}</span>
              <Badge variant="outline" class="shrink-0 font-mono">{{ variant.sku }}</Badge>
            </div>
            <p v-if="newVariantsCount > 6" class="text-xs text-muted-foreground">
              y {{ newVariantsCount - 6 }} más…
            </p>
          </div>

          <!--
            Discrepancias: el archivo dice otra cosa que el catálogo y NO se
            aplica. Sin este aviso, el usuario cree que corrigió un precio y en
            realidad solo agregó unidades.
          -->
          <div
            v-if="preview.discrepancies.length > 0"
            class="grid gap-1.5 rounded-md bg-muted px-3 py-2 text-xs"
          >
            <p class="font-medium">
              El archivo difiere del catálogo en {{ preview.discrepancies.length }}
              {{ preview.discrepancies.length === 1 ? "producto" : "productos" }}
            </p>
            <p class="text-muted-foreground">
              No se cambia nada: manda el producto ya registrado. Corregilo desde
              Referencias si el archivo tiene razón.
            </p>
            <p
              v-for="discrepancy in preview.discrepancies.slice(0, 4)"
              :key="discrepancy.sku"
              class="text-muted-foreground"
            >
              <span class="font-mono">{{ discrepancy.sku }}</span>: {{ discrepancy.fields.join(", ") }}
            </p>
            <p v-if="preview.discrepancies.length > 4" class="text-muted-foreground">
              y {{ preview.discrepancies.length - 4 }} más…
            </p>
          </div>

          <!-- La decisión es del usuario, no un default silencioso. -->
          <div class="flex items-center justify-between gap-4 rounded-md bg-muted px-3 py-2">
            <div class="grid gap-0.5">
              <Label for="create-missing" class="text-sm">Crear los productos que falten</Label>
              <p class="text-xs text-muted-foreground">
                Si lo apagas, las filas cuyo código no esté en el catálogo quedan
                sin importar.
              </p>
            </div>
            <Switch
              id="create-missing"
              v-model="createMissing"
              :disabled="isPreviewing"
              @update:model-value="onCreateMissingChange"
            />
          </div>

          <p
            v-if="preview.columns_missing && preview.columns_missing.length > 0"
            class="flex items-start gap-2 text-xs text-muted-foreground"
          >
            <IconAlertTriangle class="mt-0.5 size-3.5 shrink-0" />
            No se encontró columna para: {{ preview.columns_missing.join(", ") }} — esas
            filas siguen el precio del catálogo.
          </p>

          <p
            v-if="preview.columns_ignored && preview.columns_ignored.length > 0"
            class="flex items-start gap-2 text-xs text-muted-foreground"
          >
            <IconAlertTriangle class="mt-0.5 size-3.5 shrink-0" />
            Columnas que no se reconocen y se ignoran:
            {{ preview.columns_ignored.join(", ") }}.
          </p>

          <div
            v-if="preview.new_providers.length > 0 || preview.new_locations.length > 0 || preview.new_categories.length > 0"
            class="grid gap-1.5 text-sm"
          >
            <p v-if="preview.new_providers.length > 0" class="text-muted-foreground">
              Proveedores nuevos:
              <span v-for="name in preview.new_providers" :key="name" class="inline-block">
                <Badge variant="outline" class="ml-1">{{ name }}</Badge>
              </span>
            </p>
            <p v-if="preview.new_locations.length > 0" class="text-muted-foreground">
              Ubicaciones nuevas:
              <span v-for="name in preview.new_locations" :key="name" class="inline-block">
                <Badge variant="outline" class="ml-1">{{ name }}</Badge>
              </span>
            </p>
            <p v-if="preview.new_categories.length > 0" class="text-muted-foreground">
              Categorías nuevas:
              <span v-for="name in preview.new_categories" :key="name" class="inline-block">
                <Badge variant="outline" class="ml-1">{{ name }}</Badge>
              </span>
            </p>
          </div>

          <div v-if="preview.invalid.length > 0" class="grid gap-1 text-xs text-muted-foreground">
            <p v-for="row in preview.invalid.slice(0, 5)" :key="row.index">
              Fila {{ row.index + 1 }}{{ row.sku ? ` (${row.sku})` : "" }}: {{ row.reason }}
            </p>
            <p v-if="preview.invalid.length > 5">
              y {{ preview.invalid.length - 5 }} más…
            </p>
          </div>
        </div>
      </div>

      <DialogFooter v-if="preview">
        <Button
          :disabled="preview.units_total === 0 || isImporting || isPreviewing"
          class="gap-1.5"
          @click="confirmImport"
        >
          <Spinner v-if="isImporting" class="size-4" />
          {{ isImporting ? "Importando…" : `Agregar ${preview.units_total} existencias` }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
