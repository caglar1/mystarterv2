from django import forms
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.html import format_html
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.core.forms import SpamProtectedFormMixin, StyledFormMixin

from .models import Inquiry


def _consent_help():
    return format_html(
        '<a class="link" href="{}" target="_blank" rel="noopener">{}</a>',
        reverse("pages:privacy"),
        _("Read the privacy notice"),
    )


class InquiryForm(SpamProtectedFormMixin, StyledFormMixin, forms.ModelForm):
    consent = forms.BooleanField(
        label=_("I consent to the processing of my personal data in order to respond to my request."),
        help_text=lazy(_consent_help, str)(),
        error_messages={"required": _("Please give your consent to continue.")},
    )

    class Meta:
        model = Inquiry
        fields = ["full_name", "email", "phone", "message"]
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": _("e.g. Jane Doe")}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "name@company.com"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "+90 5xx xxx xx xx"}),
            "message": forms.Textarea(
                attrs={"rows": 4, "placeholder": _("Tell us briefly about your project")}
            ),
        }

    def save(self, commit=True):
        self.instance.consent_at = timezone.now()
        self.instance.language = get_language()
        return super().save(commit=commit)
