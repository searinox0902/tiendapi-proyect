<script setup lang="ts">
import { computed, ref, watch } from "vue"
import type { AcceptableValue } from "reka-ui"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import EmployeeCombobox from "./EmployeeCombobox.vue"
import { MARKER_COLOR, MARKER_LABEL, NOVELTY_COLOR, NOVELTY_LABEL } from "./dayActions"
import type { IDayAction } from "./dayActions"
import { MONTH_NAMES } from "./usePayrollCalendar"
import type {
  IEmployee,
  IMarker,
  INovelty,
  MarkerKind,
  NoveltyKind,
  NoveltySpan,
} from "./payroll.types"

/**
 * Novedad de una persona en un día. **Un solo modal para crear, editar y
 * borrar.**
 *
 * El tipo dejó de venir cerrado desde el "..." y pasó a un selector dentro del
 * formulario. El menú sigue preseleccionando —una pregunta menos— pero ahora
 * equivocarse cuesta un clic y no cancelar y volver a empezar.
 *
 * **Y ahí se resuelve el borrado, sin botón aparte.** Al elegir persona y día
 * el formulario se autocompleta con lo ya registrado: si Fernando tenía un
 * permiso de 4 horas, aparecen las 4 horas. Cambiarlas edita; ponerlas en 0
 * —o elegir "Laboró normal"— quita la novedad.
 *
 * La clave está en cómo está planteado el selector: no es "¿qué quieres
 * agregar?" sino **"¿qué pasó con esta persona este día?"**, y una respuesta
 * válida es "nada". Planteado así, borrar deja de ser una operación aparte y
 * pasa a ser otra respuesta más. La pregunta es el marco, no la etiqueta: los
 * campos se rotulan con sustantivos —Persona, Novedad, Horas— porque en un
 * formulario los interrogantes se leen como cuestionario.
 */

const props = defineProps<{
  open: boolean
  /** Preselección que viene del "...". Sin ella el modal abre en "Laboró normal". */
  action: IDayAction | null
  date: string
  employees: IEmployee[]
  presetEmployeeId?: string | null
  /** Lo ya registrado ese día, para autocompletar. */
  dayNovelties: INovelty[]
  dayMarkers: IMarker[]
}>()

const emit = defineEmits<{
  "update:open": [value: boolean]
  save: [payload: ICapturePayload]
}>()

export type ISelection =
  | { type: "novelty"; kind: NoveltyKind }
  | { type: "marker"; kind: MarkerKind }
  | { type: "day"; kind: "non_working" | "note" }

export interface ICapturePayload {
  employeeId: string | null
  /** Fecha de fin; igual a la de inicio cuando la novedad es de un solo día. */
  endDate: string
  attachmentName: string | null
  /** `null` = sin novedad: quita lo que hubiera y no crea nada. */
  selection: ISelection | null
  span: NoveltySpan
  amount: string
  note: string
  /** Lo que existía antes, para reemplazarlo o quitarlo. */
  existingNoveltyId: string | null
  existingMarkerId: string | null
}

/** El valor "nada pasó". Es una respuesta, no la ausencia de una. */
const NONE = "none"
const NONE_LABEL = "Laboró normal"

/**
 * Cada opción lleva el color con que el calendario la pinta: el selector
 * habla el mismo idioma que la leyenda y los anillos de los avatares.
 */
const OPTIONS: { value: string; label: string; color: string; selection: ISelection }[] = [
  {
    value: "absence",
    label: NOVELTY_LABEL.absence,
    color: NOVELTY_COLOR.absence,
    selection: { type: "novelty", kind: "absence" },
  },
  {
    value: "sick_leave",
    label: NOVELTY_LABEL.sick_leave,
    color: NOVELTY_COLOR.sick_leave,
    selection: { type: "novelty", kind: "sick_leave" },
  },
  {
    value: "vacation",
    label: NOVELTY_LABEL.vacation,
    color: NOVELTY_COLOR.vacation,
    selection: { type: "novelty", kind: "vacation" },
  },
  {
    value: "leave",
    label: NOVELTY_LABEL.leave,
    color: NOVELTY_COLOR.leave,
    selection: { type: "novelty", kind: "leave" },
  },
  {
    value: "overtime",
    label: MARKER_LABEL.overtime,
    color: MARKER_COLOR,
    selection: { type: "marker", kind: "overtime" },
  },
]

const selected = ref<string>(NONE)
/**
 * Lo que el usuario eligió con su mano —o lo que pidió el "..."—, aparte de
 * lo que el autocompletado pone. Con el tipo de primero, cambiar de persona
 * no puede pisar esa elección con el valor por defecto.
 */
const chosenKind = ref<string>(NONE)
const employeeId = ref<string | null>(null)
const span = ref<NoveltySpan>("full_day")
const amount = ref("")
const note = ref("")
const endDate = ref("")
const attachmentName = ref<string | null>(null)

const employee = computed(
  () => props.employees.find((item) => item.id === employeeId.value) ?? null,
)

const selectedOption = computed(
  () => OPTIONS.find((option) => option.value === selected.value) ?? null,
)
const selection = computed(() => selectedOption.value?.selection ?? null)

/** El Select emite `AcceptableValue`; acá solo circulan strings, y `null` no ocurre. */
function chooseKind(value: AcceptableValue) {
  const kind = typeof value === "string" ? value : NONE
  selected.value = kind
  chosenKind.value = kind
}

/** Las acciones de día no son de nadie: ese caso no usa el selector. */
const isDayAction = computed(() => props.action?.action.type === "day")

const existingNovelty = computed(() =>
  employeeId.value
    ? (props.dayNovelties.find((novelty) => novelty.employeeId === employeeId.value) ?? null)
    : null,
)
const existingMarker = computed(() =>
  employeeId.value
    ? (props.dayMarkers.find((marker) => marker.employeeId === employeeId.value) ?? null)
    : null,
)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      const preset = props.action?.action
      chosenKind.value = preset && preset.type !== "day" ? preset.kind : NONE
      employeeId.value = props.presetEmployeeId ?? null
    }
  },
  { immediate: true },
)

/**
 * Autocompleta con lo que ya estaba, y **reacciona al cambio de persona**, no
 * solo a la apertura.
 *
 * Eso último es lo que lo hace honesto: al pasar de Fernando a Marcela se ve lo
 * de Marcela, en vez de los datos del anterior esperando a que alguien los
 * pise sin darse cuenta. Y si Marcela no tiene nada, el tipo vuelve a lo que
 * el usuario eligió, no a lo que Fernando tenía.
 */
watch(
  [() => props.open, employeeId],
  ([isOpen]) => {
    if (!isOpen) {
      return
    }

    const novelty = existingNovelty.value
    const marker = existingMarker.value

    if (novelty) {
      selected.value = novelty.kind
      span.value = novelty.span
      amount.value = novelty.hours ? String(novelty.hours) : ""
      note.value = novelty.label
      endDate.value = novelty.end
      attachmentName.value = novelty.attachmentName ?? null
      return
    }
    if (marker) {
      selected.value = marker.kind
      span.value = "full_day"
      amount.value = marker.quantity ? String(marker.quantity) : ""
      note.value = ""
      endDate.value = marker.date
      attachmentName.value = null
      return
    }

    // Sin registro previo: lo elegido a mano o lo que pidió el "...".
    selected.value = chosenKind.value
    span.value = "full_day"
    amount.value = ""
    note.value = ""
    endDate.value = props.date
    attachmentName.value = null
  },
  { immediate: true },
)

/**
 * Las horas arrancan en `0`, no vacías.
 *
 * Un campo numérico vacío obliga a adivinar si está sin llenar o en cero; con
 * `0` el estado inicial es explícito y las flechas del input tienen desde
 * dónde subir. Se recalcula al cambiar de tipo o duración porque el campo
 * aparece y desaparece con ellos.
 */
watch([selection, span], () => {
  if (needsHours.value && amount.value.trim() === "") {
    amount.value = "0"
  }
})

const needsSpan = computed(() => selection.value?.type === "novelty")

/**
 * Rango de fechas: el día desde el que se entró queda como **mínimo** y el
 * final es libre hacia adelante. Nunca hacia atrás — se está registrando algo
 * que arranca hoy, no reescribiendo el pasado desde acá.
 *
 * Solo aplica a novedades de día completo: medio día y por horas son, por
 * definición, de un solo día.
 */
const needsRange = computed(
  () => selection.value?.type === "novelty" && span.value === "full_day",
)

/** Incapacidad y permiso traen soporte: certificado de la EPS, carta, etc. */
const needsAttachment = computed(
  () =>
    selection.value?.type === "novelty" &&
    (selection.value.kind === "sick_leave" || selection.value.kind === "leave"),
)

const isVacation = computed(
  () => selection.value?.type === "novelty" && selection.value.kind === "vacation",
)

/**
 * Días seleccionados, **de calendario**.
 *
 * Las vacaciones en Colombia se causan en días **hábiles** (15 al año), así que
 * esta cuenta no es la legal: no descuenta domingos ni festivos. Sirve para
 * advertir sobre el saldo, no para liquidar — eso lo hará el motor (D-113).
 */
const selectedDays = computed(() => {
  if (!needsRange.value || !endDate.value) {
    return 1
  }
  const start = Date.UTC(...(props.date.split("-").map(Number) as [number, number, number]))
  const end = Date.UTC(...(endDate.value.split("-").map(Number) as [number, number, number]))
  return Math.max(1, Math.round((end - start) / 86_400_000) + 1)
})

const exceedsBalance = computed(
  () => isVacation.value && employee.value !== null && selectedDays.value > employee.value.vacationBalance,
)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  attachmentName.value = input.files?.[0]?.name ?? null
}

/**
 * La única cantidad que se pide son horas: las extra, o las de un permiso por
 * horas. Desde que la bonificación salió del calendario (D-121) no hay campo
 * de dinero en este formulario.
 */
const needsHours = computed(
  () =>
    (selection.value?.type === "marker" && selection.value.kind === "overtime") ||
    (selection.value?.type === "novelty" && span.value === "hours"),
)

/** Poner la cantidad en 0 equivale a decir "no pasó nada". */
const clearsByZero = computed(
  () => needsHours.value && amount.value.trim() !== "" && Number(amount.value) === 0,
)

const isEditing = computed(() => Boolean(existingNovelty.value || existingMarker.value))

const willDelete = computed(
  () => isEditing.value && (selected.value === NONE || clearsByZero.value),
)

const dateLabel = computed(() => {
  const [, month, day] = props.date.split("-").map(Number)
  return `${day} de ${MONTH_NAMES[month - 1]?.toLowerCase() ?? ""}`
})

const canSave = computed(() => {
  if (isDayAction.value) {
    return true
  }
  if (employeeId.value === null) {
    return false
  }
  if (needsHours.value) {
    const quantity = Number(amount.value)
    if (amount.value.trim() === "" || Number.isNaN(quantity)) {
      return false
    }
    // Editando, el 0 significa "quitar". Creando, no significa nada: una
    // novedad de cero horas no es una novedad.
    if (quantity === 0 && !isEditing.value) {
      return false
    }
  }
  return true
})

const saveLabel = computed(() => {
  if (willDelete.value) {
    return "Quitar novedad"
  }
  return isEditing.value ? "Guardar cambios" : "Guardar"
})

const SPANS: { value: NoveltySpan; label: string }[] = [
  { value: "full_day", label: "Día completo" },
  { value: "half_day", label: "Medio día" },
  { value: "hours", label: "Por horas" },
]

const dayActionTitle = computed(() =>
  props.action?.action.type === "day" && props.action.action.kind === "non_working"
    ? "Día no laborable"
    : "Anotación del día",
)

function save() {
  if (!canSave.value) {
    return
  }

  if (isDayAction.value && props.action) {
    emit("save", {
      employeeId: null,
      endDate: props.date,
      attachmentName: null,
      selection: props.action.action as ISelection,
      span: "full_day",
      amount: "",
      note: note.value,
      existingNoveltyId: null,
      existingMarkerId: null,
    })
    emit("update:open", false)
    return
  }

  emit("save", {
    employeeId: employeeId.value,
    endDate: needsRange.value && endDate.value ? endDate.value : props.date,
    attachmentName: attachmentName.value,
    selection: selected.value === NONE || clearsByZero.value ? null : selection.value,
    span: span.value,
    amount: amount.value,
    note: note.value,
    existingNoveltyId: existingNovelty.value?.id ?? null,
    existingMarkerId: existingMarker.value?.id ?? null,
  })
  emit("update:open", false)
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="max-h-[88vh] sm:max-w-xl">
      <DialogHeader>
        <DialogTitle>{{ isDayAction ? dayActionTitle : "Novedad" }}</DialogTitle>
        <DialogDescription>{{ dateLabel }}</DialogDescription>
      </DialogHeader>

      <div class="min-h-[18rem] space-y-4 overflow-y-auto">
        <template v-if="!isDayAction">
          <!--
            El tipo va de primero y sin rótulo: el título ya dice "Novedad" y este
            control es su respuesta. Más alto y con el color del tipo, para que
            se lea como la pregunta principal del formulario y no como un campo
            más. `min-h` en vez de `h`: la altura por tamaño del trigger tiene
            más especificidad y pisaría un `h-12`.
          -->
          <Select :model-value="selected" @update:model-value="chooseKind">
            <SelectTrigger
              class="min-h-12 w-full text-base font-medium"
              aria-label="Tipo de novedad"
            >
              <SelectValue>
                <span
                  class="size-2.5 shrink-0 rounded-full"
                  :class="{ 'border-2 border-muted-foreground/40': !selectedOption }"
                  :style="selectedOption ? { backgroundColor: selectedOption.color } : undefined"
                />
                {{ selectedOption?.label ?? NONE_LABEL }}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <!-- "Laboró normal" va primero y separado: es lo que el sistema
                   asume de buena fe, y la respuesta que quita lo registrado. El
                   círculo vacío es literal: no hay nada que pintar. -->
              <SelectItem :value="NONE" class="py-2">
                <span class="size-2.5 shrink-0 rounded-full border-2 border-muted-foreground/40" />
                {{ NONE_LABEL }}
              </SelectItem>
              <SelectSeparator />
              <SelectItem
                v-for="option in OPTIONS"
                :key="option.value"
                :value="option.value"
                class="py-2"
              >
                <span
                  class="size-2.5 shrink-0 rounded-full"
                  :style="{ backgroundColor: option.color }"
                />
                {{ option.label }}
              </SelectItem>
            </SelectContent>
          </Select>

          <div class="space-y-2">
            <Label>Persona</Label>
            <EmployeeCombobox v-model="employeeId" :employees="employees" />
          </div>

          <div v-if="needsSpan" class="space-y-2">
            <Label>Duración</Label>
            <div class="flex gap-1 rounded-lg bg-muted p-1">
              <button
                v-for="option in SPANS"
                :key="option.value"
                type="button"
                class="flex-1 rounded-md px-2 py-1.5 text-xs transition"
                :class="
                  span === option.value
                    ? 'bg-background font-medium shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                "
                @click="span = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <!--
            Rango: el inicio es el día del que se entró y no se toca; el fin es
            libre hacia adelante. `min` en el input nativo da exactamente esa
            regla, sin validación a mano.
          -->
          <div v-if="needsRange" class="space-y-2">
            <Label for="capture-end">Fechas</Label>
            <div class="flex items-center gap-2">
              <Input :model-value="date" type="date" disabled class="h-10" />
              <span class="shrink-0 text-sm text-muted-foreground">a</span>
              <Input id="capture-end" v-model="endDate" type="date" :min="date" class="h-10" />
            </div>
            <p v-if="selectedDays > 1" class="text-xs text-muted-foreground">
              {{ selectedDays }} días seleccionados.
            </p>
          </div>

          <!-- Saldo de vacaciones: la pregunta que el dueño siempre tiene al
               conceder unas, y que hoy resuelve buscando en un cuaderno. -->
          <div
            v-if="isVacation && employee"
            class="rounded-lg px-3 py-2 text-xs"
            :class="
              exceedsBalance
                ? 'bg-destructive/10 text-destructive'
                : 'bg-muted/60 text-muted-foreground'
            "
          >
            <template v-if="exceedsBalance">
              Excede el saldo: {{ employee.name.split(" ")[0] }} tiene
              {{ employee.vacationBalance }} días acumulados.
            </template>
            <template v-else>
              {{ employee.name.split(" ")[0] }} tiene
              <strong class="font-semibold">{{ employee.vacationBalance }} días</strong> acumulados.
            </template>
          </div>

          <!-- Soporte: la incapacidad trae certificado de la EPS, el permiso
               suele traer carta. -->
          <div v-if="needsAttachment" class="space-y-2">
            <Label for="capture-file">Soporte (opcional)</Label>
            <Input id="capture-file" type="file" class="h-10 py-1.5" @change="onFileChange" />
            <p v-if="attachmentName" class="text-xs text-muted-foreground">
              Adjunto: {{ attachmentName }}
            </p>
          </div>

          <div v-if="needsHours" class="space-y-2">
            <Label for="capture-amount">Horas</Label>
            <Input
              id="capture-amount"
              v-model="amount"
              type="number"
              min="0"
              step="0.5"
              class="h-10"
            />

            <p v-if="isEditing" class="text-xs text-muted-foreground">
              Déjalo en 0 para quitar la novedad.
            </p>
            <p
              v-else-if="Number(amount) === 0"
              class="text-xs text-muted-foreground"
            >
              Indica un valor mayor que 0 para guardar.
            </p>
          </div>
        </template>

        <div class="space-y-2">
          <Label for="capture-note">Nota (opcional)</Label>
          <Textarea id="capture-note" v-model="note" rows="2" />
        </div>

        <!-- Se anuncia el borrado antes de que ocurra: el usuario entró a un
             formulario y el botón acaba de cambiar de significado. -->
        <p v-if="willDelete" class="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
          Se va a quitar la novedad registrada para esta persona este día.
        </p>
      </div>

      <DialogFooter>
        <Button variant="ghost" @click="emit('update:open', false)">Cancelar</Button>
        <Button
          :disabled="!canSave"
          :variant="willDelete ? 'destructive' : 'default'"
          @click="save"
        >
          {{ saveLabel }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
