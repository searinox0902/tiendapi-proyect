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
import { customersApi } from "@/api/customers/customers.api"
import type { ICustomer } from "@/api/customers/customers.types"

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{ created: [ICustomer] }>()

const fullname = ref("")
const nit = ref("")
const mail = ref("")
const isSubmitting = ref(false)

function reset() {
  fullname.value = ""
  nit.value = ""
  mail.value = ""
}

watch(open, isOpen => {
  if (isOpen) reset()
})

async function onSubmit() {
  if (!fullname.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const { data } = await customersApi.createCustomer({
      fullname: fullname.value.trim(),
      nit: nit.value.trim() || null,
      mail: mail.value.trim() || null,
    })
    emit("created", data)
    open.value = false
    toast.success("Cliente creado")
  } catch (error) {
    console.error("Create customer failed:", error)
    toast.error("No se pudo crear el cliente")
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Nuevo cliente</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="onSubmit">
        <div class="grid gap-2">
          <Label for="customer-fullname">Nombre</Label>
          <Input id="customer-fullname" v-model="fullname" placeholder="Ingrese" />
        </div>
        <div class="grid gap-2">
          <Label for="customer-nit">Cédula/NIT</Label>
          <Input id="customer-nit" v-model="nit" placeholder="Ingrese" />
        </div>
        <div class="grid gap-2">
          <Label for="customer-mail">Correo</Label>
          <Input id="customer-mail" v-model="mail" placeholder="Ingrese" />
        </div>
        <DialogFooter>
          <Button type="submit" :disabled="!fullname.trim() || isSubmitting">
            {{ isSubmitting ? "Creando…" : "Crear" }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
