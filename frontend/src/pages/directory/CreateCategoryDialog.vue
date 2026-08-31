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
import { categoriesApi } from "@/api/categories/categories.api"
import { CATEGORY_ICON_OPTIONS, resolveCategoryIcon } from "@/lib/categoryIcons"
import { cn } from "@/lib/utils"
import type { ICategory } from "@/api/categories/categories.types"

const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{ created: [ICategory] }>()

const name = ref("")
const description = ref("")
const icon = ref("")
const isSubmitting = ref(false)

function reset() {
  name.value = ""
  description.value = ""
  icon.value = ""
}

watch(open, isOpen => {
  if (isOpen) reset()
})

async function onSubmit() {
  if (!name.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const { data } = await categoriesApi.createCategory({
      name: name.value.trim(),
      description: description.value.trim() || null,
      icon: icon.value || null,
    })
    emit("created", data)
    open.value = false
    toast.success("Categoría creada")
  } catch (error) {
    console.error("Create category failed:", error)
    toast.error("No se pudo crear la categoría")
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Nueva categoría</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="onSubmit">
        <div class="grid gap-2">
          <Label for="category-name">Nombre</Label>
          <Input id="category-name" v-model="name" placeholder="Frenos" />
        </div>
        <div class="grid gap-2">
          <Label for="category-description">Descripción</Label>
          <Input id="category-description" v-model="description" placeholder="Pastillas, discos, líquidos" />
        </div>
        <div class="grid gap-2">
          <Label>Ícono</Label>
          <div class="grid grid-cols-6 gap-2 sm:grid-cols-8">
            <button
              v-for="option in CATEGORY_ICON_OPTIONS"
              :key="option.value"
              type="button"
              :aria-pressed="icon === option.value"
              :title="option.label"
              class="flex size-9 items-center justify-center rounded-md border transition-colors"
              :class="cn(
                icon === option.value
                  ? 'border-primary bg-primary/10 text-brand-icon'
                  : 'border-border text-muted-foreground hover:border-primary/50',
              )"
              @click="icon = option.value"
            >
              <component :is="resolveCategoryIcon(option.value)" class="size-4" />
            </button>
          </div>
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
