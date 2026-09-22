from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin


class SummarizeForm(StyledFormMixin, forms.Form):
    text = forms.CharField(
        label=_("Text"),
        min_length=50,
        max_length=20_000,
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": _("Paste the text to summarize here")}),
    )
    length = forms.ChoiceField(
        label=_("Summary length"),
        choices=[("short", _("Short")), ("bullets", _("Bullet points")), ("detailed", _("Detailed"))],
        initial="short",
    )
