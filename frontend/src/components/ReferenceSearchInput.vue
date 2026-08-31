<script setup lang="ts">
import { ref, watch } from "vue"
import { watchDebounced } from "@vueuse/core"
import { IconPackage } from "@tabler/icons-vue"

import { Input } from "@/components/ui/input"
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import { referencesApi } from "@/api/references/references.api"
import type { IReference } from "@/api/references/references.types"

/**
 * Campo único que busca una Referencia por **código o nombre** — el `search`
 * del backend cruza los dos con OR, así que reemplaza al par de campos
 * "SKU" + "Nombre" en cualquier pantalla que necesite señalar una pieza del
 * catálogo (D-91).
 *
 * Es el mismo patrón que `pages/pos/CustomerAutocomplete.vue` usa para
 * clientes: **`Popover` + `Input` + lista propia**, con la búsqueda del
 * servidor, debounce y navegación por teclado llevada a mano.
 *
 * **Por qué NO usa `Command`** (pedido explícitamente y descartado con motivo):
 * `CommandInput` filtra en el cliente sobre los items ya montados. Con miles de
 * Referencias que viven en el servidor y llegan paginadas, filtrar sobre la
 * página en memoria devolvería "sin resultados" para casi todo el catálogo. El
 * `Command` de shadcn sirve para paletas de comandos y listas cerradas, no para
 * un catálogo remoto.
 *
 * **Al enfocar muestra resultados aunque no haya nada escrito.** No es un
 * adorno: es lo que le enseña al usuario que el campo busca contra lo que ya
 * existe, en vez de que lo descubra por accidente al tercer carácter.
 *
 * Emite `select` con la Referencia **entera**, no solo el texto: quien lo usa
 * decide qué hacer con ella — el alta de Referencia la usa para ofrecer crear
 * una variante (D-90) y precargar la ficha.
 */
const props = defineProps<{
  modelValue: string
  /** Para asociar un `<Label for>` — sin esto la etiqueta queda huérfana. */
  id?: string
  disabled?: boolean
  placeholder?: string
  /** Encabezado de la lista cuando hay término escrito. */
  hint?: string
  /** Encabezado cuando el campo está vacío — el gancho que explica el campo. */
  emptyHint?: string
  /** Cuántas sugerencias traer. 6 entra sin scroll en el popover. */
  limit?: number
}>()

const emit = defineEmits<{
  "update:modelValue": [value: string]
  select: [reference: IReference]
  /** Se pierde el foco: quien lo usa aprovecha para normalizar o validar. */
  blur: []
}>()

const open = ref(false)
const results = ref<IReference[]>([])
const highlightedIndex = ref(-1)
/** Se apaga al rellenar desde afuera, para que elegir una sugerencia no dispare otra búsqueda. */
const isSuppressed = ref(false)

/**
 * `allowEmpty` solo lo activa el foco. Al tecleo NO se le permite: cuando un
 * formulario se resetea el valor vuelve a `""`, y sin esta distinción el
 * watcher abriría el popover solo, encima del formulario recién limpiado.
 */
async function runSearch(allowEmpty = false) {
  if (isSuppressed.value || props.disabled) {
    return
  }
  const term = props.modelValue.trim()
  if (!term && !allowEmpty) {
    results.value = []
    open.value = false
    return
  }
  const limit = props.limit ?? 6
  try {
    //  Sin término se omite `search` y el backend devuelve la primera página.
    const { data } = await referencesApi.getReferences(
      term ? { search: term, limit } : { limit },
    )
    results.value = data.items
    highlightedIndex.value = data.items.length > 0 ? 0 : -1
    //  Sin coincidencias no se abre un popover vacío: que no exista es un caso
    //  normal, y un cartel de "sin resultados" sería ruido.
    open.value = data.items.length > 0
  } catch {
    results.value = []
    open.value = false
  }
}

//  Envuelto en una arrow a propósito: `watchDebounced` pasa el valor nuevo como
//  primer argumento, y ese string llegaría como `allowEmpty` (truthy).
watchDebounced(() => props.modelValue, () => runSearch(), { debounce: 250 })

async function onFocus() {
  if (props.disabled || open.value) {
    return
  }
  await runSearch(true)
}

function choose(reference: IReference) {
  isSuppressed.value = true
  emit("update:modelValue", reference.sku)
  emit("select", reference)
  open.value = false
  setTimeout(() => { isSuppressed.value = false }, 0)
}

watch(() => props.modelValue, () => {
  if (isSuppressed.value) {
    open.value = false
  }
})

function onArrowDown() {
  if (!open.value || results.value.length === 0) return
  highlightedIndex.value = Math.min(highlightedIndex.value + 1, results.value.length - 1)
}

function onArrowUp() {
  if (!open.value || results.value.length === 0) return
  highlightedIndex.value = Math.max(highlightedIndex.value - 1, 0)
}

function onEnter() {
  if (!open.value) return
  const reference = results.value[highlightedIndex.value]
  if (reference !== undefined) {
    choose(reference)
  }
}
</script>

<template>
  <Popover v-model:open="open">
    <PopoverAnchor as-child>
      <Input
        :id="id"
        :model-value="modelValue"
        :disabled="disabled"
        :placeholder="placeholder ?? 'Código o nombre'"
        autocomplete="off"
        @update:model-value="value => emit('update:modelValue', String(value))"
        @focus="onFocus()"
        @blur="emit('blur')"
        @keydown.down.prevent="onArrowDown"
        @keydown.up.prevent="onArrowUp"
        @keydown.enter.prevent="onEnter"
        @keydown.escape="open = false"
      />
    </PopoverAnchor>

    <!-- El foco se queda en el input: hay que poder seguir escribiendo con el popover abierto. -->
    <PopoverContent
      class="w-[--reka-popover-trigger-width] min-w-80 p-1"
      align="start"
      @open-auto-focus.prevent
      @close-auto-focus.prevent
    >
      <p v-if="hint || emptyHint" class="px-2 py-1 text-xs text-muted-foreground">
        {{ modelValue.trim() ? hint : (emptyHint ?? hint) }}
      </p>
      <button
        v-for="(reference, index) in results"
        :key="reference.id"
        type="button"
        class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors"
        :class="index === highlightedIndex ? 'bg-accent text-accent-foreground' : ''"
        @click="choose(reference)"
        @mouseenter="highlightedIndex = index"
      >
        <IconPackage class="size-4 shrink-0 text-muted-foreground" />
        <span class="min-w-0 flex-1 truncate">
          {{ reference.title }}
          <span v-if="reference.brand" class="text-xs text-muted-foreground">· {{ reference.brand }}</span>
        </span>
        <span class="shrink-0 font-mono text-xs text-muted-foreground">{{ reference.sku }}</span>
      </button>
    </PopoverContent>
  </Popover>
</template>
