import { http } from "@/lib/axios";
import type { IBranding } from "./branding.types";

export const brandingApi = {
  /** Imagen del negocio cargada, o `login_image_url: null` si no hay. */
  getBranding() {
    return http.get<IBranding>("/branding");
  },

  /**
   * Sube (o reemplaza) la imagen del negocio.
   *
   * El backend deriva la extensión del **nombre del archivo**, así que quien
   * llame tiene que mandar un `File` cuyo nombre coincida con su contenido
   * real — importa cuando la imagen se reencodea a JPEG antes de subirla.
   */
  uploadLoginImage(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return http.post<IBranding>("/branding/login-image", formData);
  },

  /** Quita la imagen: el login vuelve a su fondo por defecto. */
  deleteLoginImage() {
    return http.delete<void>("/branding/login-image");
  },
};
