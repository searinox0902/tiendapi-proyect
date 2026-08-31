<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { IconPhotoUp, IconTrash, IconUpload } from "@tabler/icons-vue"
import axios from "axios"
import { toast } from "vue-sonner"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { brandingApi } from "@/api/branding/branding.api"
import { rememberLoginImage } from "@/lib/branding"
import { resizeToFit } from "@/lib/image"

/**
 * Imagen del negocio — la que se ve en la pantalla de inicio de sesión.
 *
 * **No usa `ImageDropCropper` a propósito.** Ese componente recorta a un
 * cuadrado de 500 px (`resizeSquareTo`), que es lo correcto para la foto de un
 * producto en una grilla y lo contrario de lo que hace falta acá: esta imagen
 * se pinta grande y de fondo, así que tiene que conservar su proporción
 * original y una resolución alta. Además el pedido fue un file input, no un
 * flujo de recorte.
 *
 * **Se redimensiona en el navegador y solo si hace falta.** Una foto de
 * celular son 12 MP y varios MB; bajarla a 1920 px de lado largo la deja
 * nítida para un fondo y liviana para subir. Pero si la imagen ya entra en ese
 * tamaño **se sube tal cual**, sin reencodear: `resizeToFit` siempre emite
 * JPEG, y pasar por ahí un PNG con transparencia le pintaría el fondo de
 * negro. No tocar lo que no hace falta tocar es también lo que conserva la
 * calidad original.
 */
const MAX_DIMENSION = 1920
//  Mismo tope que valida el backend (`branding.py:MAX_UPLOAD_BYTES`). Se
//  chequea acá para poder decirlo antes de subir 8 MB y recibir un 413.
const MAX_BYTES = 8 * 1024 * 1024

const fileInputRef = ref<HTMLInputElement | null>(null)
const currentPath = ref<string | null>(null)
const isLoading = ref(true)
const isUploading = ref(false)

/** URL absoluta para la vista previa: la ruta guardada es relativa (D-84). */
const previewUrl = computed(() =>
  currentPath.value ? `${import.meta.env.VITE_API_URL}${currentPath.value}` : null,
)

onMounted(async () => {
  try {
    const { data } = await brandingApi.getBranding()
    currentPath.value = data.login_image_url
    //  Se recuerda también al entrar y no solo al subir: si el negocio cargó
    //  la imagen desde otra máquina, ésta se entera la primera vez que abre
    //  Configuraciones y la próxima pantalla de login ya la muestra.
    rememberLoginImage(data.login_image_url)
  } catch (error) {
    console.error("Load branding failed:", error)
  } finally {
    isLoading.value = false
  }
})

/**
 * Deja el archivo listo para subir: lo redimensiona solo si se pasa de
 * `MAX_DIMENSION`.
 *
 * Cuando reencodea cambia el nombre a `.jpg` — el backend deriva la extensión
 * del **nombre del archivo**, así que mandar bytes JPEG dentro de un
 * `negocio.png` lo guardaría con la extensión equivocada.
 */
async function prepare(file: File): Promise<File> {
  const bitmap = await createImageBitmap(file)
  const longestSide = Math.max(bitmap.width, bitmap.height)
  bitmap.close()

  if (longestSide <= MAX_DIMENSION && file.size <= MAX_BYTES) {
    return file
  }
  const blob = await resizeToFit(file, MAX_DIMENSION)
  return new File([blob], "negocio.jpg", { type: "image/jpeg" })
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

  isUploading.value = true
  try {
    const prepared = await prepare(file)
    if (prepared.size > MAX_BYTES) {
      toast.error("La imagen sigue pesando más de 8 MB después de redimensionarla", {
        position: "bottom-center",
      })
      return
    }
    const { data } = await brandingApi.uploadLoginImage(prepared)
    currentPath.value = data.login_image_url
    rememberLoginImage(data.login_image_url)
    toast.success("Imagen del negocio actualizada", { position: "bottom-center" })
  } catch (error) {
    console.error("Upload branding failed:", error)
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
    toast.error(typeof detail === "string" ? detail : "No se pudo subir la imagen", {
      position: "bottom-center",
    })
  } finally {
    isUploading.value = false
  }
}

async function removeImage() {
  isUploading.value = true
  try {
    await brandingApi.deleteLoginImage()
    currentPath.value = null
    rememberLoginImage(null)
    toast.success("Imagen quitada", { position: "bottom-center" })
  } catch (error) {
    console.error("Delete branding failed:", error)
    toast.error("No se pudo quitar la imagen", { position: "bottom-center" })
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="rounded-xl border border-border p-4">
    <input
      ref="fileInputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
      class="hidden"
      @change="onFileChange"
    >

    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div class="flex items-start gap-3">
        <div class="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <IconPhotoUp class="size-5 text-brand-icon" />
        </div>
        <div class="grid gap-1">
          <p class="text-sm font-medium">
            Imagen del negocio
          </p>
          <p class="text-sm text-muted-foreground">
            Se muestra en la pantalla de inicio de sesión. Puede ser una imagen
            grande: si supera {{ MAX_DIMENSION }} px se ajusta sola, conservando
            su proporción.
          </p>
        </div>
      </div>

      <div class="flex shrink-0 gap-2">
        <Button
          v-if="currentPath"
          variant="outline"
          class="gap-1.5"
          :disabled="isUploading"
          @click="removeImage"
        >
          <IconTrash class="size-4" />
          Quitar
        </Button>
        <Button class="gap-1.5" :disabled="isUploading" @click="fileInputRef?.click()">
          <Spinner v-if="isUploading" class="size-4" />
          <IconUpload v-else class="size-4" />
          {{ currentPath ? "Cambiar" : "Subir imagen" }}
        </Button>
      </div>
    </div>

    <!--
      Vista previa con la MISMA regla de encuadre que el login (`contain` sobre
      un fondo neutro): así lo que se ve acá es lo que va a verse allá, en vez
      de un recorte distinto que sorprenda al cerrar sesión.
    -->
    <div
      v-if="!isLoading"
      class="mt-4 grid h-44 place-items-center overflow-hidden rounded-lg border border-dashed border-border bg-muted/40"
    >
      <img
        v-if="previewUrl"
        :src="previewUrl"
        alt="Imagen del negocio"
        class="max-h-full max-w-full object-contain"
      >
      <p v-else class="px-4 text-center text-sm text-muted-foreground">
        Sin imagen: el inicio de sesión usa el fondo por defecto.
      </p>
    </div>
  </div>
</template>
