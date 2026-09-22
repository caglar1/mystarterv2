"""Form altyapısı: DaisyUI sınıfları, hata stilleri ve spam koruması.

- `DaisyFormRenderer` (settings.FORM_RENDERER): `{{ form }}` tek satırda stilli render edilir.
- `StyledFormMixin`: widget'lara DaisyUI sınıflarını ve hata durumunu ekler.
- `SpamProtectedFormMixin`: honeypot alanı + imzalı zaman damgası (çok hızlı gönderimler reddedilir).
"""

import time

from django import forms
from django.conf import settings
from django.core import signing
from django.forms.renderers import DjangoTemplates
from django.utils.translation import gettext_lazy as _

_WIDGET_CLASSES = [
    (forms.CheckboxInput, "checkbox checkbox-primary"),
    (forms.RadioSelect, "radio radio-primary"),
    (forms.CheckboxSelectMultiple, "checkbox checkbox-primary"),
    (forms.Select, "select w-full"),
    (forms.SelectMultiple, "select w-full"),
    (forms.Textarea, "textarea w-full"),
    (forms.ClearableFileInput, "file-input w-full"),
    (forms.FileInput, "file-input w-full"),
]


class DaisyFormRenderer(DjangoTemplates):
    form_template_name = "forms/div.html"
    field_template_name = "forms/field.html"


def _css_class_for(widget: forms.Widget) -> str:
    for widget_type, css_class in _WIDGET_CLASSES:
        if isinstance(widget, widget_type):
            return css_class
    return "input w-full"


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{_css_class_for(field.widget)} {existing}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                error_class = "input-error" if "input" in widget.attrs.get("class", "") else ""
                if "textarea" in widget.attrs.get("class", ""):
                    error_class = "textarea-error"
                elif "select" in widget.attrs.get("class", ""):
                    error_class = "select-error"
                if error_class:
                    widget.attrs["class"] += f" {error_class}"
                widget.attrs["aria-invalid"] = "true"


class SpamProtectedFormMixin:
    """Botlara karşı iki katman: görünmez honeypot alanı ve minimum doldurma süresi."""

    honeypot_field = "website"
    timestamp_field = "form_ts"
    spam_message = _("The form could not be submitted. Please refresh the page and try again.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        honeypot = forms.CharField(
            required=False,
            label=_("Leave this field empty"),
            widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
        )
        honeypot.is_honeypot = True
        self.fields[self.honeypot_field] = honeypot
        self.fields[self.timestamp_field] = forms.CharField(
            required=False,
            widget=forms.HiddenInput,
            initial=signing.dumps(time.time(), salt="form-ts"),
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get(self.honeypot_field):
            raise forms.ValidationError(self.spam_message, code="spam")
        try:
            started = signing.loads(cleaned.get(self.timestamp_field) or "", salt="form-ts", max_age=86400)
        except signing.BadSignature as exc:
            raise forms.ValidationError(self.spam_message, code="spam") from exc
        if time.time() - float(started) < settings.FORM_MIN_SUBMIT_SECONDS:
            raise forms.ValidationError(self.spam_message, code="spam")
        return cleaned
