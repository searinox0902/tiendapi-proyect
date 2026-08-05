<script setup lang="ts">
import { RouterView } from "vue-router";
import { Toaster } from "@/components/ui/sonner";
import 'vue-sonner/style.css'
</script>

<template>
  <!--
    Sin <Transition> a propósito: con `mode="out-in"` Vue espera a que la vista
    saliente termine su animación, y las vistas con sidebar tienen raíz de
    fragmento (SidebarProvider → TooltipProvider), que no es animable. La salida
    nunca terminaba y la vista entrante no llegaba a montarse: pantalla en blanco
    al navegar entre Dashboard y Referencias.
    Si se quiere el fundido, va dentro de <SidebarInset> (solo el contenido),
    no envolviendo el shell completo — el sidebar no debería parpadear.
  -->
  <RouterView />
  <Toaster />
</template>

