from django import forms

from apps.core.forms import StyledFormMixin

from .prompts import SUMMARY_LENGTHS


class SummarizeForm(StyledFormMixin, forms.Form):
    text = forms.CharField(
        label="Metin",
        min_length=50,
        max_length=20_000,
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "Özetlenecek metni buraya yapıştırın"}),
    )
    length = forms.ChoiceField(
        label="Özet uzunluğu",
        choices=[("kisa", "Kısa"), ("orta", "Madde madde"), ("uzun", "Ayrıntılı")],
        initial="kisa",
    )

    def clean_length(self):
        value = self.cleaned_data["length"]
        if value not in SUMMARY_LENGTHS:
            raise forms.ValidationError("Geçersiz seçim")
        return value
