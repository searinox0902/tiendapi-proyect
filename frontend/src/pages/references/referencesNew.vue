<script setup lang="ts">
import { computed, onMounted, reactive } from "vue"
import { toast } from "vue-sonner"

import AppSidebar from "@/components/AppSidebar.vue"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
import { useReferencesStore } from "@/stores/references"
import { Badge } from '@/components/ui/badge'


const store = useReferencesStore()

const form = reactive({
  sku: "",
  brand: undefined as string | undefined,
  category_id: undefined as string | undefined,
  title: "",
  description: "",
  base_price: "" as string | number,
})

/** Marcas: no hay catálogo propio en el backend (`brand` es texto libre en `Reference`), así que por ahora se sugieren las que ya existen en el catálogo cargado. */
const brandOptions = computed(() => {
  const unique = new Set(
    store.references.map(reference => reference.brand).filter((brand): brand is string => !!brand),
  )
  return [...unique].sort((a, b) => a.localeCompare(b))
})

onMounted(async () => {
  try {
    await store.fetchCategories()
  } catch {
    toast.error("No se pudieron cargar las categorías", { position: "bottom-center" })
  }
  try {
    await store.fetchReferences({ limit: 200 })
  } catch {
    toast.error("No se pudieron cargar las marcas", { position: "bottom-center" })
  }
})
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
            Registrar referencia
          </h1>
        </div>
      </header>

      <div class="flex w-full flex-1 gap-4 p-4 lg:p-6">
        
        <!-- Formulario -->
        <div class="flex-1 rounded-lg border border-border p-4 lg:p-6">
          <form class="grid grid-cols-1 gap-4 md:grid-cols-2" @submit.prevent>
            <div class="grid gap-2">
              <Label for="new-sku">SKU</Label>
              <Input id="new-sku" v-model="form.sku" placeholder="FRE-0001" />
            </div>

            <div class="grid gap-2">
              <Label for="new-brand">Marca</Label>
              <Select v-model="form.brand">
                <SelectTrigger id="new-brand" class="w-full">
                  <SelectValue placeholder="Selecciona una marca" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="brand in brandOptions" :key="brand" :value="brand">
                    {{ brand }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="grid gap-2">
              <Label for="new-category">Categoría</Label>
              <Select v-model="form.category_id">
                <SelectTrigger id="new-category" class="w-full">
                  <SelectValue placeholder="Selecciona una categoría" />
                </SelectTrigger>
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
            </div>

            <div class="grid gap-2">
              &nbsp;
            </div>

            <div class="grid gap-2 md:col-span-2">
              <Label for="new-title">Nombre</Label>
              <Input id="new-title" v-model="form.title" placeholder="Pastillas de freno delanteras" />
            </div>

            <div class="grid gap-2 md:col-span-2">
              <Label for="new-description">Descripción</Label>
              <Textarea id="new-description" v-model="form.description" />
            </div>
            
            <div class="grid gap-2">
              <Label for="new-price">Precio base</Label>
              <Input id="new-price" v-model="form.base_price" type="number" min="0"/>
            </div>

             
            <div class="grid gap-2">
              <Label for="new-price">IVA</Label>
              <Input id="new-price" v-model="form.base_price" type="number" min="0" max="100" />
            </div>

            <div class="grid gap-2 md:col-span-2">
              <Label for="new-image">Foto</Label>
              <Input id="new-image" type="file" accept="image/*" />
            </div>
          </form>
        </div>

        <!--Vista Previa-->
        <div class="w-sm border border-border p-4 lg:p-6 rounded-lg flex flex-col space-y-8">
          
          <p class="text-gray-600">Vista previa</p>
          
          <div class="bg-gray-100 h-44 w-44">
            <figure>
              <img src=".&" alt="" class="h-auto w-full">
            </figure>
          </div>
          
          <div class="flex-1  space-y-1">
            <p class="font-bold text-lg">SKU : {12312324}</p>
            <p class="text-sm">YAMALUBE</p>
            <P class="font-bold mb-2 text-base">ACEITE YAMALUBE 4T 800ML</P>
            <Badge variant="secondary">
              <span class="font-mono">Aceites/Lubricantes</span>
            </Badge>
          </div>
          
          <div class="border-t border-t-gray-200 border-b border-b-gray-100 py-4 space-y-2">
            <div class="flex">
                <span class="flex-1 text-gray-600">
                  Precio Base:
                </span>

                <span class="font-bold">
                  $ 8.251
                </span>
            </div>
             <div class="flex">
                <span class="flex-1 text-gray-600">
                  IVA:
                </span>

                <span class="font-bold">
                  $ 2.251
                </span>
            </div>
          </div>
          
          <div class="flex items-center">
                <span class="text-lg flex-1 font-bold">
                  Precio Final:
                </span>

                <span class="text-lg font-bold px-3 rounded-full py-1 bg-purple-100 text-purple-700">
                  $ 8.251
                </span>
            </div>
        
        </div>

      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
