// Kanban: SortableJS ile sürükle-bırak, sonucu HTMX ile sunucuya kaydeder.
document.addEventListener("alpine:init", () => {
  Alpine.data("kanbanColumn", () => ({
    init() {
      this.sortable = Sortable.create(this.$el, {
        group: "kanban",
        animation: 150,
        ghostClass: "opacity-40",
        // Dokunmatik ekranda sayfa kaydırması sürüklemeyle karışmasın
        delay: 150,
        delayOnTouchOnly: true,
        onEnd: (event) => this.moved(event),
      });
    },
    moved(event) {
      if (event.from === event.to && event.oldIndex === event.newIndex) return;
      const ids = [...event.to.querySelectorAll("[data-card-id]")].map((el) => el.dataset.cardId);
      // `source`: istek, body'deki hx-headers (CSRF) değerini miras alsın
      htmx.ajax("POST", event.item.dataset.moveUrl, {
        source: event.item,
        swap: "none",
        values: { status: event.to.dataset.status, order: ids.join(",") },
      });
    },
    destroy() {
      if (this.sortable) this.sortable.destroy();
    },
  }));

  // Kart eklendikten sonra formu temizle
  Alpine.data("cardForm", () => ({
    reset(event) {
      if (event.detail.successful) this.$el.reset();
    },
  }));
});

// Sunucu taşımayı reddederse (ör. oturum düştü) ekrandaki sıra yanlış kalmasın
document.addEventListener("htmx:responseError", (event) => {
  if (event.detail.elt && event.detail.elt.closest && event.detail.elt.closest("[data-kanban]")) {
    window.location.reload();
  }
});
