<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue"
import { Cropper } from "vue-advanced-cropper"
import "vue-advanced-cropper/dist/style.css"
import { IconUpload } from "@tabler/icons-vue"
import { Button } from "@/components/ui/button"
import { resizeSquareTo, resizeToFit } from "@/lib/image"

/**
 * Input de imagen reutilizable: dropzone ("Arrastra o adjunta imagen") → recorte
 * (`vue-advanced-cropper`, D-50) → confirmación. Emite el Blob ya recortado por
 * `update:modelValue`; quien lo use decide qué hacer con él (armar un object URL
 * para una vista previa, subirlo al backend, etc.). Pensado para reusarse en
 * cualquier pantalla que capture una imagen (Referencias, Productos, …).
 *
 * Toda imagen se redimensiona dos veces:
 * 1) Al cargarla, se topa a `MAX_SOURCE_DIMENSION` (preservando aspect ratio)
 *    — evita que una foto de cámara/celular (3000px+) desborde el recortador
 *    (su `<img>` interna se renderiza a tamaño intrínseco) y aligera el trabajo
 *    del navegador al decodificarla/manipularla.
 * 2) Al confirmar el recorte (ya cuadrado por el aspect ratio 1:1), se reduce a
 *    `outputSize` fijo — así toda imagen de la plataforma queda homologada al
 *    mismo tamaño/peso, sin importar la resolución original que subió el usuario.
 */
const MAX_SOURCE_DIMENSION = 1600

const props = withDefaults(defineProps<{
  modelValue?: Blob | null
  /** Aspect ratio del recorte. 1:1 por defecto (D-50). */
  aspectRatio?: number
  /** Lado (px) del cuadrado de salida ya recortado. */
  outputSize?: number
  /** Imagen ya persistida (ej. al editar una Referencia existente) — se muestra en el dropzone mientras no se recorte una nueva. */
  initialPreviewUrl?: string | null
}>(), {
  aspectRatio: 1,
  outputSize: 500,
  initialPreviewUrl: null,
})

const emit = defineEmits<{
  (e: "update:modelValue", value: Blob | null): void
}>()

type Mode = "idle" | "cropping"
const mode = ref<Mode>("idle")
const isDragging = ref(false)

const fileInputRef = ref<HTMLInputElement>()
const cropperRef = ref<InstanceType<typeof Cropper>>()

/** Imagen ya redimensionada a MAX_SOURCE_DIMENSION, antes de recortar. */
const sourceImageUrl = ref<string | null>(null)
/** Miniatura del último recorte confirmado, para mostrar en el propio dropzone. */
const resultUrl = ref<string | null>(null)

function openFileDialog() {
  fileInputRef.value?.click()
}

async function loadFile(file: File | undefined) {
  if (!file) {
    return
  }
  const resized = await resizeToFit(file, MAX_SOURCE_DIMENSION)
  if (sourceImageUrl.value) {
    URL.revokeObjectURL(sourceImageUrl.value)
  }
  sourceImageUrl.value = URL.createObjectURL(resized)
  mode.value = "cropping"
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  void loadFile(input.files?.[0])
  input.value = ""
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  void loadFile(event.dataTransfer?.files?.[0])
}

function cancelCrop() {
  if (sourceImageUrl.value) {
    URL.revokeObjectURL(sourceImageUrl.value)
  }
  sourceImageUrl.value = null
  mode.value = "idle"
}

async function confirmCrop() {
  const canvas = cropperRef.value?.getResult().canvas
  if (!canvas) {
    return
  }
  const blob = await resizeSquareTo(canvas, props.outputSize)
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
  }
  resultUrl.value = URL.createObjectURL(blob)
  emit("update:modelValue", blob)
  cancelCrop()
}

/** Si quien lo usa limpia el `v-model` desde afuera (ej. tras crear la Referencia), refleja el reset acá también. */
watch(() => props.modelValue, (value) => {
  if (value === null && resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = null
  }
})

onBeforeUnmount(() => {
  if (sourceImageUrl.value) {
    URL.revokeObjectURL(sourceImageUrl.value)
  }
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
  }
})
</script>

<template>
  <div class="min-w-0">
    <div
      v-if="mode === 'idle'"
      class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed p-6 text-center transition-colors"
      :class="isDragging ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/50'"
      @click="openFileDialog"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <template v-if="resultUrl">
        <img :src="resultUrl" alt="" class="size-24 rounded-md object-cover">
        <span class="text-sm text-primary underline">Cambiar imagen</span>
      </template>
      <template v-else-if="initialPreviewUrl">
        <img :src="initialPreviewUrl" alt="" class="size-24 rounded-md object-cover">
        <span class="text-sm text-primary underline">Cambiar imagen</span>
      </template>
      <template v-else>
        <IconUpload class="size-6 text-muted-foreground" />
        <p class="text-sm text-muted-foreground">
          Arrastra o adjunta una imagen
        </p>
      </template>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        class="hidden"
        @change="onFileSelected"
      >
    </div>

    <div v-else class="flex min-w-0 flex-col gap-3">
      <Cropper
        ref="cropperRef"
        class="h-64 w-full min-w-0 rounded-md bg-muted"
        :src="sourceImageUrl ?? undefined"
        :stencil-props="{ aspectRatio: props.aspectRatio }"
      />
      <div class="flex justify-end gap-2">
        <Button type="button" variant="outline" size="sm" @click="cancelCrop">
          Cancelar
        </Button>
        <Button type="button" size="sm" @click="confirmCrop">
          Confirmar recorte
        </Button>
      </div>
    </div>
  </div>
</template>
