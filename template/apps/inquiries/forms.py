from django import forms
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.html import format_html

from apps.core.forms import SpamProtectedFormMixin, StyledFormMixin

from .models import Inquiry


def _consent_help():
    return format_html(
        '<a class="link" href="{}" target="_blank" rel="noopener">Aydınlatma metnini okuyun</a>',
        reverse_lazy("pages:privacy"),
    )


class InquiryForm(SpamProtectedFormMixin, StyledFormMixin, forms.ModelForm):
    consent = forms.BooleanField(
        label="Kişisel verilerimin talebime yanıt verilmesi amacıyla işlenmesini kabul ediyorum.",
        help_text=lazy(_consent_help, str)(),
        error_messages={"required": "Devam etmek için onay vermeniz gerekiyor."},
    )

    class Meta:
        model = Inquiry
        fields = ["full_name", "email", "phone", "message"]
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Örn. Ayşe Yılmaz"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "ornek@firma.com"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "0 5xx xxx xx xx"}),
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Projenizden kısaca bahsedin"}),
        }

    def save(self, commit=True):
        self.instance.consent_at = timezone.now()
        return super().save(commit=commit)
