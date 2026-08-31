import {
  IconAddressBook,
  IconCashRegister,
  IconDashboard,
  IconPackage,
  IconReceipt,
  IconReport,
  IconSettings,
  IconTags,
} from "@tabler/icons-vue"
import type { Component } from "vue"

export interface NavItem {
  title: string
  /** Apunta al `name` de una ruta del router. */
  to: string
  icon: Component
}

export interface NavGroup {
  /** Mini-título del grupo. Omitirlo lo deja sin título. */
  label?: string
  items: NavItem[]
}

/**
 * Navegación de módulos, agrupada por área. Fuente única para el sidebar
 * (`AppSidebar.vue`) y el selector de módulo de cada navbar interno
 * (`ModuleNavSelect.vue`) — para agregar una opción basta con una línea más
 * en el grupo que corresponda.
 */
export const navGroups: NavGroup[] = [
  {
    items: [
      { title: "Dashboard", to: "dashboard", icon: IconDashboard },
    ],
  },
  {
    label: "Gestión logística",
    items: [
      { title: "Referencias", to: "references", icon: IconTags },
      { title: "Productos", to: "items", icon: IconPackage },
    ],
  },
  {
    label: "Ventas",
    items: [
      { title: "Caja registradora", to: "pos", icon: IconCashRegister },
      { title: "Facturación", to: "invoices", icon: IconReceipt },
    ],
  },
  {
    label: "Reportes",
    items: [
      { title: "Reporte DIAN", to: "blank", icon: IconReport },
    ],
  },
  {
    label: "Datos base",
    items: [
      { title: "Directorio", to: "directory", icon: IconAddressBook },
      { title: "Configuraciones", to: "settings", icon: IconSettings },
    ],
  },
]

export const navItems: NavItem[] = navGroups.flatMap((group) => group.items)
