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

  // Sekmeler. Şablonda: <div x-data="tabs" data-tab="ilk"> + @click="show('ikinci')", x-show="is('ikinci')"
  Alpine.data("tabs", () => ({
    tab: "",
    init() {
      this.tab = this.$el.dataset.tab || "";
    },
    show(name) {
      this.tab = name;
    },
    is(name) {
      return this.tab === name;
    },
  }));

  // Tarayıcının kendi <dialog> penceresi. Şablonda: <div x-data="modal"> + @click="open" + <dialog x-ref="dialog">
  Alpine.data("modal", () => ({
    open() {
      this.$refs.dialog.showModal();
    },
  }));
});
