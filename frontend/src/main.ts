import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./style.css";
//  Importar acá y no desde una vista: los efectos del módulo (clase `.dark` del
//  modo y atributo `data-theme` del color, D-80) corren al importarlo, así que
//  colgados de una pantalla solo se aplicarían al llegar a ella. El login no
//  importa el composable, y sin esto arrancaba siempre en claro y en violeta
//  aunque el usuario tuviera otra cosa guardada.
import "./composables/useTheme";

createApp(App).use(createPinia()).use(router).mount("#app");
