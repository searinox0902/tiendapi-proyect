<script setup lang="ts">
import { ref, watch } from "vue"
import { watchDebounced } from "@vueuse/core"
import { IconUser } from "@tabler/icons-vue"

import { Input } from "@/components/ui/input"
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import { customersApi } from "@/api/customers/customers.api"
import type { ICustomer } from "@/api/customers/customers.types"


const props = defineProps<{
  modelValue: string
  field: "nit" | "fullname"
  id?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  "update:modelValue": [value: string]
  select: [customer: ICustomer]
}>()

const open = ref(false)
const results = ref<ICustomer[]>([])
const isLoading = ref(false)
const highlightedIndex = ref(-1)
const isSuppressed = ref(false)

async function runSearch() {
  if (isSuppressed.value) {
    return
  }
  const term = props.modelValue.trim()
  if (term === "") {
    results.value = []
    open.value = false
    return
  }
  isLoading.value = true
  try {
    const { data } = await customersApi.getCustomers({ search: term, limit: 6 })
    results.value = data
    highlightedIndex.value = data.length > 0 ? 0 : -1
    open.value = data.length > 0
  } catch {
    results.value = []
    open.value = false
  } finally {
    isLoading.value = false
  }
}

watchDebounced(() => props.modelValue, runSearch, { debounce: 250 })

function setQuietly(value: string) {
  isSuppressed.value = true
  emit("update:modelValue", value)
  setTimeout(() => { isSuppressed.value = false }, 0)
}

function choose(customer: ICustomer) {
  setQuietly(props.field === "nit" ? (customer.nit ?? "") : customer.fullname)
  emit("select", customer)
  open.value = false
}

watch(() => props.modelValue, () => {
  if (isSuppressed.value) {
    open.value = false
  }
})

function onArrowDown() {
  if (!open.value || results.value.length === 0) return
  highlightedIndex.value = Math.min(highlightedIndex.value + 1, results.value.length - 1)
}

function onArrowUp() {
  if (!open.value || results.value.length === 0) return
  highlightedIndex.value = Math.max(highlightedIndex.value - 1, 0)
}

function onEnter() {
  if (!open.value) return
  const customer = results.value[highlightedIndex.value]
  if (customer !== undefined) {
    choose(customer)
  }
}

defineExpose({ setQuietly })
</script>

<template>
  <Popover v-model:open="open">
    <PopoverAnchor as-child>
      <Input
        :id="id"
        :model-value="modelValue"
        :placeholder="placeholder"
        autocomplete="off"
        @update:model-value="value => emit('update:modelValue', String(value))"
        @keydown.down.prevent="onArrowDown"
        @keydown.up.prevent="onArrowUp"
        @keydown.enter.prevent="onEnter"
        @keydown.escape="open = false"
      />
    </PopoverAnchor>

    <PopoverContent
      class="w-[--reka-popover-trigger-width] min-w-72 p-1"
      align="start"
      @open-auto-focus.prevent
      @close-auto-focus.prevent
    >
      <button
        v-for="(customer, index) in results"
        :key="customer.id"
        type="button"
        class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors"
        :class="index === highlightedIndex ? 'bg-accent text-accent-foreground' : ''"
        @click="choose(customer)"
        @mouseenter="highlightedIndex = index"
      >
        <IconUser class="size-4 shrink-0 text-muted-foreground" />
        <span class="min-w-0 flex-1 truncate">{{ customer.fullname }}</span>
        <span class="shrink-0 font-mono text-xs text-muted-foreground">{{ customer.nit ?? "—" }}</span>
      </button>
    </PopoverContent>
  </Popover>
</template>
