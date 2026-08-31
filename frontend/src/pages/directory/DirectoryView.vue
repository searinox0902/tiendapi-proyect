<script setup lang="ts">
import { onMounted, ref } from "vue"
import {
  IconAward,
  IconCategory,
  IconMapPin,
  IconTruckDelivery,
  IconUsers,
} from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"

import AppSidebar from "@/components/AppSidebar.vue"
import DirectoryExportPopover from "@/components/DirectoryExportPopover.vue"
import DirectoryImportDialog from "@/components/DirectoryImportDialog.vue"
import DirectoryImportPopover from "@/components/DirectoryImportPopover.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { isDark } from "@/composables/useTheme"
import { resolveCategoryIcon } from "@/lib/categoryIcons"
import { directoryApi } from "@/api/directory/directory.api"
import type { IDirectorySummary } from "@/api/directory/directory.types"
import CreateBrandDialog from "./CreateBrandDialog.vue"
import CreateCategoryDialog from "./CreateCategoryDialog.vue"
import CreateCustomerDialog from "./CreateCustomerDialog.vue"
import CreateLocationDialog from "./CreateLocationDialog.vue"
import CreateProviderDialog from "./CreateProviderDialog.vue"

/**
 * Directorio: datos base compartidos que no son trabajo diario (Proveedores,
 * Ubicaciones, Categorías, Clientes, Marcas) — sacados del sidebar principal
 * para no competir con las pantallas operativas (Referencias, Productos,
 * Caja, Facturación). Un resumen (conteo + últimos 5) por entidad, cada uno
 * con su propio alta rápida.
 */

const summary = ref<IDirectorySummary | null>(null)
const isLoading = ref(false)
const hasError = ref(false)

async function loadSummary() {
  isLoading.value = true
  hasError.value = false
  try {
    summary.value = (await directoryApi.getSummary()).data
  } catch (error) {
    console.error("Fetch directory summary failed:", error)
    hasError.value = true
  } finally {
    isLoading.value = false
  }
}

onMounted(loadSummary)

type DialogKey = "providers" | "locations" | "categories" | "customers" | "brands"
const openDialog = ref<DialogKey | null>(null)

function onCreated() {
  loadSummary()
}

//  Un ref por entidad para poder llamar `.pickFile(accept)` desde el popover
//  de import de esa misma card — `InstanceType<typeof DirectoryImportDialog>`
//  porque `pickFile` se expone vía `defineExpose`, no es un prop.
const providerImportRef = ref<InstanceType<typeof DirectoryImportDialog> | null>(null)
const locationImportRef = ref<InstanceType<typeof DirectoryImportDialog> | null>(null)
const categoryImportRef = ref<InstanceType<typeof DirectoryImportDialog> | null>(null)
const customerImportRef = ref<InstanceType<typeof DirectoryImportDialog> | null>(null)
const brandImportRef = ref<InstanceType<typeof DirectoryImportDialog> | null>(null)
</script>

<template>
  <SidebarProvider
    :style="{
      '--sidebar-width': 'calc(var(--spacing) * 72)',
      '--header-height': 'calc(var(--spacing) * 12)',
    }"
  >
    <AppSidebar variant="inset" />
    <SidebarInset class="min-w-0">
      <div class="min-w-0 space-y-6 px-6 pb-6">
        <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
          <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
            <SidebarTrigger class="-ml-1" />
            <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
            <ModuleNavSelect current="directory" />
            <div class="ml-auto flex items-center gap-2">
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <p v-if="hasError" class="text-sm text-destructive">
          No se pudo cargar el Directorio.
          <button type="button" class="underline" @click="loadSummary">
            Reintentar
          </button>
        </p>

        <!-- Cards de resumen: una por entidad, mismo alto para que no salten al cargar. -->
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <template v-if="isLoading || !summary">
            <div
              v-for="placeholder in 5"
              :key="placeholder"
              class="min-h-24 space-y-2 rounded-xl border border-border px-4 py-3"
            >
              <Skeleton class="h-4 w-24" />
              <Skeleton class="h-8 w-12" />
            </div>
          </template>
          <template v-else>
            <div class="min-h-24 rounded-xl border border-border px-4 py-3">
              <p class="flex items-center gap-2 text-sm text-muted-foreground">
                <IconTruckDelivery class="size-4" /> Proveedores
              </p>
              <p class="text-2xl font-bold tabular-nums">
                {{ summary.total_providers }}
              </p>
            </div>
            <div class="min-h-24 rounded-xl border border-border px-4 py-3">
              <p class="flex items-center gap-2 text-sm text-muted-foreground">
                <IconMapPin class="size-4" /> Ubicaciones
              </p>
              <p class="text-2xl font-bold tabular-nums">
                {{ summary.total_locations }}
              </p>
            </div>
            <div class="min-h-24 rounded-xl border border-border px-4 py-3">
              <p class="flex items-center gap-2 text-sm text-muted-foreground">
                <IconCategory class="size-4" /> Categorías
              </p>
              <p class="text-2xl font-bold tabular-nums">
                {{ summary.total_categories }}
              </p>
            </div>
            <div class="min-h-24 rounded-xl border border-border px-4 py-3">
              <p class="flex items-center gap-2 text-sm text-muted-foreground">
                <IconUsers class="size-4" /> Clientes
              </p>
              <p class="text-2xl font-bold tabular-nums">
                {{ summary.total_customers }}
              </p>
            </div>
            <div class="min-h-24 rounded-xl border border-border px-4 py-3">
              <p class="flex items-center gap-2 text-sm text-muted-foreground">
                <IconAward class="size-4" /> Marcas
              </p>
              <p class="text-2xl font-bold tabular-nums">
                {{ summary.total_brands }}
              </p>
            </div>
          </template>
        </div>

        <!-- Minitablas: últimos 5 de cada entidad + alta rápida. -->
        <div class="grid gap-4 grid-cols-2 xl:grid-cols-2">
          <div class="rounded-xl border border-border">
            <div class="flex items-center justify-between border-b border-border px-4 py-3">
              <h2 class="flex items-center gap-2 text-sm font-medium">
                <IconTruckDelivery class="size-4 text-brand-icon" /> Proveedores
              </h2>
              <div class="flex items-center gap-1">
                <DirectoryImportPopover @pick="accept => providerImportRef?.pickFile(accept)" />
                <DirectoryExportPopover entity="providers" />
                <Button size="sm" variant="default" @click="openDialog = 'providers'">
                  Agregar
                </Button>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>NIT</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableEmpty v-if="!summary?.latest_providers.length" :colspan="2">
                  Sin proveedores todavía
                </TableEmpty>
                <TableRow v-for="provider in summary?.latest_providers" v-else :key="provider.id">
                  <TableCell>{{ provider.title }}</TableCell>
                  <TableCell class="text-muted-foreground">
                    {{ provider.nit ?? "—" }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <div class="rounded-xl border border-border">
            <div class="flex items-center justify-between border-b border-border px-4 py-3">
              <h2 class="flex items-center gap-2 text-sm font-medium">
                <IconMapPin class="size-4 text-brand-icon" /> Ubicaciones
              </h2>
              <div class="flex items-center gap-1">
                <DirectoryImportPopover @pick="accept => locationImportRef?.pickFile(accept)" />
                <DirectoryExportPopover entity="locations" />
                <Button size="sm" variant="default" @click="openDialog = 'locations'">
                  Agregar
                </Button>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Tipo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableEmpty v-if="!summary?.latest_locations.length" :colspan="2">
                  Sin ubicaciones todavía
                </TableEmpty>
                <TableRow v-for="location in summary?.latest_locations" v-else :key="location.id">
                  <TableCell>{{ location.name }}</TableCell>
                  <TableCell class="text-muted-foreground capitalize">
                    {{ location.type }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <div class="rounded-xl border border-border">
            <div class="flex items-center justify-between border-b border-border px-4 py-3">
              <h2 class="flex items-center gap-2 text-sm font-medium">
                <IconCategory class="size-4 text-brand-icon" /> Categorías
              </h2>
              <div class="flex items-center gap-1">
                <DirectoryImportPopover @pick="accept => categoryImportRef?.pickFile(accept)" />
                <DirectoryExportPopover entity="categories" />
                <Button size="sm" variant="default" @click="openDialog = 'categories'">
                  Agregar
                </Button>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Descripción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableEmpty v-if="!summary?.latest_categories.length" :colspan="2">
                  Sin categorías todavía
                </TableEmpty>
                <TableRow v-for="category in summary?.latest_categories" v-else :key="category.id">
                  <TableCell>
                    <span class="flex items-center gap-2">
                      <component :is="resolveCategoryIcon(category.icon)" class="size-4 text-brand-icon" />
                      {{ category.name }}
                    </span>
                  </TableCell>
                  <TableCell class="text-muted-foreground">
                    {{ category.description ?? "—" }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <div class="rounded-xl border border-border">
            <div class="flex items-center justify-between border-b border-border px-4 py-3">
              <h2 class="flex items-center gap-2 text-sm font-medium">
                <IconUsers class="size-4 text-brand-icon" /> Clientes
              </h2>
              <div class="flex items-center gap-1">
                <DirectoryImportPopover @pick="accept => customerImportRef?.pickFile(accept)" />
                <DirectoryExportPopover entity="customers" />
                <Button size="sm" variant="default" @click="openDialog = 'customers'">
                  Agregar
                </Button>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Cédula/NIT</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableEmpty v-if="!summary?.latest_customers.length" :colspan="2">
                  Sin clientes todavía
                </TableEmpty>
                <TableRow v-for="customer in summary?.latest_customers" v-else :key="customer.id">
                  <TableCell>{{ customer.fullname }}</TableCell>
                  <TableCell class="text-muted-foreground">
                    {{ customer.nit ?? "—" }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <div class="rounded-xl border border-border">
            <div class="flex items-center justify-between border-b border-border px-4 py-3">
              <h2 class="flex items-center gap-2 text-sm font-medium">
                <IconAward class="size-4 text-brand-icon" /> Marcas
              </h2>
              <div class="flex items-center gap-1">
                <DirectoryImportPopover @pick="accept => brandImportRef?.pickFile(accept)" />
                <DirectoryExportPopover entity="brands" />
                <Button size="sm" variant="default" @click="openDialog = 'brands'">
                  Agregar
                </Button>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Descripción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableEmpty v-if="!summary?.latest_brands.length" :colspan="2">
                  Sin marcas todavía
                </TableEmpty>
                <TableRow v-for="brand in summary?.latest_brands" v-else :key="brand.id">
                  <TableCell>{{ brand.name }}</TableCell>
                  <TableCell class="text-muted-foreground">
                    {{ brand.description ?? "—" }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>
      </div>
    </SidebarInset>

    <CreateProviderDialog
      :open="openDialog === 'providers'"
      @update:open="value => { if (!value) openDialog = null }"
      @created="onCreated"
    />
    <CreateLocationDialog
      :open="openDialog === 'locations'"
      @update:open="value => { if (!value) openDialog = null }"
      @created="onCreated"
    />
    <CreateCategoryDialog
      :open="openDialog === 'categories'"
      @update:open="value => { if (!value) openDialog = null }"
      @created="onCreated"
    />
    <CreateCustomerDialog
      :open="openDialog === 'customers'"
      @update:open="value => { if (!value) openDialog = null }"
      @created="onCreated"
    />
    <CreateBrandDialog
      :open="openDialog === 'brands'"
      @update:open="value => { if (!value) openDialog = null }"
      @created="onCreated"
    />

    <DirectoryImportDialog
      ref="providerImportRef"
      entity="providers"
      entity-label="proveedores"
      @imported="loadSummary"
    />
    <DirectoryImportDialog
      ref="locationImportRef"
      entity="locations"
      entity-label="ubicaciones"
      @imported="loadSummary"
    />
    <DirectoryImportDialog
      ref="categoryImportRef"
      entity="categories"
      entity-label="categorías"
      @imported="loadSummary"
    />
    <DirectoryImportDialog
      ref="customerImportRef"
      entity="customers"
      entity-label="clientes"
      @imported="loadSummary"
    />
    <DirectoryImportDialog
      ref="brandImportRef"
      entity="brands"
      entity-label="marcas"
      @imported="loadSummary"
    />
  </SidebarProvider>
</template>
