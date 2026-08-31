<script setup lang="ts">
import { Moon, Sun } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Switch } from '@/components/ui/switch'
import { isDark } from '@/composables/useTheme'
</script>

<template>
  <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
    <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
      <SidebarTrigger class="-ml-1" />
      <Separator
        orientation="vertical"
        class="mx-2 data-[orientation=vertical]:h-4"
      />
      <h1 class="text-base font-medium">
        Documents
      </h1>
      <div class="ml-auto flex items-center gap-2">
        <div class="flex items-center gap-2">
          <Sun class="size-4 text-muted-foreground" />
          <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
          <Moon class="size-4 text-muted-foreground" />
        </div>
        <Button variant="ghost" as-child size="sm" class="hidden sm:flex">
          <a
            href="https://github.com/shadcn-ui/ui/tree/main/apps/v4/app/(examples)/dashboard"
            rel="noopener noreferrer"
            target="_blank"
            class="dark:text-foreground"
          >
            GitHub
          </a>
        </Button>
      </div>
    </div>
  </header>
</template>
