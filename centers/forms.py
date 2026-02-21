from django import forms
from .models import Participant, ProjectCenter


class ParticipantForm(forms.ModelForm):
    """
    Staff usage:
      - Do NOT show project_center in the form.
      - View sets participant.project_center = staff_center

    National Office usage:
      - Show project_center dropdown so they can assign any center.
      - In the view, pass show_center_field=True
    """

    class Meta:
        model = Participant
        fields = [
            "project_center",          # will be hidden/removed for staff
            "participant_name",
            "participant_id",
            "sex",
            "caregiver_name",
            "house_latitude",
            "house_longitude",
        ]
        widgets = {
            "project_center": forms.Select(attrs={"class": "form-select"}),
            "participant_name": forms.TextInput(attrs={"class": "form-control"}),
            "participant_id": forms.TextInput(attrs={"class": "form-control"}),
            "sex": forms.Select(attrs={"class": "form-select"}),
            "caregiver_name": forms.TextInput(attrs={"class": "form-control"}),
            "house_latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "house_longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
        }

    def __init__(self, *args, **kwargs):
        show_center_field = kwargs.pop("show_center_field", False)
        super().__init__(*args, **kwargs)

        # If staff, remove project_center field completely
        if not show_center_field:
            self.fields.pop("project_center", None)
        else:
            # National Office: show all centers
            self.fields["project_center"].queryset = ProjectCenter.objects.all().order_by("center_code")

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


class ProjectCenterForm(forms.ModelForm):
    class Meta:
        model = ProjectCenter
        fields = [
            "name",
            "center_code",
            "territory",
            "cluster",
            "latitude",
            "longitude",
            "beneficiaries",
            "address",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "center_code": forms.TextInput(attrs={"class": "form-control"}),
            "territory": forms.TextInput(attrs={"class": "form-control"}),
            "cluster": forms.TextInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "beneficiaries": forms.NumberInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            if "form-control" not in css and "form-select" not in css:
                field.widget.attrs["class"] = (css + " form-control").strip()

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