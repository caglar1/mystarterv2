from pathlib import PurePath

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from apps.core.ratelimit import ratelimit

from .forms import InquiryForm
from .models import Inquiry
from .tasks import send_inquiry_emails


@require_POST
@ratelimit("inquiry", rate="5/10m")
def submit(request):
    form = InquiryForm(request.POST, request.FILES)
    if not form.is_valid():
        if request.htmx:
            return render(request, "inquiries/form_card.html", {"form": form}, status=422)
        return render(request, "pages/contact.html", {"form": form}, status=422)

    inquiry = form.save()
    send_inquiry_emails.enqueue(inquiry.pk)
    messages.success(request, _("Thank you! We received your request and will get back to you shortly."))

    if request.htmx:
        return render(request, "inquiries/form_card.html", {"sent": True, "inquiry": inquiry})
    return redirect("pages:contact")


@staff_member_required
@require_GET
def attachment(request, pk: int):
    """Teklif ekini indirir. Dosyalar `private/` altında; web sunucusu onları doğrudan sunmaz."""
    inquiry = get_object_or_404(Inquiry, pk=pk)
    if not inquiry.attachment:
        raise Http404
    suffix = PurePath(inquiry.attachment.name).suffix
    return FileResponse(
        inquiry.attachment.open("rb"), as_attachment=True, filename=f"inquiry-{inquiry.pk}{suffix}"
    )
