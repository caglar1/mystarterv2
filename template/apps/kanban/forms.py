from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import Board, Card


class BoardForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Board
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": _("Board name")})}


class CardForm(StyledFormMixin, forms.Form):
    title = forms.CharField(label=_("Title"), max_length=200)
    status = forms.ChoiceField(choices=Card.Status.choices, widget=forms.HiddenInput)


class MoveForm(forms.Form):
    status = forms.ChoiceField(choices=Card.Status.choices)
    order = forms.CharField(required=False)

    def clean_order(self):
        raw = self.cleaned_data.get("order", "")
        try:
            return [int(part) for part in raw.split(",") if part.strip()]
        except ValueError as exc:
            raise forms.ValidationError(_("Invalid order")) from exc
