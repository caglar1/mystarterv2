// Harita bileşenleri (Alpine CSP build ile uyumlu: mantık burada, şablonda sadece isimler).
document.addEventListener("alpine:init", () => {
  function readJson(id) {
    const element = document.getElementById(id);
    return element ? JSON.parse(element.textContent) : null;
  }

  // Popup içeriği DOM ile kurulur (innerHTML yok -> XSS riski yok).
  function popupContent(place) {
    const wrapper = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = place.name;
    wrapper.append(title);
    if (place.category) {
      const category = document.createElement("div");
      category.textContent = place.category;
      category.className = "text-xs opacity-70";
      wrapper.append(category);
    }
    return wrapper;
  }

  Alpine.data("leafletMap", () => ({
    map: null,
    init() {
      const config = readJson("map-config");
      const places = readJson("places-data") || [];
      this.map = L.map(this.$el, { scrollWheelZoom: false }).setView(config.center, config.zoom);

      if (config.tiles === "pmtiles") {
        const dark = document.documentElement.dataset.theme === "marka-koyu";
        protomapsL
          .leafletLayer({ url: config.url, flavor: dark ? "dark" : "light", lang: "tr", attribution: config.attribution })
          .addTo(this.map);
      } else {
        L.tileLayer(config.url, {
          maxZoom: config.maxZoom,
          attribution: config.attribution,
          // Sayfanın genel Referrer-Policy'si "same-origin"; karo sağlayıcıları (Stadia, CARTO) alan adı
          // doğrulaması için origin'i görmeli. Yalnızca origin gönderilir, sayfa yolu gönderilmez.
          referrerPolicy: "strict-origin-when-cross-origin",
        }).addTo(this.map);
      }

      const icon = L.icon({
        ...config.icon,
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41],
      });
      const markers = places.map((place) =>
        L.marker([place.lat, place.lng], { icon, title: place.name }).bindPopup(popupContent(place)),
      );
      if (markers.length) {
        const group = L.featureGroup(markers).addTo(this.map);
        this.map.fitBounds(group.getBounds(), { padding: [24, 24], maxZoom: 15 });
      }

      this.onFocus = (event) => this.map.setView([event.detail.lat, event.detail.lng], 17);
      window.addEventListener("place:focus", this.onFocus);
    },
    destroy() {
      window.removeEventListener("place:focus", this.onFocus);
      if (this.map) this.map.remove();
    },
  }));

  // Konumu tarayıcıdan alır, gizli alanlara yazar; isteği HTMX gönderir (Alpine HTTP isteği yapmaz).
  Alpine.data("nearbyFinder", () => ({
    busy: false,
    error: "",
    locate() {
      if (!("geolocation" in navigator)) {
        this.error = "Tarayıcınız konum özelliğini desteklemiyor.";
        return;
      }
      this.busy = true;
      this.error = "";
      navigator.geolocation.getCurrentPosition(
        (position) => {
          this.$refs.lat.value = position.coords.latitude.toFixed(6);
          this.$refs.lng.value = position.coords.longitude.toFixed(6);
          this.busy = false;
          htmx.trigger(this.$el, "submit");
        },
        () => {
          this.busy = false;
          this.error = "Konum alınamadı. Konum iznini kontrol edin.";
        },
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
      );
    },
  }));

  Alpine.data("placeFocus", () => ({
    focus() {
      const detail = { lat: Number(this.$el.dataset.lat), lng: Number(this.$el.dataset.lng) };
      window.dispatchEvent(new CustomEvent("place:focus", { detail }));
      document.getElementById("map")?.scrollIntoView({ behavior: "smooth", block: "center" });
    },
  }));
});
