import {
  Battery,
  Bike,
  Box,
  Car,
  CircleGauge,
  Disc,
  Droplet,
  Fuel,
  Gauge,
  Hammer,
  Layers,
  Lightbulb,
  Package,
  PaintBucket,
  Ruler,
  Settings,
  Shield,
  ShoppingCart,
  Snowflake,
  SprayCan,
  Tag,
  Thermometer,
  Wind,
  Wrench,
  Zap,
} from "@lucide/vue"
import type { Component } from "vue"

/**
 * `Category.icon` guarda solo este nombre (string, sin `enum`/`CHECK` en el
 * backend — D-72): el set de íconos vive y crece acá, no en el esquema. Un
 * nombre que no está en este mapa (ícono removido, dato viejo, typo) cae a
 * `DEFAULT_CATEGORY_ICON` en vez de romper la UI.
 */
export const CATEGORY_ICONS: Record<string, Component> = {
  wrench: Wrench,
  droplet: Droplet,
  battery: Battery,
  disc: Disc,
  gauge: Gauge,
  "circle-gauge": CircleGauge,
  package: Package,
  tag: Tag,
  "shopping-cart": ShoppingCart,
  car: Car,
  bike: Bike,
  fuel: Fuel,
  lightbulb: Lightbulb,
  shield: Shield,
  zap: Zap,
  settings: Settings,
  box: Box,
  layers: Layers,
  "paint-bucket": PaintBucket,
  snowflake: Snowflake,
  thermometer: Thermometer,
  wind: Wind,
  ruler: Ruler,
  hammer: Hammer,
  "spray-can": SprayCan,
}

export const DEFAULT_CATEGORY_ICON = Tag

export function resolveCategoryIcon(name: string | null | undefined): Component {
  if (!name) return DEFAULT_CATEGORY_ICON
  return CATEGORY_ICONS[name] ?? DEFAULT_CATEGORY_ICON
}

/** Opciones para el picker de alta, en el orden en que se listan. */
export const CATEGORY_ICON_OPTIONS = Object.keys(CATEGORY_ICONS).map(value => ({
  value,
  label: value,
}))
