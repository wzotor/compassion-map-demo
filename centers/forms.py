from django import forms
from .models import Participant


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = [
            "participant_name",
            "participant_id",
            "sex",
            "caregiver_name",
            "house_latitude",
            "house_longitude",
        ]
        widgets = {
            "participant_name": forms.TextInput(attrs={"class": "form-control"}),
            "participant_id": forms.TextInput(attrs={"class": "form-control"}),
            "sex": forms.Select(attrs={"class": "form-select"}),
            "caregiver_name": forms.TextInput(attrs={"class": "form-control"}),
            "house_latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "house_longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ensure all fields have a Bootstrap base class
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            if "form-control" not in css and "form-select" not in css:
                field.widget.attrs["class"] = (css + " form-control").strip()

        # After a POST, mark invalid fields with Bootstrap red styling
        if self.is_bound:
            for name in self.fields:
                if name in self.errors:
                    current = self.fields[name].widget.attrs.get("class", "")
                    if "is-invalid" not in current:
                        self.fields[name].widget.attrs["class"] = (current + " is-invalid").strip()

class ParticipantUploadForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": ".csv"}
        )
    )
