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
import { brandsApi } from "@/api/brands/brands.api"
import type { IBrand } from "@/api/brands/brands.types"

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{ created: [IBrand] }>()

const name = ref("")
const description = ref("")
const isSubmitting = ref(false)

function reset() {
  name.value = ""
  description.value = ""
}

watch(open, isOpen => {
  if (isOpen) reset()
})

async function onSubmit() {
  if (!name.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const { data } = await brandsApi.createBrand({
      name: name.value.trim(),
      description: description.value.trim() || null,
    })
    emit("created", data)
    open.value = false
    toast.success("Marca creada")
  } catch (error) {
    console.error("Create brand failed:", error)
    toast.error("No se pudo crear la marca")
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Nueva marca</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="onSubmit">
        <div class="grid gap-2">
          <Label for="brand-name">Nombre</Label>
          <Input id="brand-name" v-model="name" placeholder="Bosch" />
        </div>
        <div class="grid gap-2">
          <Label for="brand-description">Descripción</Label>
          <Input id="brand-description" v-model="description" placeholder="Repuestos eléctricos" />
        </div>
        <DialogFooter>
          <Button type="submit" :disabled="!name.trim() || isSubmitting">
            {{ isSubmitting ? "Creando…" : "Crear" }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
