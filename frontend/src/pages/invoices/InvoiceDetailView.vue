<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import {
  IconBan,
  IconCheck,
  IconChevronLeft,
  IconCopy,
  IconFileDescription,
  IconPrinter,
} from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { toast } from "vue-sonner"
import { useRouter } from "vue-router"

import AppSidebar from "@/components/AppSidebar.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { isDark } from "@/composables/useTheme"
import { useBillsStore } from "@/stores/bills"
import InvoiceDocument from "./InvoiceDocument.vue"
import InvoiceLinesList from "./InvoiceLinesList.vue"

/** `Bill.id` (UUID) desde la ruta `/factura/:id`. */
const props = defineProps<{ id: string }>()

const router = useRouter()
const store = useBillsStore()

const isVoidOpen = ref(false)
const voidReason = ref("")
const isVoiding = ref(false)
/** El check verde que reemplaza al ícono de copiar por un instante. */
const justCopied = ref(false)

const bill = computed(() => store.detail)
const isVoided = computed(() => bill.value !== null && bill.value.voided_at !== null)

async function load() {
  try {
    await store.fetchDetail(props.id)
  } catch {
    //  El estado de error ya quedó en el store y la pantalla lo pinta con su
    //  botón de reintentar; el toast solo avisa que pasó algo.
    toast.error("No se pudo cargar la factura", { position: "bottom-center" })
  }
}

//  Navegar de una factura a otra sin desmontar la vista (por ejemplo desde un
//  enlace) cambia el parámetro pero no vuelve a montar el componente.
watch(() => props.id, load)
onMounted(load)

function goBack() {
  router.push({ name: "invoices" })
}

async function copyNumber() {
  if (bill.value === null) return
  try {
    await navigator.clipboard.writeText(bill.value.bill_number)
    justCopied.value = true
    setTimeout(() => { justCopied.value = false }, 1500)
  } catch {
    //  Sin permiso de portapapeles (o contexto no seguro) no hay forma de
    //  copiar por código: se dice, en vez de fingir que se copió.
    toast.error("No se pudo copiar al portapapeles", { position: "bottom-center" })
  }
}

/**
 * Imprime la hoja reconstruida. `window.print()` y no una librería de PDF: lo
 * que hay que imprimir ya está en el DOM, y el `@media print` de
 * `InvoiceDocument.vue` deja solo la hoja. Una librería agregaría una
 * dependencia para volver a maquetar lo mismo en otro formato.
 */
function print() {
  window.print()
}

async function confirmVoid() {
  if (bill.value === null) return
  isVoiding.value = true
  try {
    await store.voidBill(bill.value.id, voidReason.value.trim())
    isVoidOpen.value = false
    voidReason.value = ""
    toast.success("Factura anulada y existencias devueltas al inventario", { position: "bottom-center" })
  } catch (error: any) {
    //  El 409 del servidor trae el motivo real (ya estaba anulada, o la DIAN
    //  la autorizó y hay que hacer nota crédito): mostrarlo tal cual es más
    //  útil que un "no se pudo" genérico.
    const detail = error?.response?.data?.detail
    toast.error(typeof detail === "string" ? detail : "No se pudo anular la factura", {
      position: "bottom-center",
    })
  } finally {
    isVoiding.value = false
  }
}

/** El motivo es obligatorio (lo exige el servidor con `min_length=3`). */
const canConfirmVoid = computed(() => voidReason.value.trim().length >= 3)
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
      <div class="min-w-0 px-6 space-y-6 pb-6">
        <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
          <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
            <SidebarTrigger class="-ml-1" />
            
            <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />

            <Button variant="ghost" size="sm" class="-ml-2 gap-1 self-start" @click="goBack">
              <IconChevronLeft class="size-4" />
            </Button>

            <ModuleNavSelect current="invoices" />
            <span class="text-muted-foreground text-sm">
              Detalle ·
              <!-- El consecutivo, no el UUID: es el identificador que el negocio usa para hablar de esta factura. -->
              <span class="font-mono">{{ bill?.bill_number ?? "…" }}</span>
            </span>
            <div class="ml-auto flex items-center gap-2">
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>



        <!-- Falló la carga: no es lo mismo que "factura sin ítems". -->
        <div
          v-if="store.hasDetailError"
          class="flex flex-col items-center gap-2 rounded-lg border border-border py-16"
        >
          <p class="text-destructive">
            No se pudo cargar la factura.
          </p>
          <Button variant="outline" size="sm" @click="load">
            Reintentar
          </Button>
        </div>

        <template v-else-if="store.isLoadingDetail || bill === null">
          <div class="flex flex-col gap-4 rounded-xl border border-border p-4 md:flex-row md:items-center md:justify-between">
            <div class="space-y-2">
              <Skeleton class="h-7 w-40" />
              <Skeleton class="h-4 w-56" />
            </div>
            <div class="flex gap-2">
              <Skeleton class="h-9 w-32" />
              <Skeleton class="h-9 w-44" />
              <Skeleton class="h-9 w-28" />
            </div>
          </div>
          <div class="flex flex-col gap-6 lg:flex-row">
            <Skeleton class="h-96 w-full rounded-xl lg:w-[320px]" />
            <Skeleton class="h-96 min-w-0 flex-1 rounded-xl" />
          </div>
        </template>

        <template v-else>
          <!-- Fila 1 — identificación de la factura y acciones sobre ella. -->
          <div class="flex flex-col gap-4 rounded-xl border border-border p-4 md:flex-row md:items-center md:justify-between">
            <div class="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <p class="truncate font-mono text-xl font-bold font-mono">
                    {{ bill.bill_number }}
                  </p>
                  <!--
                    Copiar el consecutivo, no el UUID: es lo que el usuario
                    pega en un WhatsApp o en un correo para referirse a esta
                    venta. El UUID no le dice nada a nadie.
                  -->
                  <button
                    type="button"
                    class="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                    :aria-label="`Copiar ${bill.bill_number}`"
                    @click="copyNumber"
                  >
                    <IconCheck v-if="justCopied" class="size-4 text-brand-icon" />
                    <IconCopy v-else class="size-4" />
                  </button>
                  <Badge v-if="isVoided" variant="destructive" class="shrink-0">
                    Anulada
                  </Badge>
                </div>
                <p class="truncate text-xs text-muted-foreground">
                  Factura de venta
                </p>
              </div>

              <Separator orientation="vertical" class="hidden h-10 sm:block" />

              <div class="min-w-0">
                <p class="truncate font-medium" :title="bill.customer.fullname">
                  {{ bill.customer.fullname }}
                </p>
                <p class="truncate text-xs text-muted-foreground">
                  <!-- Sin documento cargado se dice; inventar un "N/A" lo haría parecer un dato. -->
                  {{ bill.customer.nit ? `CC/NIT ${bill.customer.nit}` : "Sin documento registrado" }}
                </p>
              </div>
            </div>

            <div class="flex shrink-0 flex-wrap items-center gap-2">
              <!--
                Anular ya no está disponible sobre una factura anulada: el
                servidor lo rechaza igual (409), pero dejar el botón vivo
                invita a intentarlo.
              -->
              <Button
                variant="outline"
                class="gap-2 text-destructive hover:text-destructive"
                :disabled="isVoided"
                @click="isVoidOpen = true"
              >
                <IconBan class="size-4" />
                Anular factura
              </Button>

              <!--
                Declarar ante la DIAN: la integración está delegada a un tercero
                y **diferida** (D-09/D-38), así que no hay a quién declararle
                todavía. El botón se muestra —es parte del flujo final y sirve
                para que la pantalla no cambie de forma el día que exista— pero
                inactivo y diciendo por qué. `span` intermedio: un botón
                `disabled` no emite eventos de puntero y el tooltip nunca se
                abriría.
              -->
              <Tooltip>
                <TooltipTrigger as-child>
                  <span tabindex="0" class="inline-flex">
                    <Button variant="outline" class="gap-2" disabled>
                      <IconFileDescription class="size-4" />
                      Declarar ante la DIAN
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent class="max-w-64">
                  La facturación electrónica está delegada a un proveedor externo y
                  todavía no está integrada (D-09/D-38).
                </TooltipContent>
              </Tooltip>

              <Button class="gap-2 text-white hover:text-white" @click="print">
                <IconPrinter class="size-4" />
                Imprimir
              </Button>
            </div>
          </div>

          <!--
            Motivo de la anulación, en la pantalla y no solo en la base: es el
            dato que explica por qué esta venta no cuenta.
          -->
          <div
            v-if="isVoided && bill.void_reason"
            class="rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm"
          >
            <span class="font-medium text-destructive">Motivo de la anulación:</span>
            {{ bill.void_reason }}
          </div>

          <!-- Fila 2 — ítems vendidos a la izquierda, documento a la derecha. -->
          <div class="flex min-w-0 flex-col gap-6 lg:h-screen lg:flex-row">
            <InvoiceLinesList
              :lines="bill.lines"
              :subtotal="bill.subtotal"
              :total-iva="bill.total_iva"
              :total="bill.total"
              :voided="isVoided"
            />
            <InvoiceDocument :bill="bill" />
          </div>
        </template>
      </div>
    </SidebarInset>

    <AlertDialog v-model:open="isVoidOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>¿Anular esta factura?</AlertDialogTitle>
          <AlertDialogDescription>
            La factura conserva su número y sus líneas, pero deja de sumar a lo
            facturado, al IVA y a la utilidad. Las unidades vendidas
            <strong class="font-medium text-foreground">vuelven al inventario</strong>
            como disponibles. No se puede deshacer.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div class="grid gap-2">
          <Label for="void-reason">Motivo</Label>
          <Textarea
            id="void-reason"
            v-model="voidReason"
            placeholder="Ej.: devolución del cliente, error de digitación…"
            rows="3"
          />
          <!--
            Obligatorio (el servidor exige 3 caracteres): un mes después,
            "anulada" a secas no distingue una devolución de un error, y para
            el inventario no son lo mismo.
          -->
          <p class="text-xs text-muted-foreground">
            Queda registrado con la factura.
          </p>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel :disabled="isVoiding">
            Cancelar
          </AlertDialogCancel>
          <!--
            `Button` y no `AlertDialogAction` (que es lo que usa el borrado de
            existencias): `AlertDialogAction` cierra el diálogo en su propio
            manejador de clic, así que se cerraría **antes** de saber si el
            servidor aceptó — y con él se perdería el motivo ya escrito, que
            habría que teclear de nuevo. Acá lo cierra `confirmVoid`, solo si
            la anulación salió bien.
          -->
          <Button
            :disabled="!canConfirmVoid || isVoiding"
            class="bg-destructive text-white hover:bg-destructive/90"
            @click="confirmVoid"
          >
            {{ isVoiding ? "Anulando…" : "Anular factura" }}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </SidebarProvider>
</template>
