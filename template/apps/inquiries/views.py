from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.ratelimit import ratelimit

from .forms import InquiryForm
from .tasks import send_inquiry_emails


@require_POST
@ratelimit("inquiry", rate="5/10m")
def submit(request):
    form = InquiryForm(request.POST)
    if not form.is_valid():
        if request.htmx:
            return render(request, "inquiries/form_card.html", {"form": form}, status=422)
        return render(request, "pages/contact.html", {"form": form}, status=422)

    inquiry = form.save()
    send_inquiry_emails.enqueue(inquiry.pk)
    messages.success(request, "Talebiniz alındı. En kısa sürede size dönüş yapacağız.")

    if request.htmx:
        return render(request, "inquiries/form_card.html", {"sent": True, "inquiry": inquiry})
    return redirect("pages:contact")
