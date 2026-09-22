from django.contrib import messages
from django.template.loader import render_to_string

_REDIRECT_CODES = {301, 302, 303, 307, 308}
_HTMX_NAVIGATION_HEADERS = ("HX-Redirect", "HX-Location", "HX-Refresh")


class HtmxMessagesMiddleware:
    """HTMX yanıtlarına Django mesajlarını toast olarak ekler (out-of-band swap).

    Normal sayfa isteklerinde mesajlar base.html içindeki toast alanında render edilir.
    HTMX isteklerinde ise sayfa yeniden yüklenmediği için mesajlar bu middleware ile
    yanıtın sonuna `hx-swap-oob` olarak eklenir; böylece bir sonraki sayfaya kaymazlar.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not getattr(request, "htmx", False) or not self._can_append(response):
            return response

        storage = messages.get_messages(request)
        if not len(storage):
            return response

        response.write(render_to_string("core/partials/toasts_oob.html", {"messages": storage}, request))
        return response

    @staticmethod
    def _can_append(response) -> bool:
        if response.streaming or response.status_code in _REDIRECT_CODES or response.status_code == 204:
            return False
        if any(header in response.headers for header in _HTMX_NAVIGATION_HEADERS):
            return False
        return response.get("Content-Type", "").startswith("text/html")
