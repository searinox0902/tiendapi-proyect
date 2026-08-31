<script setup lang="ts">
import { ref, watch } from "vue"
import { toast } from "vue-sonner"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { locationsApi } from "@/api/locations/locations.api"
import type { ILocation, TLocationType } from "@/api/locations/locations.types"

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{ created: [ILocation] }>()

const name = ref("")
const type = ref<TLocationType | "">("")
const address = ref("")
const isSubmitting = ref(false)

function reset() {
  name.value = ""
  type.value = ""
  address.value = ""
}

watch(open, isOpen => {
  if (isOpen) reset()
})

async function onSubmit() {
  if (!name.value.trim() || !type.value || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const { data } = await locationsApi.createLocation({
      name: name.value.trim(),
      type: type.value,
      address: address.value.trim() || null,
    })
    emit("created", data)
    open.value = false
    toast.success("Ubicación creada")
  } catch (error) {
    console.error("Create location failed:", error)
    toast.error("No se pudo crear la ubicación")
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Nueva ubicación</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="onSubmit">
        <div class="grid gap-2">
          <Label for="location-name">Nombre</Label>
          <Input id="location-name" v-model="name" placeholder="Bodega principal" />
        </div>
        <div class="grid gap-2">
          <Label for="location-type">Tipo</Label>
          <Select v-model="type">
            <SelectTrigger id="location-type" class="w-full">
              <SelectValue placeholder="Selecciona un tipo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sucursal">
                Sucursal
              </SelectItem>
              <SelectItem value="bodega">
                Bodega
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="grid gap-2">
          <Label for="location-address">Dirección</Label>
          <Input id="location-address" v-model="address" placeholder="Cra 45 #12-30" />
        </div>
        <DialogFooter>
          <Button type="submit" :disabled="!name.trim() || !type || isSubmitting">
            {{ isSubmitting ? "Creando…" : "Crear" }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
