<template>
  <div
    class="loginContainer grid min-h-screen place-items-start items-center px-6 py-12"
    :style="businessImageStyle"
  >
    <div class="w-full ml-44 max-w-md">
      <div class="mb-12 text-center">
        <span
          class="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-xl bg-primary text-xl font-bold text-primary-foreground"
        >
          T
        </span>
        <h1 class="text-2xl font-bold text-foreground">TiendAPI</h1>
        <p class="mt-1 text-sm text-muted-foreground">Gestión comercial local</p>
      </div>

      <h2 class="text-xl text-center font-semibold text-card-foreground">Iniciar sesión</h2>


      <div class="rounded-lg p-6">
        
        <form class="mt-4 space-y-6" @submit.prevent="submit">
          
          <FormField v-slot="{ componentField }" name="email">
            <FormItem>
              <FormLabel>Usuario</FormLabel>
              <FormControl>
                <Input type="text" placeholder="tu.usuario" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="password">
            <FormItem>
              <FormLabel>Contraseña</FormLabel>
              <FormControl>
                <Input type="password" placeholder="Ingrese constraseña" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ value, handleChange }" name="saveSession">
            <FormItem class="flex flex-row items-center gap-2 space-y-0">
              <FormControl>
                <Checkbox :model-value="value" @update:model-value="handleChange" />
              </FormControl>
              <FormLabel class="font-normal">Recordar usuario</FormLabel>
            </FormItem>
          </FormField>

          <Button
            type="submit" 
            :disabled="isSubmitting || !meta.valid || authStore.isLoading" 
            class="w-full">
            <Spinner v-if="authStore.isLoading" />
            Entrar
          </Button>


        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted } from "vue";
  import { useForm } from "vee-validate";
  import { toTypedSchema } from "@vee-validate/zod";
  import { Button } from "@/components/ui/button";
  import { Input } from "@/components/ui/input";
  import { Checkbox } from "@/components/ui/checkbox";
  import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
  } from "@/components/ui/form";
  import { isAxiosError } from "axios";
  import { loginSchema } from "@/api/auth/auth.schema";
  import { useAuthStore } from "@/stores/auth"
  import { readLoginImageUrl, rememberLoginImage } from "@/lib/branding"
  import { brandingApi } from "@/api/branding/branding.api"
  import { Spinner } from '@/components/ui/spinner'
  import { toast } from 'vue-sonner'
  import { useRouter } from "vue-router";


  const router = useRouter();
  const authStore = useAuthStore();

  onMounted(() => {
    import("@/pages/dashboard/DashboardView.vue")
  });

  /**
   * Fondo del login: la imagen del negocio si esta instalación ya la conoce.
   *
   * Se lee de `localStorage` y no del backend porque esta pantalla se dibuja
   * **antes** de autenticarse: sin token no hay `tenant_id`, y el servidor no
   * puede saber de qué negocio es una petición anónima. Ver `@/lib/branding`.
   *
   * Devuelve `{}` cuando no hay ninguna, y ahí manda la regla de la hoja de
   * estilos (el fondo por defecto): una máquina recién instalada no tiene por
   * qué mostrar una pantalla en blanco.
   */
  const businessImageStyle = computed(() => {
    const url = readLoginImageUrl();
    return url ? { backgroundImage: `url("${url}")` } : {};
  });

  const REMEMBERED_EMAIL_KEY = "tiendapi.rememberedEmail";
  const rememberedEmail = localStorage.getItem(REMEMBERED_EMAIL_KEY);

  const { handleSubmit, isSubmitting, meta, resetForm } = useForm({
    validationSchema: toTypedSchema(loginSchema),
    initialValues: {
      email: rememberedEmail ?? "",
      password: "",
      saveSession: !!rememberedEmail,
    },
  });

  function resetLogin() {
    resetForm();
  }

  function describeLoginError(error: unknown): string {
    if (isAxiosError(error)) {
      if (!error.response) {
        return `No se pudo conectar con el servidor (${error.code ?? error.message})`;
      }
      const { status, data } = error.response;
      const detail = data?.detail;
      const message = typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("; ")
          : undefined;
      return message
        ? `Error al iniciar sesión (${status}): ${message}`
        : `Error al iniciar sesión (${status})`;
    }
    return `Error inesperado al iniciar sesión: ${error instanceof Error ? error.message : String(error)}`;
  }


  const submit = handleSubmit(async (values) => {
    const { saveSession, ...credentials } = values;

    try {
      await authStore.login(credentials);

      //  Ya hay token: se aprovecha para dejar la imagen del negocio
      //  actualizada de cara al **próximo** inicio de sesión. Va sin `await` y
      //  con el error tragado a propósito — es una comodidad visual, y hacer
      //  esperar (o peor, fallar) un login por ella sería desproporcionado.
      brandingApi
        .getBranding()
        .then(({ data }) => rememberLoginImage(data.login_image_url))
        .catch(() => {});

      if (saveSession) {
        localStorage.setItem(REMEMBERED_EMAIL_KEY, credentials.email);
        toast.success("Inicio de sesión exitoso", {
            position: "bottom-center",
        }); 
      } else {
        localStorage.removeItem(REMEMBERED_EMAIL_KEY);
      }
      router.push({ name: "dashboard" });
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 401) {
        toast.error("Usuario o contraseña incorrectos", {
            position: "bottom-center",
        });
        resetLogin();
      } else {
        toast.error(describeLoginError(error), {
            position: "bottom-center",
        });
      }
    }
  });



</script>

<style scoped>
  /*
    El `background-image` por defecto se queda acá; cuando el negocio subió su
    propia imagen, `businessImageStyle` la sobreescribe inline (la regla inline
    gana sobre la de la hoja, sin necesidad de `!important`). Encuadre `contain`
    en los dos casos: la imagen del negocio puede tener cualquier proporción y
    `cover` la recortaría por donde caiga.
  */
  .loginContainer {
    background-image: url('@/assets/bg_login.png');
    background-size: contain;
    background-position: right;
    background-repeat: no-repeat;
  }
</style>
