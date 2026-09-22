// Uygulama geneli Alpine bileşenleri.
// Alpine'ın CSP build'i kullanılıyor: şablonlarda yalnızca basit ifadeler (x-data="toast", @click="close")
// yazılır, mantık burada Alpine.data() ile tanımlanır. Inline <script> ve eval yok.
document.addEventListener("alpine:init", () => {
  Alpine.data("themeToggle", () => ({
    dark: document.documentElement.dataset.theme === "marka-koyu",
    toggle() {
      this.dark = !this.dark;
      const theme = this.dark ? "marka-koyu" : "marka";
      document.documentElement.dataset.theme = theme;
      try {
        localStorage.setItem("theme", theme);
      } catch (error) {
        // Gizli mod vb.: tercih hatırlanmaz, sorun değil.
      }
    },
  }));

  // Toast bildirimleri 5 sn sonra kendiliğinden kapanır.
  Alpine.data("toast", () => ({
    visible: true,
    init() {
      this.timer = setTimeout(() => this.close(), 5000);
    },
    close() {
      clearTimeout(this.timer);
      this.visible = false;
      setTimeout(() => this.$el.remove(), 300);
    },
  }));
});
