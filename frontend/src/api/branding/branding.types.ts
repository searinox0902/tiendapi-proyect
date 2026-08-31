export interface IBranding {
  /**
   * Ruta **relativa** de la imagen del negocio (`/static/branding/...`), o
   * `null` si no hay ninguna cargada.
   *
   * Relativa y nunca absoluta a propósito: una URL con el host quemado
   * (`http://localhost:8000/...`) rompe en cualquier otra máquina de la LAN,
   * que es el bug que D-84 sacó del modelo. El host lo pone el cliente al
   * pintarla, con el que esté usando en ese momento.
   */
  login_image_url: string | null;
}
