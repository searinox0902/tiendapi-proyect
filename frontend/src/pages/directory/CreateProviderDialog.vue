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
import { providersApi } from "@/api/providers/providers.api"
import type { IProvider } from "@/api/providers/providers.types"

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{ created: [IProvider] }>()

const title = ref("")
const nit = ref("")
const providerCode = ref("")
const isSubmitting = ref(false)

function reset() {
  title.value = ""
  nit.value = ""
  providerCode.value = ""
}

watch(open, isOpen => {
  if (isOpen) reset()
})

async function onSubmit() {
  if (!title.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const { data } = await providersApi.createProvider({
      title: title.value.trim(),
      nit: nit.value.trim() || null,
      provider_code: providerCode.value.trim() || null,
    })
    emit("created", data)
    open.value = false
    toast.success("Proveedor creado")
  } catch (error) {
    console.error("Create provider failed:", error)
    toast.error("No se pudo crear el proveedor")
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Nuevo proveedor</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="onSubmit">
        <div class="grid gap-2">
          <Label for="provider-title">Nombre</Label>
          <Input id="provider-title" v-model="title" placeholder="Repuestos del Norte" />
        </div>
        <div class="grid gap-2">
          <Label for="provider-nit">NIT</Label>
          <Input id="provider-nit" v-model="nit" placeholder="900123456-7" />
        </div>
        <div class="grid gap-2">
          <Label for="provider-code">Código</Label>
          <Input id="provider-code" v-model="providerCode" placeholder="PROV-001" />
        </div>
        <DialogFooter>
          <Button type="submit" :disabled="!title.trim() || isSubmitting">
            {{ isSubmitting ? "Creando…" : "Crear" }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
