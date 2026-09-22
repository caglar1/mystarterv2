from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from apps.inquiries.forms import InquiryForm


def home(request):
    return render(request, "pages/home.html", {"form": InquiryForm()})


def about(request):
    return render(request, "pages/about.html")


def services(request):
    return render(request, "pages/services.html")


def contact(request):
    return render(request, "pages/contact.html", {"form": InquiryForm()})


def privacy(request):
    return render(request, "pages/privacy.html")


def ui_kit(request):
    if not settings.DEBUG:
        raise Http404
    return render(request, "pages/ui_kit.html", {"form": InquiryForm()})
